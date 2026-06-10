"""
outfit_scorer.py — Phase 4: Outfit_Scorer (XGBoost)

Trains an XGBoost ranker on labeled examples from rules.json,
then scores OutfitFeatureVectors to produce compatibility score (0-100)
and confidence score (0-1).

Scoring formula (fallback when model not yet trained):
  weighted sum of sub-scores using scoring_weights from rules.json
"""

import json
import logging
import joblib
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
import numpy as np

from .feature_extractor import OutfitFeatureVector, has_missing_features

logger = logging.getLogger(__name__)

# ── Feature order (must be consistent for training + inference) ───────────────
FEATURE_NAMES = [
    "colorCompatibilityScore",
    "fabricCompatibilityScore",
    "occasionMatchScore",
    "garmentCategoryBalanceScore",
    "patternCompatibilityScore",
    "fitCombinationScore",
    "seasonMaterialMatchScore",
    "rulesSatisfied",
    "totalRulesApplicable",
]

# ── Data Classes ──────────────────────────────────────────────────────────────
@dataclass
class ScoringRequest:
    outfitId: str
    features: dict    # OutfitFeatureVector as dict


@dataclass
class ScoringResponse:
    outfitId: str
    compatibilityScore: int       # 0-100 or -1
    confidenceScore: float        # 0.0-1.0
    corpusVersion: str
    scoredAt: str
    error: Optional[dict] = None


