"""
preprocessor.py — Phase 1: Data_Preprocessor

Cleans and normalizes raw fashion book text before LLM ingestion.

Steps (in order per design.md §1):
  1. PDF extraction (strip headers/footers/page numbers)
  2. Remove Unicode Cc and Cf control characters (except U+0009 tab, U+000A newline)
  3. Normalize to NFC form
  4. Replace smart quotes with ASCII equivalents
  5. Replace en-dash and em-dash with ` - `

Outputs: cleaned .txt file + PreprocessingReport JSON
"""

import re
import json
import unicodedata
import logging
from pathlib import Path
from datetime import datetime, timezone
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)

# ── Constants ─────────────────────────────────────────────────────────────────
MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024          # 10 MB
MIN_WORD_COUNT_WARNING = 500

SMART_QUOTE_MAP = str.maketrans({
    "\u201c": '"',   # "
    "\u201d": '"',   # "
    "\u2018": "'",   # '
    "\u2019": "'",   # '
    "\u2013": " - ", # en-dash
    "\u2014": " - ", # em-dash
})

# ── Data Classes ──────────────────────────────────────────────────────────────
@dataclass
class PreprocessingReport:
    inputFileName: str
    inputSizeBytes: int
    outputSizeBytes: int
    charactersRemoved: int
    unicodeNormalizationsApplied: int
    smartQuotesReplaced: int
    dashesNormalized: int
    wordCountAfterProcessing: int
    warnings: list
    processedAt: str


