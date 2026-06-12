"""
knowledge_extractor.py — Phase 2: Knowledge_Extractor

LLM pipeline that reads cleaned fashion text and emits a versioned Rule_Corpus JSON.

Strategy (per design.md §2):
  - Chunk text into ≤ 2000-token segments with 200-token overlap
  - Each chunk → Gemini with schema-constrained prompt → JSON array of StyleRule
  - Validate against schema, retry up to 3× on failure
  - Merge all chunks, deduplicate by content hash, assign sequential IDs
  - Output: Rule_Corpus JSON + ExtractionJob record
"""

import json
import hashlib
import logging
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, asdict, field
import uuid

logger = logging.getLogger(__name__)

# ── Constants ─────────────────────────────────────────────────────────────────
CHUNK_TOKENS = 2000
OVERLAP_TOKENS = 200
AVG_CHARS_PER_TOKEN = 4             # rough approximation
CHUNK_SIZE = CHUNK_TOKENS * AVG_CHARS_PER_TOKEN
OVERLAP_SIZE = OVERLAP_TOKENS * AVG_CHARS_PER_TOKEN
MAX_RETRIES = 3
LOW_CONFIDENCE_THRESHOLD = 0.5

VALID_RULE_TYPES = {
    "color_pairing",
    "fabric_compatibility",
    "occasion_appropriateness",
    "layering_proportion",
    "fit_combination",
    "footwear_match",
    "pattern_compatibility",
}

# ── Data Classes ──────────────────────────────────────────────────────────────
@dataclass
class StyleRule:
    ruleId: str
    ruleType: str
    description: str
    conditions: dict
    score: float           # 0-1
    confidence: float      # 0-1
    sourcePassage: Optional[str] = None


@dataclass
class UnresolvedPassage:
    passageId: str
    text: str
    confidenceScore: float
    reason: str
    detectedAt: str


@dataclass
class ExtractionJob:
    jobId: str
    inputFileHash: str
    startedAt: str
    status: str           # "running" | "completed" | "failed"
    completedAt: Optional[str] = None
    corpusVersion: Optional[str] = None
    ruleCount: Optional[int] = None
    unresolvedPassages: list = field(default_factory=list)
    error: Optional[str] = None


@dataclass
class RuleCorpus:
    version: str
    generatedAt: str
    sourceHash: str
    ruleCount: int
    rules: list


# ── Chunking ──────────────────────────────────────────────────────────────────
def _chunk_text(text: str) -> list[str]:
    """Split text into overlapping chunks of ~2000 tokens."""
    chunks = []
    start = 0
    while start < len(text):
        end = start + CHUNK_SIZE
        chunks.append(text[start:end])
        start += CHUNK_SIZE - OVERLAP_SIZE
    return chunks


# ── Hash ──────────────────────────────────────────────────────────────────────
def _rule_content_hash(rule: dict) -> str:
    """Hash a rule by its description for deduplication."""
    content = (rule.get("description", "") + rule.get("ruleType", "")).lower().strip()
    return hashlib.sha256(content.encode()).hexdigest()[:16]