# ── Model Loader ──────────────────────────────────────────────────────────────
class OutfitScorerModel:
    """Wrapper around XGBoost model with weighted-sum fallback."""

    def __init__(self, rules_path: Path, models_dir: Path):
        self.rules_path = rules_path
        self.models_dir = models_dir
        self._model = None
        self._weights: dict = {}
        self._corpus_version: str = "unknown"
        self._load_weights()

    def _load_weights(self):
        """Load scoring_weights from rules.json."""
        try:
            rules = json.loads(self.rules_path.read_text(encoding='utf-8'))
            self._weights = rules.get("scoring_weights", {
                "color_compatibility": 0.30,
                "style_occasion_match": 0.20,
                "footwear_match": 0.15,
                "fabric_compatibility": 0.15,
                "pattern_compatibility": 0.08,
                "fit_combination": 0.07,
                "garment_category_balance": 0.05,
            })
            self._corpus_version = rules.get("version", "1.0.0")
            logger.info(f"[OutfitScorer] Loaded weights for corpus v{self._corpus_version}")
        except Exception as e:
            logger.error(f"[OutfitScorer] Failed to load rules.json: {e}")

    def _model_path(self) -> Path:
        return self.models_dir / f"outfit_scorer_v{self._corpus_version}.joblib"

    def load_model(self) -> bool:
        """Try to load a saved XGBoost model. Returns True if successful."""
        # First try versioned path, then try generic path
        paths_to_try = [
            self._model_path(),
            self.models_dir / "xgb_regressor.pkl",
        ]
        for path in paths_to_try:
            if path.exists():
                try:
                    import joblib as jl
                    self._model = jl.load(str(path))
                    logger.info(f"[OutfitScorer] Loaded XGBoost model from {path}")
                    return True
                except Exception as e:
                    logger.warning(f"[OutfitScorer] Could not load model from {path}: {e}")
        return False

    def train(self, rules_path: Optional[Path] = None) -> dict:
        """
        Train XGBoost on labeled examples in rules.json (xgboost_training_examples).
        Saves model artifact to models_dir.
        Returns training summary dict.
        """
        try:
            import xgboost as xgb
            from sklearn.model_selection import cross_val_score
            from sklearn.preprocessing import MinMaxScaler
        except ImportError as e:
            raise RuntimeError(f"ML dependencies not installed: {e}")

        rp = rules_path or self.rules_path
        rules = json.loads(rp.read_text(encoding='utf-8'))
        examples = rules.get("xgboost_training_examples", [])

        if not examples:
            raise ValueError("No xgboost_training_examples found in rules.json")

        X = []
        y = []
        for ex in examples:
            # Support both "features" and "feature_vector" keys
            fv = ex.get("features", ex.get("feature_vector", {}))
            if isinstance(fv, str):
                continue  # skip malformed
            row = [
                fv.get("color_compatibility_score",    fv.get("colorCompatibilityScore",   50)),
                fv.get("fabric_compatibility_score",   fv.get("fabricCompatibilityScore",  50)),
                fv.get("style_occasion_match_score",   fv.get("occasionMatchScore",         50)),
                fv.get("footwear_match_score",         fv.get("footwearMatchScore",         50)),
                fv.get("pattern_compatibility_score",  fv.get("patternCompatibilityScore",  50)),
                fv.get("fit_combination_score",        fv.get("fitCombinationScore",         50)),
                fv.get("garment_category_balance",     fv.get("garmentCategoryBalanceScore", 50)),
                0,   # rulesSatisfied placeholder
                8,   # totalRulesApplicable placeholder
            ]
            X.append(row)
            # Support numeric score or string label
            label = ex.get("ground_truth_score", ex.get("label", 0.5))
            if isinstance(label, str):
                label = {"positive": 0.85, "negative": 0.15, "medium": 0.55}.get(label, 0.5)
            y.append(float(label))

        X_arr = np.array(X, dtype=float)
        y_arr = np.array(y, dtype=float)

        # Normalize labels to 0-1 if they look like 0-100 scores
        if y_arr.max() > 1.0:
            y_arr = y_arr / 100.0

        model = xgb.XGBRegressor(
            n_estimators=100,
            max_depth=4,
            learning_rate=0.1,
            subsample=0.8,
            colsample_bytree=0.8,
            random_state=42,
            eval_metric="rmse",
        )

        if len(X_arr) >= 5:
            cv_scores = cross_val_score(model, X_arr, y_arr, cv=min(5, len(X_arr)), scoring='r2')
            logger.info(f"[OutfitScorer] 5-fold CV R² scores: {cv_scores}")

        model.fit(X_arr, y_arr)
        self._model = model

        # Save artifact
        self.models_dir.mkdir(parents=True, exist_ok=True)
        save_path = self._model_path()
        joblib.dump(model, str(save_path))
        logger.info(f"[OutfitScorer] Model saved to {save_path}")

        return {
            "modelPath": str(save_path),
            "corpusVersion": self._corpus_version,
            "trainingSamples": len(X_arr),
            "features": FEATURE_NAMES,
            "trainedAt": datetime.now(timezone.utc).isoformat(),
        }

    def _weighted_sum_score(self, fv_dict: dict) -> tuple[int, float]:
        """
        Fallback scoring: weighted sum of sub-scores.
        Used when XGBoost model is not yet trained.
        """
        w = self._weights
        score = (
            fv_dict.get("colorCompatibilityScore", 0) * w.get("color_compatibility", 0.30) +
            fv_dict.get("occasionMatchScore", 0) * w.get("style_occasion_match", 0.20) +
            fv_dict.get("footwearMatchScore",
                fv_dict.get("fitCombinationScore", 0)) * w.get("footwear_match", 0.15) +
            fv_dict.get("fabricCompatibilityScore", 0) * w.get("fabric_compatibility", 0.15) +
            fv_dict.get("patternCompatibilityScore", 0) * w.get("pattern_compatibility", 0.08) +
            fv_dict.get("fitCombinationScore", 0) * w.get("fit_combination", 0.07) +
            fv_dict.get("garmentCategoryBalanceScore", 0) * w.get("garment_category_balance", 0.05)
        )
        score = round(min(100.0, max(0.0, score)))
        # Confidence based on rules satisfied ratio
        ratio = fv_dict.get("rulesSatisfied", 0) / max(fv_dict.get("totalRulesApplicable", 8), 1)
        confidence = round(0.5 + ratio * 0.5, 3)
        return int(score), confidence

    def score(self, fv: OutfitFeatureVector, corpus_version: str) -> ScoringResponse:
        """
        Score a single outfit feature vector.

        Returns ScoringResponse. If any required feature is missing,
        returns sentinel (compatibilityScore=-1, confidenceScore=0).
        """
        scored_at = datetime.now(timezone.utc).isoformat()
        fv_dict = asdict(fv)

        # ── Sentinel: missing required features ───────────────────────────────
        missing = has_missing_features(fv)
        if missing:
            return ScoringResponse(
                outfitId=fv.outfitId,
                compatibilityScore=-1,
                confidenceScore=0.0,
                corpusVersion=corpus_version,
                scoredAt=scored_at,
                error={"code": "MISSING_FEATURES", "missingFields": missing},
            )

        # ── Try XGBoost model ─────────────────────────────────────────────────
        if self._model is not None:
            try:
                feature_row = np.array([[fv_dict.get(f, 0) for f in FEATURE_NAMES]])
                raw = float(self._model.predict(feature_row)[0])
                # Model outputs 0-1, scale to 0-100
                compat_score = int(round(min(100.0, max(0.0, raw * 100))))
                # Confidence = model's output clamped to [0.1, 1.0]
                confidence = round(min(1.0, max(0.1, raw)), 3)
            except Exception as e:
                logger.warning(f"[OutfitScorer] XGBoost inference failed, using weighted sum: {e}")
                compat_score, confidence = self._weighted_sum_score(fv_dict)
        else:
            # Fallback: weighted sum
            compat_score, confidence = self._weighted_sum_score(fv_dict)

        return ScoringResponse(
            outfitId=fv.outfitId,
            compatibilityScore=compat_score,
            confidenceScore=confidence,
            corpusVersion=corpus_version,
            scoredAt=scored_at,
        )


# ── Package-level helpers ──────────────────────────────────────────────────────
def score_outfit(
    fv: OutfitFeatureVector,
    scorer: OutfitScorerModel,
    corpus_version: str,
) -> ScoringResponse:
    """Convenience wrapper."""
    return scorer.score(fv, corpus_version)
