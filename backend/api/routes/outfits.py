"""
outfits.py — Outfit recommendation + save routes
POST /recommend  → score outfits for an occasion
POST /outfits    → save outfit to collection
GET  /outfits    → list saved outfits
"""
import uuid
import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from db.database import get_db
from db.models import Garment, Outfit, OutfitGarment, Wardrobe
from api.schemas import RecommendRequest, RecommendResponse, SaveOutfitRequest, OutfitCard
from api.routes.garments import _get_or_create_wardrobe, _garment_to_dict
from config import RULE_CORPUS_DIR, MODELS_DIR

logger = logging.getLogger(__name__)
router = APIRouter(tags=["outfits"])

_scorer = None
_corpus_version = "1.1.0"

def set_scorer(scorer, version: str):
    global _scorer, _corpus_version
    _scorer = scorer
    _corpus_version = version


@router.post("/recommend", response_model=RecommendResponse)
async def recommend(
    body: RecommendRequest,
    db: AsyncSession = Depends(get_db),
):
    """Score outfit combinations from wardrobe for a given occasion."""
    from ml.feature_extractor import extract_features
    from rag.pipeline import _generate_outfit_combinations

    wardrobe = await _get_or_create_wardrobe(body.userId, db)
    garment_result = await db.execute(
        select(Garment).where(Garment.wardrobeId == wardrobe.wardrobeId)
    )
    garments_orm = garment_result.scalars().all()
    if not garments_orm:
        return RecommendResponse(
            recommendations=[],
            lowConfidence=False,
            requestId=str(uuid.uuid4()),
            corpusVersion=_corpus_version,
        )

    garments = []
    for g in garments_orm:
        await db.refresh(g, ["occasion_tags"])
        garments.append(_garment_to_dict(g))

    combos = _generate_outfit_combinations(garments)
    scored = []

    for i, combo in enumerate(combos):
        outfit_id = f"rec-{uuid.uuid4().hex[:8]}-{i}"
        try:
            fv = extract_features(
                outfit_id=outfit_id,
                garments=combo,
                occasion=body.occasion,
                rules_path=RULE_CORPUS_DIR / "rules.json",
                corpus_version=_corpus_version,
            )
            if _scorer:
                resp = _scorer.score(fv, _corpus_version)
                if resp.compatibilityScore != -1:
                    scored.append((resp, combo))
        except Exception as e:
            logger.warning(f"[OutfitsRoute] Scoring failed for combo {i}: {e}")

    scored.sort(key=lambda x: x[0].compatibilityScore, reverse=True)
    top3 = scored[:3]

    cards = [
        OutfitCard(
            outfitId=resp.outfitId,
            garmentNames=[g.get("name") for g in combo],
            garmentIds=[g.get("garmentId") for g in combo],
            compatibilityScore=resp.compatibilityScore,
            confidenceScore=resp.confidenceScore,
            lowConfidence=resp.confidenceScore < 0.6,
            corpusVersion=resp.corpusVersion,
            occasion=body.occasion,
        )
        for resp, combo in top3
    ]

    return RecommendResponse(
        recommendations=cards,
        lowConfidence=any(c.lowConfidence for c in cards),
        requestId=str(uuid.uuid4()),
        corpusVersion=_corpus_version,
    )


@router.post("/outfits", status_code=201)
async def save_outfit(
    body: SaveOutfitRequest,
    user_id: str = "demo-user",
    db: AsyncSession = Depends(get_db),
):
    """Save a recommended outfit to a named collection."""
    # Validate collection name (1-50 chars) — Property 11
    if not (1 <= len(body.collectionName) <= 50):
        raise HTTPException(
            status_code=400,
            detail="Collection name must be between 1 and 50 characters.",
        )

    outfit = Outfit(
        outfitId=body.outfitId or str(uuid.uuid4()),
        userId=user_id,
        occasion=body.occasion,
        collectionName=body.collectionName,
        compatibilityScore=body.compatibilityScore,
        confidenceScore=body.confidenceScore,
        explanation=body.explanation,
        corpusVersion=body.corpusVersion,
    )
    db.add(outfit)
    await db.flush()

    for pos, garment_id in enumerate(body.garmentIds):
        db.add(OutfitGarment(
            outfitId=outfit.outfitId,
            garmentId=garment_id,
            position=pos,
        ))

    return {
        "outfitId": outfit.outfitId,
        "collectionName": outfit.collectionName,
        "message": "Outfit saved successfully.",
    }


@router.get("/outfits")
async def list_outfits(
    user_id: str = "demo-user",
    collection: str = None,
    db: AsyncSession = Depends(get_db),
):
    """List saved outfits, optionally filtered by collection."""
    query = select(Outfit).where(Outfit.userId == user_id)
    if collection:
        query = query.where(Outfit.collectionName == collection)
    result = await db.execute(query)
    outfits = result.scalars().all()
    return {
        "outfits": [
            {
                "outfitId": o.outfitId,
                "collectionName": o.collectionName,
                "compatibilityScore": o.compatibilityScore,
                "confidenceScore": o.confidenceScore,
                "explanation": o.explanation,
                "occasion": o.occasion,
                "createdAt": o.createdAt.isoformat(),
            }
            for o in outfits
        ]
    }
