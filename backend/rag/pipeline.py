"""
pipeline.py — Phase 4: RAG_Pipeline

Orchestrates:
  1. Intent classification from user query
  2. Vector_Store retrieval (garments + rules)
  3. Outfit scoring (Feature_Extractor → Outfit_Scorer)
  4. Context assembly for Stylist LLM
  5. Gemini LLM call → natural language explanation
  6. Returns ranked outfit recommendations (max 3)

Fallback behaviors:
  - < 3 results above threshold → lowConfidence: true, use top-3 anyway
  - Zero results → error, no LLM call
  - Empty wardrobe → prompt to add garments, no scoring
  - Unknown intent → clarifying prompt, no LLM call
  - LLM unavailable → return outfit cards without explanation
"""

import itertools
import json
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from config import (
    GEMINI_API_KEY, LLM_MODEL, LLM_TIMEOUT_SECONDS,
    TOP_N_OUTFITS, CHAT_MAX_MESSAGE_CHARS, CHAT_HISTORY_WINDOW,
    LOW_CONFIDENCE_THRESHOLD, RAG_DEFAULT_K, RULE_CORPUS_DIR, MODELS_DIR,
)
from vector_store.store import VectorStore, EmbeddingRecord
from ml.feature_extractor import extract_features, OutfitFeatureVector
from ml.outfit_scorer import OutfitScorerModel, ScoringResponse

logger = logging.getLogger(__name__)

# ── Intent Keywords ───────────────────────────────────────────────────────────
INTENT_KEYWORDS = {
    "outfit_suggestion": ["wear", "outfit", "recommend", "suggest", "look", "dress", "style"],
    "color_pairing": ["color", "colour", "pair", "match", "goes with", "combine"],
    "fabric_pairing": ["fabric", "material", "linen", "wool", "cotton", "cashmere"],
    "wardrobe_gap_analysis": ["missing", "need", "gap", "add", "buy", "wardrobe"],
    "style_tips": ["tip", "rule", "advice", "guide", "how to", "what is"],
}


def classify_intent(query: str) -> str:
    """Classify user query intent using keyword matching."""
    q = query.lower()
    for intent, keywords in INTENT_KEYWORDS.items():
        if any(kw in q for kw in keywords):
            return intent
    return "unknown"


# ── Outfit Combination Generator ──────────────────────────────────────────────
def _generate_outfit_combinations(garments: list[dict]) -> list[list[dict]]:
    """
    Generate valid outfit combinations from the wardrobe.
    A valid outfit must have: at least 1 top + 1 bottom + 1 footwear.
    Also considers full_outfit category.
    """
    tops = [g for g in garments if g.get("category") == "top"]
    bottoms = [g for g in garments if g.get("category") == "bottom"]
    footwear = [g for g in garments if g.get("category") == "footwear"]
    outerwear = [g for g in garments if g.get("category") == "outerwear"]
    full_outfits = [g for g in garments if g.get("category") == "full_outfit"]

    combinations = []

    # Full outfit + footwear combinations
    for fo in full_outfits:
        for fw in footwear:
            combinations.append([fo, fw])

    # top + bottom + footwear (+ optional outerwear)
    for top, bottom, fw in itertools.product(tops, bottoms, footwear):
        combinations.append([top, bottom, fw])
        for ow in outerwear:
            combinations.append([top, bottom, fw, ow])

    # Limit to avoid combinatorial explosion
    return combinations[:50]


# ── LLM Stylist ────────────────────────────────────────────────────────────────
STYLIST_SYSTEM_PROMPT = """You are a professional fashion stylist AI. Generate a concise outfit explanation.

Rules:
- Reference specific garment names provided
- Include the compatibility score in your explanation
- 20-100 words maximum
- Reference at least one styling rule (e.g. color harmony, occasion match, fabric quality)
- If confidence < 0.6, append: "Note: This suggestion is based on limited data (confidence: {score}). Results may vary."
- Do NOT mention internal system names (XGBoost, RAG, Vector_Store, etc.)
- Do NOT generate new outfit combinations — only explain the one provided"""


