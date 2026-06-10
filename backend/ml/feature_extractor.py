"""
feature_extractor.py — Phase 4: Feature_Extractor

Transforms a candidate Outfit (set of Garment dicts) into an OutfitFeatureVector
using the active Rule_Corpus lookup tables (rules.json).

Sub-score weights (from rules.json scoring_weights):
  color_compatibility    0.30
  style_occasion_match   0.20  (design.md uses 0.25 — aligned with rules.json)
  footwear_match         0.15
  fabric_compatibility   0.15
  pattern_compatibility  0.08
  fit_combination        0.07
  garment_category_bal   0.05
"""

import json
import logging
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


# ── Data Classes ──────────────────────────────────────────────────────────────
@dataclass
class OutfitFeatureVector:
    outfitId: str
    corpusVersion: str
    colorCompatibilityScore: float          # 0–100
    fabricCompatibilityScore: float         # 0–100
    occasionMatchScore: float               # 0–100
    garmentCategoryBalanceScore: float      # 0–100
    patternCompatibilityScore: float        # 0–100
    fitCombinationScore: float              # 0–100
    seasonMaterialMatchScore: float         # 0–100
    rulesSatisfied: int
    totalRulesApplicable: int


# ── Rule Corpus Loader ─────────────────────────────────────────────────────────
class RulesLoader:
    """Loads and caches rules.json from the project root."""

    _cache: Optional[dict] = None
    _corpus_path: Optional[Path] = None

    @classmethod
    def load(cls, corpus_path: Path) -> dict:
        if cls._cache is None or cls._corpus_path != corpus_path:
            cls._corpus_path = corpus_path
            cls._cache = json.loads(corpus_path.read_text(encoding='utf-8'))
            logger.info(f"[FeatureExtractor] Loaded rules from {corpus_path}")
        return cls._cache


# ── Sub-score Computers ────────────────────────────────────────────────────────
def _compute_color_score(garments: list[dict], rules: dict) -> float:
    """
    Score based on color_rules.good_pairs / bad_pairs.
    Neutral colors get a bonus. Returns 0–100.
    """
    color_rules = rules.get("color_rules", {})
    good_pairs = set(
        tuple(sorted(p)) for p in color_rules.get("good_pairs", [])
    )
    bad_pairs = set(
        tuple(sorted(p)) for p in color_rules.get("bad_pairs", [])
    )
    neutral_colors = set(c.lower() for c in color_rules.get("neutral_colors", []))

    colors = []
    for g in garments:
        c = g.get("primaryColor", "").lower().strip()
        if c:
            colors.append(c)
        sc = g.get("secondaryColor", "")
        if sc:
            colors.append(sc.lower().strip())

    if len(colors) < 2:
        return 80.0   # single-color outfit — assume acceptable

    total_pairs = 0
    good_count = 0
    bad_count = 0
    neutral_count = sum(1 for c in colors if c in neutral_colors)

    for i in range(len(colors)):
        for j in range(i + 1, len(colors)):
            pair = tuple(sorted([colors[i], colors[j]]))
            total_pairs += 1
            if pair in good_pairs:
                good_count += 1
            elif pair in bad_pairs:
                bad_count += 1

    if total_pairs == 0:
        return 75.0

    # Base score
    score = ((good_count - bad_count * 2) / total_pairs) * 100
    # Neutral bonus (up to +10)
    neutral_bonus = min(10, neutral_count * 5)
    score = max(0.0, min(100.0, score + 50 + neutral_bonus))
    return round(score, 1)