# ── PDF Extraction ────────────────────────────────────────────────────────────
def _extract_pdf_text(path: Path) -> str:
    """Extract text from PDF, stripping headers/footers by heuristic."""
    try:
        import pdfplumber
    except ImportError:
        raise RuntimeError("pdfplumber not installed. Run: pip install pdfplumber")

    pages_text = []
    with pdfplumber.open(str(path)) as pdf:
        # Collect all lines across pages with their page numbers
        all_lines: list[tuple[int, str]] = []
        for page_num, page in enumerate(pdf.pages, start=1):
            text = page.extract_text() or ""
            for line in text.splitlines():
                all_lines.append((page_num, line))

        # Heuristic: lines that repeat across many pages = header/footer
        from collections import Counter
        line_counts = Counter(line.strip() for _, line in all_lines)
        threshold = max(2, len(pdf.pages) // 5)  # appears on 20%+ of pages
        boilerplate = {line for line, count in line_counts.items()
                       if count >= threshold and line.strip()}

        for _, line in all_lines:
            stripped = line.strip()
            # Also skip pure page numbers
            if stripped not in boilerplate and not stripped.isdigit():
                pages_text.append(line)

    return "\n".join(pages_text)


# ── Core Processing Steps ─────────────────────────────────────────────────────
def _remove_control_chars(text: str) -> tuple[str, int]:
    """Remove Unicode Cc and Cf characters, keeping tab (U+0009) and newline (U+000A)."""
    allowed_controls = {'\t', '\n'}
    result = []
    removed = 0
    for ch in text:
        cat = unicodedata.category(ch)
        if cat in ('Cc', 'Cf') and ch not in allowed_controls:
            removed += 1
        else:
            result.append(ch)
    return ''.join(result), removed


def _nfc_normalize(text: str) -> tuple[str, int]:
    """Normalize to NFC. Returns (normalized_text, count_of_changed_chars)."""
    normalized = unicodedata.normalize('NFC', text)
    changed = sum(1 for a, b in zip(text, normalized) if a != b)
    return normalized, changed


def _replace_smart_quotes(text: str) -> tuple[str, int, int]:
    """Replace smart quotes and dashes. Returns (text, quotes_replaced, dashes_replaced)."""
    quotes_count = sum(text.count(ch) for ch in '"\u201c\u201d\u2018\u2019')
    dashes_count = sum(text.count(ch) for ch in '\u2013\u2014')
    result = text.translate(SMART_QUOTE_MAP)
    return result, quotes_count, dashes_count


# ── Main Preprocessor ─────────────────────────────────────────────────────────
def preprocess(
    input_path: Path,
    output_dir: Path
) -> tuple[Path, PreprocessingReport]:
    """
    Preprocess a .txt or .pdf file.

    Args:
        input_path: Path to the raw input file.
        output_dir: Directory to write the cleaned output.

    Returns:
        (cleaned_output_path, PreprocessingReport)

    Raises:
        ValueError: if file is too large, wrong format, etc.
        RuntimeError: if PDF is unreadable/corrupted.
    """
    warnings: list[str] = []

    # ── Validation ────────────────────────────────────────────────────────────
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    size = input_path.stat().st_size
    if size > MAX_FILE_SIZE_BYTES:
        raise ValueError(
            f"File size {size:,} bytes exceeds the 10 MB limit ({MAX_FILE_SIZE_BYTES:,} bytes)."
        )

    suffix = input_path.suffix.lower()
    if suffix not in ('.txt', '.pdf'):
        raise ValueError(
            f"Unsupported format '{suffix}'. Only .txt and .pdf are accepted."
        )

    # ── Step 1: Extract raw text ───────────────────────────────────────────────
    logger.info(f"[Preprocessor] Reading {input_path.name} ({size:,} bytes)")

    if suffix == '.pdf':
        try:
            raw_text = _extract_pdf_text(input_path)
        except Exception as e:
            raise RuntimeError(
                f"PDF is unreadable, corrupted, or password-protected: {e}"
            )
    else:
        raw_text = input_path.read_text(encoding='utf-8', errors='strict')

    # ── Step 2: Remove control characters ─────────────────────────────────────
    text, chars_removed = _remove_control_chars(raw_text)
    logger.debug(f"[Preprocessor] Removed {chars_removed} control characters")

    # ── Step 3: NFC normalization ──────────────────────────────────────────────
    text, nfc_count = _nfc_normalize(text)
    logger.debug(f"[Preprocessor] NFC normalization applied to {nfc_count} characters")

    # ── Step 4 & 5: Smart quotes + dashes ─────────────────────────────────────
    text, quotes_replaced, dashes_normalized = _replace_smart_quotes(text)

    # ── Word count check ───────────────────────────────────────────────────────
    word_count = len(text.split())
    if word_count < MIN_WORD_COUNT_WARNING:
        msg = (
            f"Document contains only {word_count} words after preprocessing. "
            f"This may be too short for meaningful rule extraction."
        )
        warnings.append(msg)
        logger.warning(f"[Preprocessor] {msg}")

    # ── Write output ───────────────────────────────────────────────────────────
    output_dir.mkdir(parents=True, exist_ok=True)
    stem = input_path.stem
    output_path = output_dir / f"{stem}_cleaned.txt"
    output_path.write_text(text, encoding='utf-8')

    output_size = output_path.stat().st_size
    logger.info(f"[Preprocessor] Written cleaned text to {output_path} ({output_size:,} bytes)")

    # ── Build report ───────────────────────────────────────────────────────────
    report = PreprocessingReport(
        inputFileName=input_path.name,
        inputSizeBytes=size,
        outputSizeBytes=output_size,
        charactersRemoved=chars_removed,
        unicodeNormalizationsApplied=nfc_count,
        smartQuotesReplaced=quotes_replaced,
        dashesNormalized=dashes_normalized,
        wordCountAfterProcessing=word_count,
        warnings=warnings,
        processedAt=datetime.now(timezone.utc).isoformat(),
    )

    # Save report JSON alongside cleaned file
    report_path = output_dir / f"{stem}_preprocessing_report.json"
    report_path.write_text(json.dumps(asdict(report), indent=2), encoding='utf-8')
    logger.info(f"[Preprocessor] Report saved to {report_path}")

    return output_path, report


# ── CLI entry point ───────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO)
    if len(sys.argv) < 3:
        print("Usage: python preprocessor.py <input_file> <output_dir>")
        sys.exit(1)
    cleaned, rpt = preprocess(Path(sys.argv[1]), Path(sys.argv[2]))
    print(f"\n✅ Cleaned file: {cleaned}")
    print(f"📊 Report:\n{json.dumps(asdict(rpt), indent=2)}")