def _call_gemini_stylist(
    garment_names: list[str],
    compatibility_score: int,
    confidence_score: float,
    occasion: str,
    retrieved_rules: list[str],
) -> Optional[str]:
    """Call Gemini to generate outfit explanation. Returns None on failure."""
    if not GEMINI_API_KEY:
        return _mock_explanation(garment_names, compatibility_score, occasion, retrieved_rules)

    rules_context = "\n".join(f"- {r}" for r in retrieved_rules[:3])
    prompt = f"""
Outfit: {", ".join(garment_names)}
Occasion: {occasion}
Compatibility Score: {compatibility_score}/100
Confidence: {confidence_score:.2f}

Relevant styling rules:
{rules_context}

Generate a 20-100 word explanation of why this outfit works for the occasion.
"""
    try:
        import google.generativeai as genai
        import signal

        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel(
            LLM_MODEL,
            system_instruction=STYLIST_SYSTEM_PROMPT,
        )
        response = model.generate_content(
            prompt,
            generation_config={"max_output_tokens": 200, "temperature": 0.4},
        )
        return response.text.strip()
    except Exception as e:
        logger.error(f"[RAGPipeline] Gemini stylist failed: {e}")
        return None


def _mock_explanation(
    garment_names: list[str],
    score: int,
    occasion: str,
    rules: list[str],
) -> str:
    """Generate a rule-grounded explanation without LLM (dev/offline mode)."""
    outfit_str = ", ".join(garment_names[:3])
    rule_ref = rules[0] if rules else "color harmony and proportion principles"
    return (
        f"Your {outfit_str} combination scores {score}/100 for {occasion}. "
        f"This works because it applies {rule_ref.lower()}, "
        f"creating a balanced and occasion-appropriate look."
    )