def _file_hash(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


# ── LLM Extraction ────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """You are a fashion knowledge extraction expert. Extract styling rules from the provided fashion text.

Output a JSON array of rule objects. Each object MUST conform to this exact schema:
{
  "ruleType": one of ["color_pairing","fabric_compatibility","occasion_appropriateness","layering_proportion","fit_combination","footwear_match","pattern_compatibility"],
  "description": "Clear, actionable rule statement (1-2 sentences)",
  "conditions": { key-value pairs describing when/how the rule applies },
  "score": float between 0.0 and 1.0 (importance weight),
  "confidence": float between 0.0 and 1.0 (your extraction confidence),
  "sourcePassage": "verbatim excerpt from the source text (max 200 chars)"
}

Rules:
- Only output valid JSON array, no markdown, no extra text
- If a passage cannot be mapped to a rule type, set confidence below 0.5 and ruleType to the closest match
- Extract as many distinct rules as the text supports
- Do not invent rules not supported by the text"""


def _call_gemini(prompt: str, api_key: str, model: str) -> str:
    """Call Gemini API and return the text response."""
    try:
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        model_obj = genai.GenerativeModel(model)
        response = model_obj.generate_content(prompt)
        return response.text
    except Exception as e:
        raise RuntimeError(f"Gemini API error: {e}")


def _extract_json_array(text: str) -> list:
    """Extract JSON array from LLM response, handling markdown code blocks."""
    # Strip markdown code block if present
    text = re.sub(r'^```(?:json)?\s*', '', text.strip(), flags=re.MULTILINE)
    text = re.sub(r'\s*```$', '', text.strip(), flags=re.MULTILINE)
    text = text.strip()
    # Find JSON array
    match = re.search(r'\[.*\]', text, re.DOTALL)
    if match:
        return json.loads(match.group())
    raise ValueError("No JSON array found in LLM response")


def _validate_rule(obj: dict) -> tuple[bool, str]:
    """Validate a single rule object against schema."""
    required = ['ruleType', 'description', 'conditions', 'score', 'confidence']
    for field_name in required:
        if field_name not in obj:
            return False, f"Missing field: {field_name}"
    if obj['ruleType'] not in VALID_RULE_TYPES:
        return False, f"Invalid ruleType: {obj['ruleType']}"
    if not (0.0 <= obj.get('score', -1) <= 1.0):
        return False, "score must be 0.0-1.0"
    if not (0.0 <= obj.get('confidence', -1) <= 1.0):
        return False, "confidence must be 0.0-1.0"
    return True, ""


# ── Mock extractor (no API key) ────────────────────────────────────────────────
def _mock_extract_from_chunk(chunk_text: str, chunk_idx: int) -> list[dict]:
    """
    Fallback extractor when no Gemini API key is available.
    Extracts simple rules using keyword matching against the fashion text.
    Used for development/testing only.
    """
    rules = []
    text_lower = chunk_text.lower()

    keyword_map = [
        ("color", "color_pairing", "Colors should be harmoniously combined in an outfit."),
        ("fabric", "fabric_compatibility", "Fabric types should be compatible in texture and formality."),
        ("occasion", "occasion_appropriateness", "Clothing should be appropriate for the occasion."),
        ("layer", "layering_proportion", "Layering should create visual balance and proportion."),
        ("fit", "fit_combination", "Garment fits should be balanced — one relaxed, one fitted."),
        ("shoe", "footwear_match", "Footwear should match the style and occasion of the outfit."),
        ("pattern", "pattern_compatibility", "Patterns should not compete — one bold, rest solid."),
    ]

    for keyword, rule_type, description in keyword_map:
        if keyword in text_lower:
            # Find sentence containing keyword
            sentences = chunk_text.split('.')
            passage = next(
                (s.strip() for s in sentences if keyword in s.lower()),
                chunk_text[:100]
            )
            rules.append({
                "ruleType": rule_type,
                "description": description,
                "conditions": {"keyword_detected": keyword},
                "score": 0.7,
                "confidence": 0.6,
                "sourcePassage": passage[:200],
            })

    return rules


# ── Main Extractor ─────────────────────────────────────────────────────────────
def extract(
    cleaned_text_path: Path,
    output_dir: Path,
    corpus_version: str,
    api_key: str = "",
    gemini_model: str = "gemini-2.5-flash",
) -> tuple[Path, ExtractionJob]:
    """
    Extract styling rules from cleaned text and produce a versioned Rule_Corpus.

    Args:
        cleaned_text_path: Path to preprocessed .txt file.
        output_dir: Directory to write corpus + log.
        corpus_version: Semantic version string (e.g. "2.1.0").
        api_key: Gemini API key. If empty, falls back to mock extraction.
        gemini_model: Gemini model identifier.

    Returns:
        (corpus_path, ExtractionJob)
    """
    job_id = f"job-{uuid.uuid4().hex[:8]}"
    started_at = datetime.now(timezone.utc).isoformat()
    source_hash = _file_hash(cleaned_text_path)

    job = ExtractionJob(
        jobId=job_id,
        inputFileHash=source_hash,
        startedAt=started_at,
        status="running",
    )

    logger.info(f"[KnowledgeExtractor] Job {job_id} started — version {corpus_version}")

    use_mock = not api_key
    if use_mock:
        logger.warning("[KnowledgeExtractor] No API key — using mock extractor (dev mode)")

    text = cleaned_text_path.read_text(encoding='utf-8')
    chunks = _chunk_text(text)
    logger.info(f"[KnowledgeExtractor] Text split into {len(chunks)} chunks")

    all_rules: list[dict] = []
    unresolved: list[UnresolvedPassage] = []
    seen_hashes: set[str] = set()

    for idx, chunk in enumerate(chunks):
        logger.debug(f"[KnowledgeExtractor] Processing chunk {idx+1}/{len(chunks)}")

        extracted = []

        if use_mock:
            extracted = _mock_extract_from_chunk(chunk, idx)
        else:
            prompt = f"{SYSTEM_PROMPT}\n\n---\nFASHION TEXT:\n{chunk}\n---\nOutput JSON array:"
            for attempt in range(1, MAX_RETRIES + 1):
                try:
                    response_text = _call_gemini(prompt, api_key, gemini_model)
                    extracted = _extract_json_array(response_text)
                    break
                except Exception as e:
                    if attempt == MAX_RETRIES:
                        logger.error(
                            f"[KnowledgeExtractor] Chunk {idx} failed after {MAX_RETRIES} attempts: {e}"
                        )
                        unresolved.append(UnresolvedPassage(
                            passageId=f"p-{idx:05d}",
                            text=chunk[:300],
                            confidenceScore=0.0,
                            reason=f"LLM extraction failed: {e}",
                            detectedAt=datetime.now(timezone.utc).isoformat(),
                        ))
                    else:
                        logger.warning(f"[KnowledgeExtractor] Attempt {attempt} failed, retrying...")
                        time.sleep(1)

        for rule_dict in extracted:
            valid, reason = _validate_rule(rule_dict)
            if not valid:
                logger.debug(f"[KnowledgeExtractor] Invalid rule skipped: {reason}")
                continue

            # Log low-confidence passages
            if rule_dict.get("confidence", 1.0) < LOW_CONFIDENCE_THRESHOLD:
                unresolved.append(UnresolvedPassage(
                    passageId=f"p-{idx:05d}-lc",
                    text=rule_dict.get("sourcePassage", rule_dict["description"])[:300],
                    confidenceScore=rule_dict["confidence"],
                    reason="Confidence below 0.5",
                    detectedAt=datetime.now(timezone.utc).isoformat(),
                ))

            # Deduplicate by content hash
            content_hash = _rule_content_hash(rule_dict)
            if content_hash not in seen_hashes:
                seen_hashes.add(content_hash)
                all_rules.append(rule_dict)

    # Assign sequential IDs
    final_rules: list[StyleRule] = []
    for i, rule_dict in enumerate(all_rules, start=1):
        final_rules.append(StyleRule(
            ruleId=f"rule-{i:04d}",
            ruleType=rule_dict["ruleType"],
            description=rule_dict["description"],
            conditions=rule_dict.get("conditions", {}),
            score=rule_dict.get("score", 0.5),
            confidence=rule_dict.get("confidence", 0.5),
            sourcePassage=rule_dict.get("sourcePassage"),
        ))

    # Build corpus
    corpus = RuleCorpus(
        version=corpus_version,
        generatedAt=datetime.now(timezone.utc).isoformat(),
        sourceHash=source_hash,
        ruleCount=len(final_rules),
        rules=[asdict(r) for r in final_rules],
    )

    # Write corpus
    output_dir.mkdir(parents=True, exist_ok=True)
    corpus_filename = f"rule_corpus_v{corpus_version}.json"
    corpus_path = output_dir / corpus_filename
    corpus_path.write_text(
        json.dumps(asdict(corpus), indent=2, ensure_ascii=False),
        encoding='utf-8'
    )

    # Finalize job
    completed_at = datetime.now(timezone.utc).isoformat()
    job.status = "completed"
    job.completedAt = completed_at
    job.corpusVersion = corpus_version
    job.ruleCount = len(final_rules)
    job.unresolvedPassages = [asdict(u) for u in unresolved]

    # Write extraction log
    log_path = output_dir / f"extraction_log_{job_id}.json"
    log_path.write_text(json.dumps(asdict(job), indent=2), encoding='utf-8')

    logger.info(
        f"[KnowledgeExtractor] Job {job_id} completed — "
        f"{len(final_rules)} rules, {len(unresolved)} unresolved passages"
    )

    return corpus_path, job


# ── CLI ────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    import os
    logging.basicConfig(level=logging.INFO)
    if len(sys.argv) < 4:
        print("Usage: python knowledge_extractor.py <cleaned_txt> <output_dir> <version>")
        sys.exit(1)
    api_key = os.getenv("GEMINI_API_KEY", "")
    corpus_file, job_record = extract(
        Path(sys.argv[1]),
        Path(sys.argv[2]),
        sys.argv[3],
        api_key=api_key,
    )
    print(f"\n✅ Corpus: {corpus_file}")
    print(f"📋 Job: {json.dumps(asdict(job_record), indent=2)}")