def _compute_fabric_score(garments: list[dict], rules: dict) -> float:
    """Score fabric pairings against fabric_compatibility_rules."""
    fabric_rules = rules.get("fabric_compatibility_rules", {})
    compatible = set(
        tuple(sorted(p)) for p in fabric_rules.get("compatible_pairs", [])
    )
    incompatible = set(
        tuple(sorted(p)) for p in fabric_rules.get("incompatible_pairs", [])
    )

    fabrics = [g.get("fabricType", "").lower().strip() for g in garments if g.get("fabricType")]

    if len(fabrics) < 2:
        return 80.0

    total = 0
    good = 0
    bad = 0
    for i in range(len(fabrics)):
        for j in range(i + 1, len(fabrics)):
            pair = tuple(sorted([fabrics[i], fabrics[j]]))
            total += 1
            if pair in compatible:
                good += 1
            elif pair in incompatible:
                bad += 1

    if total == 0:
        return 75.0

    score = ((good - bad * 2) / total) * 100
    return round(max(0.0, min(100.0, score + 50)), 1)


def _compute_occasion_score(garments: list[dict], occasion: Optional[str], rules: dict) -> float:
    """Score how well garment occasion tags match the requested occasion."""
    if not occasion:
        return 70.0

    style_rules = rules.get("style_occasion_rules", {})
    occasion_garments = style_rules.get(occasion.lower(), {}).get("appropriate_categories", [])

    if not occasion_garments:
        return 70.0

    garment_categories = [g.get("category", "").lower() for g in garments]
    garment_occasion_tags = []
    for g in garments:
        garment_occasion_tags.extend(t.lower() for t in g.get("occasionTags", []))

    # Check if all garments have the occasion tag
    tag_matches = sum(1 for g in garments if occasion.lower() in [t.lower() for t in g.get("occasionTags", [])])
    tag_score = (tag_matches / max(len(garments), 1)) * 100

    return round(min(100.0, tag_score), 1)


def _compute_footwear_score(garments: list[dict], occasion: Optional[str], rules: dict) -> float:
    """Score footwear appropriateness for the occasion."""
    footwear = next((g for g in garments if g.get("category", "").lower() == "footwear"), None)
    if not footwear:
        return 0.0   # Missing footwear — will trigger sentinel

    footwear_rules = rules.get("footwear_occasion_rules", {})
    if not occasion:
        return 70.0

    occasion_footwear = footwear_rules.get(occasion.lower(), {})
    appropriate = [s.lower() for s in occasion_footwear.get("appropriate_styles", [])]
    inappropriate = [s.lower() for s in occasion_footwear.get("inappropriate_styles", [])]

    style_tag = footwear.get("styleTag", "").lower()
    name_lower = footwear.get("name", "").lower()

    # Check by style tag or name keywords
    is_appropriate = any(s in style_tag or s in name_lower for s in appropriate)
    is_inappropriate = any(s in style_tag or s in name_lower for s in inappropriate)

    if is_inappropriate:
        return 20.0
    if is_appropriate:
        return 95.0
    return 65.0


def _compute_pattern_score(garments: list[dict], rules: dict) -> float:
    """Score pattern compatibility. max_patterns_in_outfit from rules.json."""
    pattern_rules = rules.get("pattern_rules", {})
    max_patterns = pattern_rules.get("max_patterns_in_outfit", 1)

    patterns = [
        g.get("patternType", "").lower().strip()
        for g in garments
        if g.get("patternType", "").lower() not in ("", "solid", "plain", "none")
    ]

    pattern_count = len(patterns)

    if pattern_count == 0:
        return 100.0   # All solid — perfect
    if pattern_count <= max_patterns:
        return 85.0    # Within allowed limit
    # Each extra pattern above max costs 25 points
    excess = pattern_count - max_patterns
    return max(0.0, 85.0 - excess * 25)


def _compute_fit_score(garments: list[dict], rules: dict) -> float:
    """Score fit combination against fit_combination_rules."""
    fit_rules = rules.get("fit_combination_rules", {})
    good_combos = [
        set(c) for c in fit_rules.get("good_combinations", [])
    ]
    bad_combos = [
        set(c) for c in fit_rules.get("bad_combinations", [])
    ]

    fits = set(
        g.get("fitType", "").lower().strip()
        for g in garments
        if g.get("fitType")
    )

    if not fits:
        return 75.0

    for bad in bad_combos:
        if bad.issubset(fits):
            return 20.0

    for good in good_combos:
        if good.issubset(fits):
            return 95.0

    return 70.0