# ── Main RAG Pipeline ──────────────────────────────────────────────────────────
class RAGPipeline:
    def __init__(
        self,
        vector_store: VectorStore,
        scorer: OutfitScorerModel,
        rules_path: Path,
        corpus_version: str,
    ):
        self.vector_store = vector_store
        self.scorer = scorer
        self.rules_path = rules_path
        self.corpus_version = corpus_version

    def handle_query(
        self,
        session_id: str,
        user_id: str,
        user_query: str,
        garments: list[dict],
        conversation_history: list[dict],
        occasion: Optional[str] = None,
        k: int = RAG_DEFAULT_K,
    ) -> dict:
        """
        Full RAG pipeline execution.

        Returns:
            {
                "intent": str,
                "recommendations": list[dict],   # top-3 outfit cards
                "lowConfidence": bool,
                "clarifyingPrompt": str | None,
                "error": str | None,
                "requestId": str,
            }
        """
        request_id = str(uuid.uuid4())
        result_base = {
            "requestId": request_id,
            "intent": "unknown",
            "recommendations": [],
            "lowConfidence": False,
            "clarifyingPrompt": None,
            "error": None,
        }

        # ── Validate message length ───────────────────────────────────────────
        if len(user_query) > CHAT_MAX_MESSAGE_CHARS:
            result_base["error"] = f"Message exceeds {CHAT_MAX_MESSAGE_CHARS} character limit."
            return result_base

        # ── Intent classification ─────────────────────────────────────────────
        intent = classify_intent(user_query)
        result_base["intent"] = intent

        if intent == "unknown":
            result_base["clarifyingPrompt"] = (
                "I can help with: outfit suggestions, color pairing, fabric advice, "
                "wardrobe gap analysis, or style tips. What would you like help with?"
            )
            return result_base

        # ── Empty wardrobe guard ──────────────────────────────────────────────
        if intent == "outfit_suggestion" and not garments:
            result_base["clarifyingPrompt"] = (
                "Your wardrobe is empty. Please upload at least one garment before "
                "requesting outfit recommendations."
            )
            return result_base

        # ── Vector retrieval ──────────────────────────────────────────────────
        try:
            retrieval = self.vector_store.retrieve(
                query=user_query,
                user_id=user_id,
                k=k,
            )
            result_base["lowConfidence"] = retrieval.lowConfidence

            if not retrieval.records:
                logger.warning(f"[RAGPipeline] Zero retrieval results for request {request_id}")
                result_base["error"] = "ZERO_RETRIEVAL_RESULTS"
                return result_base

        except Exception as e:
            logger.error(f"[RAGPipeline] Vector_Store unavailable: {e}")
            retrieval = None
            result_base["lowConfidence"] = True

        # ── Outfit scoring ────────────────────────────────────────────────────
        scored_outfits: list[ScoringResponse] = []

        if intent == "outfit_suggestion" and garments:
            combos = _generate_outfit_combinations(garments)
            for i, combo in enumerate(combos):
                outfit_id = f"outfit-{request_id[:8]}-{i}"
                try:
                    fv = extract_features(
                        outfit_id=outfit_id,
                        garments=combo,
                        occasion=occasion,
                        rules_path=self.rules_path,
                        corpus_version=self.corpus_version,
                    )
                    score_resp = self.scorer.score(fv, self.corpus_version)
                    if score_resp.compatibilityScore != -1:
                        scored_outfits.append((score_resp, combo))
                except Exception as e:
                    logger.warning(f"[RAGPipeline] Scoring failed for combo {i}: {e}")

            # Sort by score descending, take top-N
            scored_outfits.sort(key=lambda x: x[0].compatibilityScore, reverse=True)
            top_outfits = scored_outfits[:TOP_N_OUTFITS]
        else:
            top_outfits = []

        # ── Retrieved rule texts ──────────────────────────────────────────────
        retrieved_rule_texts = []
        if retrieval:
            for record in retrieval.records:
                if record.type == "rule":
                    retrieved_rule_texts.append(
                        record.metadata.get("description", "") or
                        record.metadata.get("document", "")
                    )

        # Truncate conversation history to last N pairs
        history_pairs = conversation_history[-(CHAT_HISTORY_WINDOW * 2):]

        # ── Build outfit cards ────────────────────────────────────────────────
        recommendations = []
        for score_resp, combo in top_outfits:
            garment_names = [g.get("name", "Garment") for g in combo]

            # Generate explanation
            explanation = _call_gemini_stylist(
                garment_names=garment_names,
                compatibility_score=score_resp.compatibilityScore,
                confidence_score=score_resp.confidenceScore,
                occasion=occasion or "general",
                retrieved_rules=retrieved_rule_texts,
            )

            card = {
                "outfitId": score_resp.outfitId,
                "garments": combo,
                "garmentNames": garment_names,
                "compatibilityScore": score_resp.compatibilityScore,
                "confidenceScore": score_resp.confidenceScore,
                "lowConfidence": score_resp.confidenceScore < LOW_CONFIDENCE_THRESHOLD,
                "explanation": explanation or "",
                "explanationUnavailable": explanation is None,
                "corpusVersion": score_resp.corpusVersion,
                "scoredAt": score_resp.scoredAt,
            }
            recommendations.append(card)

        # ── Style tips / color / fabric queries (no scoring) ─────────────────
        if not recommendations and retrieval:
            # Return top retrieved rules as advice
            advice_rules = [
                r.metadata.get("description", r.metadata.get("ruleText", ""))
                for r in retrieval.records
                if r.type == "rule"
            ]
            if advice_rules:
                explanation = _call_gemini_stylist(
                    garment_names=[],
                    compatibility_score=0,
                    confidence_score=0.8,
                    occasion=occasion or "general",
                    retrieved_rules=advice_rules,
                ) or " ".join(advice_rules[:2])
                recommendations.append({
                    "outfitId": None,
                    "advice": explanation,
                    "rules": advice_rules[:5],
                })

        result_base["recommendations"] = recommendations
        return result_base