def _compute_category_balance_score(garments: list[dict]) -> float:
    """
    Score completeness of garment categories.
    A complete outfit has: top + bottom + footwear (outerwear optional).
    """
    categories = {g.get("category", "").lower() for g in garments}

    required = {"top", "bottom", "footwear"}
    has_required = required.issubset(categories)

    # full_outfit counts as all required
    if "full_outfit" in categories:
        has_required = True

    if not has_required:
        missing = required - categories
        # Missing footwear is critical (triggers sentinel elsewhere)
        if "footwear" in missing:
            return 0.0
        return 50.0

    # Bonus for outerwear
    score = 100.0
    if "outerwear" in categories:
        score = min(100.0, score + 5)

    return score


def _compute_season_material_score(garments: list[dict], rules: dict) -> float:
    """Score season-material compatibility."""
    season_rules = rules.get("season_material_rules", {})
    if not season_rules:
        return 75.0

    scores = []
    for garment in garments:
        fabric = garment.get("fabricType", "").lower()
        for season, materials in season_rules.items():
            appropriate = [m.lower() for m in materials.get("appropriate_fabrics", [])]
            if fabric in appropriate:
                scores.append(90.0)
                break
        else:
            scores.append(70.0)

    return round(sum(scores) / max(len(scores), 1), 1)


# ── Sentinel check ─────────────────────────────────────────────────────────────
REQUIRED_SUB_SCORES = [
    "colorCompatibilityScore",
    "fabricCompatibilityScore",
    "occasionMatchScore",
    "garmentCategoryBalanceScore",
]


def has_missing_features(fv: OutfitFeatureVector) -> list[str]:
    """Return list of feature names that are 0 and indicate missing data."""
    missing = []
    d = asdict(fv)
    for field in REQUIRED_SUB_SCORES:
        if d.get(field, 1) == 0.0:
            missing.append(field)
    return missing


# ── Main Feature Extractor ────────────────────────────────────────────────────
def extract_features(
    outfit_id: str,
    garments: list[dict],
    occasion: Optional[str],
    rules_path: Path,
    corpus_version: str,
) -> OutfitFeatureVector:
    """
    Compute the full feature vector for an outfit.

    Args:
        outfit_id: Unique outfit identifier.
        garments: List of garment dicts (from DB or API).
        occasion: Selected occasion tag (e.g. "casual", "formal").
        rules_path: Path to rules.json.
        corpus_version: Active Rule_Corpus version string.

    Returns:
        OutfitFeatureVector
    """
    rules = RulesLoader.load(rules_path)

    color = _compute_color_score(garments, rules)
    fabric = _compute_fabric_score(garments, rules)
    occasion_score = _compute_occasion_score(garments, occasion, rules)
    footwear = _compute_footwear_score(garments, occasion, rules)
    pattern = _compute_pattern_score(garments, rules)
    fit = _compute_fit_score(garments, rules)
    category_balance = _compute_category_balance_score(garments)
    season_material = _compute_season_material_score(garments, rules)

    # Count rules satisfied (binary per sub-score threshold of 70)
    sub_scores = [color, fabric, occasion_score, footwear, pattern, fit, category_balance, season_material]
    rules_satisfied = sum(1 for s in sub_scores if s >= 70)
    total_applicable = len(sub_scores)

    return OutfitFeatureVector(
        outfitId=outfit_id,
        corpusVersion=corpus_version,
        colorCompatibilityScore=color,
        fabricCompatibilityScore=fabric,
        occasionMatchScore=occasion_score,
        garmentCategoryBalanceScore=category_balance,
        patternCompatibilityScore=pattern,
        fitCombinationScore=fit,
        seasonMaterialMatchScore=season_material,
        rulesSatisfied=rules_satisfied,
        totalRulesApplicable=total_applicable,
    )
