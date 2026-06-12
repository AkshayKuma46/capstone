"""
garments.py — Garment CRUD routes
POST /garments         → add garment (with optional vision extraction)
GET  /garments         → list all garments in wardrobe
GET  /garments/{id}    → get single garment
PUT  /garments/{id}    → update garment
DELETE /garments/{id}  → delete garment
POST /garments/extract-from-image → vision model extraction
"""
import uuid
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from db.database import get_db
from db.models import Garment, GarmentOccasionTag, Wardrobe, User
from api.schemas import GarmentCreate, GarmentUpdate, GarmentOut, VisionExtractResponse
from vector_store.store import get_vector_store
from config import GEMINI_API_KEY, VISION_MODEL, DATA_DIR, UPLOADS_DIR

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/garments", tags=["garments"])

MAX_IMAGE_BYTES = 5 * 1024 * 1024   # 5 MB
ALLOWED_MIME = {"image/jpeg", "image/png", "image/jpg", "image/webp"}


# ── Helper: ensure wardrobe exists ────────────────────────────────────────────
async def _get_or_create_wardrobe(user_id: str, db: AsyncSession) -> Wardrobe:
    result = await db.execute(select(Wardrobe).where(Wardrobe.userId == user_id))
    wardrobe = result.scalar_one_or_none()
    if not wardrobe:
        # Auto-create user + wardrobe for dev convenience
        user_result = await db.execute(select(User).where(User.userId == user_id))
        user = user_result.scalar_one_or_none()
        if not user:
            user = User(userId=user_id, email=f"{user_id}@wardrobe.local", role="user")
            db.add(user)
        wardrobe = Wardrobe(wardrobeId=str(uuid.uuid4()), userId=user_id)
        db.add(wardrobe)
        await db.flush()
    return wardrobe


def _garment_to_dict(garment: Garment, request: Optional[Request] = None) -> dict:
    img = garment.imageUrl
    if img and "/static/uploads/" in img:
        filename = img.split("/static/uploads/")[-1]
        path = f"/static/uploads/{filename}"
        if request:
            base = str(request.base_url).rstrip("/")
            img = f"{base}{path}"
        else:
            img = f"http://localhost:8000{path}"
    return {
        "garmentId": garment.garmentId,
        "wardrobeId": garment.wardrobeId,
        "name": garment.name,
        "category": garment.category,
        "primaryColor": garment.primaryColor,
        "secondaryColor": garment.secondaryColor,
        "fabricType": garment.fabricType,
        "patternType": garment.patternType,
        "fitType": garment.fitType,
        "styleTag": garment.styleTag,
        "occasionTags": [t.tag for t in garment.occasion_tags],
        "imageUrl": img,
        "embeddingId": garment.embeddingId,
        "createdAt": garment.createdAt.isoformat(),
        "updatedAt": garment.updatedAt.isoformat(),
    }


# ── Vision Extraction ─────────────────────────────────────────────────────────
@router.post("/extract-from-image", response_model=VisionExtractResponse)
async def extract_from_image(request: Request, file: UploadFile = File(...)):
    """Extract garment attributes from an uploaded image using Vision Model."""
    # Validate file
    content_type = file.content_type or ""
    if content_type not in ALLOWED_MIME:
        raise HTTPException(
            status_code=415,
            detail=f"Only JPEG and PNG files are accepted. Got: {content_type}",
        )
    data = await file.read()
    if len(data) > MAX_IMAGE_BYTES:
        raise HTTPException(status_code=413, detail="File exceeds the 5 MB limit.")

    # Save the file permanently
    import uuid
    suffix = Path(file.filename or "").suffix or (".jpg" if content_type == "image/jpeg" else ".png")
    unique_filename = f"{uuid.uuid4().hex}{suffix}"
    upload_path = UPLOADS_DIR / unique_filename
    try:
        upload_path.write_bytes(data)
        image_url = f"{str(request.base_url).rstrip('/')}/static/uploads/{unique_filename}"
    except Exception as e:
        logger.error(f"[GarmentsRoute] Failed to save uploaded image: {e}")
        image_url = None

    if GEMINI_API_KEY:
        try:
            import google.generativeai as genai
            import base64
            genai.configure(api_key=GEMINI_API_KEY)
            model = genai.GenerativeModel(VISION_MODEL)

            prompt = """Analyze this clothing image and extract attributes as JSON:
{
  "name": "specific descriptive name (e.g. Beige Hoodie, Black Slim Jeans, Navy Cashmere Sweater)",
  "category": "top|bottom|outerwear|footwear|accessory|full_outfit",
  "primaryColor": "color name",
  "secondaryColor": "color name or null",
  "fabricType": "fabric type (e.g. cotton, wool, denim)",
  "patternType": "solid|stripes|checks|camo|graphic|floral|null",
  "fitType": "slim fit|regular fit|relaxed fit|oversized fit|null",
  "confidence": 0.0-1.0,
  "fieldConfidences": {"category": 0.9, "primaryColor": 0.95, ...}
}
Output only valid JSON, no other text."""

            image_part = {
                "inline_data": {
                    "mime_type": content_type,
                    "data": base64.b64encode(data).decode(),
                }
            }
            response = model.generate_content([prompt, image_part])
            import json, re
            text = response.text.strip()
            text = re.sub(r'^```(?:json)?\s*', '', text, flags=re.MULTILINE)
            text = re.sub(r'\s*```$', '', text, flags=re.MULTILINE)
            attrs = json.loads(text)

            low_conf_fields = [
                k for k, v in attrs.get("fieldConfidences", {}).items()
                if v < 0.6
            ]
            return VisionExtractResponse(
                name=attrs.get("name"),
                category=attrs.get("category", "top"),
                primaryColor=attrs.get("primaryColor", "unknown"),
                secondaryColor=attrs.get("secondaryColor"),
                fabricType=attrs.get("fabricType", "unknown"),
                patternType=attrs.get("patternType"),
                fitType=attrs.get("fitType"),
                confidence=attrs.get("confidence", 0.7),
                lowConfidenceFields=low_conf_fields,
                imageUrl=image_url,
            )
        except Exception as e:
            logger.error(f"[GarmentsRoute] Vision extraction failed: {e}")
            filename_stem = Path(file.filename).stem if file.filename else ""
            if filename_stem and filename_stem not in ("file", "confusion_matrix", "score_distribution", "image"):
                fallback_name = filename_stem.replace('_', ' ').replace('-', ' ').title()
            else:
                fallback_name = "New Garment"
            return VisionExtractResponse(
                name=fallback_name,
                category="top",
                primaryColor="unknown",
                secondaryColor=None,
                fabricType="unknown",
                patternType=None,
                fitType=None,
                confidence=0.0,
                lowConfidenceFields=["category", "primaryColor", "fabricType"],
                imageUrl=image_url,
            )
    else:
        # Mock response for development
        filename_stem = Path(file.filename).stem if file.filename else ""
        if filename_stem and filename_stem not in ("file", "confusion_matrix", "score_distribution", "image"):
            mock_name = filename_stem.replace('_', ' ').replace('-', ' ').title()
        else:
            mock_name = "Navy Blazer"
        return VisionExtractResponse(
            name=mock_name,
            category="top",
            primaryColor="navy",
            secondaryColor=None,
            fabricType="cotton",
            patternType="solid",
            fitType="regular fit",
            confidence=0.85,
            lowConfidenceFields=[],
            imageUrl=image_url,
        )


# ── POST /garments ─────────────────────────────────────────────────────────────
@router.post("", status_code=status.HTTP_201_CREATED)
async def create_garment(
    body: GarmentCreate,
    request: Request,
    user_id: str = "demo-user",    # In prod, extract from JWT
    db: AsyncSession = Depends(get_db),
):
    """Add a garment to the user's wardrobe."""
    wardrobe = await _get_or_create_wardrobe(user_id, db)

    # Normalize inputs to lowercase/trimmed to match database enums
    category_lower = body.category.strip().lower() if body.category else None
    primary_color_lower = body.primaryColor.strip().lower() if body.primaryColor else None
    
    secondary_color_lower = body.secondaryColor.strip().lower() if body.secondaryColor else None
    if secondary_color_lower == "":
        secondary_color_lower = None

    fit_type_lower = body.fitType.strip().lower() if body.fitType else None
    if fit_type_lower == "":
        fit_type_lower = None

    occasion_tags_lower = [t.strip().lower() for t in body.occasionTags if t.strip()]

    garment = Garment(
        garmentId=str(uuid.uuid4()),
        wardrobeId=wardrobe.wardrobeId,
        name=body.name,
        category=category_lower,
        primaryColor=primary_color_lower,
        secondaryColor=secondary_color_lower,
        fabricType=body.fabricType,
        patternType=body.patternType,
        fitType=fit_type_lower,
        styleTag=body.styleTag,
        imageUrl=body.imageUrl,
    )
    db.add(garment)
    await db.flush()

    for tag in occasion_tags_lower:
        db.add(GarmentOccasionTag(garmentId=garment.garmentId, tag=tag))
    await db.flush()

    # Async vector store update (within 10s SLA)
    try:
        garment_dict = {
            "garmentId": garment.garmentId,
            "name": garment.name,
            "category": garment.category,
            "primaryColor": garment.primaryColor,
            "fabricType": garment.fabricType,
            "fitType": garment.fitType or "",
            "styleTag": garment.styleTag or "",
            "occasionTags": occasion_tags_lower,
        }
        vs = get_vector_store()
        embedding_id = vs.add_garment(garment_dict, user_id)
        garment.embeddingId = embedding_id
    except Exception as e:
        logger.error(f"[GarmentsRoute] Vector store update failed for {garment.garmentId}: {e}")

    await db.refresh(garment)
    await db.refresh(garment, ["occasion_tags"])
    return _garment_to_dict(garment, request)


# ── GET /garments ──────────────────────────────────────────────────────────────
@router.get("")
async def list_garments(
    request: Request,
    user_id: str = "demo-user",
    category: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """List all garments in the user's wardrobe with optional filters."""
    wardrobe = await _get_or_create_wardrobe(user_id, db)

    query = select(Garment).where(Garment.wardrobeId == wardrobe.wardrobeId)
    if category:
        query = query.where(Garment.category == category)

    result = await db.execute(query)
    garments = result.scalars().all()

    garment_dicts = []
    for g in garments:
        await db.refresh(g, ["occasion_tags"])
        garment_dicts.append(_garment_to_dict(g, request))

    return {"garments": garment_dicts, "total": len(garment_dicts)}


# ── GET /garments/{id} ────────────────────────────────────────────────────────
@router.get("/{garment_id}")
async def get_garment(
    garment_id: str,
    request: Request,
    user_id: str = "demo-user",
    db: AsyncSession = Depends(get_db),
):
    wardrobe = await _get_or_create_wardrobe(user_id, db)
    result = await db.execute(
        select(Garment).where(
            Garment.garmentId == garment_id,
            Garment.wardrobeId == wardrobe.wardrobeId,
        )
    )
    garment = result.scalar_one_or_none()
    if not garment:
        raise HTTPException(status_code=404, detail="Garment not found")
    await db.refresh(garment, ["occasion_tags"])
    return _garment_to_dict(garment, request)


# ── PUT /garments/{id} ────────────────────────────────────────────────────────
@router.put("/{garment_id}")
async def update_garment(
    garment_id: str,
    body: GarmentUpdate,
    request: Request,
    user_id: str = "demo-user",
    db: AsyncSession = Depends(get_db),
):
    wardrobe = await _get_or_create_wardrobe(user_id, db)
    result = await db.execute(
        select(Garment).where(
            Garment.garmentId == garment_id,
            Garment.wardrobeId == wardrobe.wardrobeId,
        )
    )
    garment = result.scalar_one_or_none()
    if not garment:
        raise HTTPException(status_code=404, detail="Garment not found")

    update_data = body.model_dump(exclude_none=True)
    occasion_tags = update_data.pop("occasionTags", None)

    for field, value in update_data.items():
        if field == "category" and isinstance(value, str):
            value = value.strip().lower()
        elif field == "fitType" and isinstance(value, str):
            value = value.strip().lower()
            if value == "":
                value = None
        elif field in ("primaryColor", "secondaryColor") and isinstance(value, str):
            value = value.strip().lower()
            if value == "":
                value = None
        setattr(garment, field, value)

    if occasion_tags is not None:
        # Replace tags
        result2 = await db.execute(
            select(GarmentOccasionTag).where(GarmentOccasionTag.garmentId == garment_id)
        )
        for tag in result2.scalars().all():
            await db.delete(tag)
        for tag in occasion_tags:
            if tag.strip():
                db.add(GarmentOccasionTag(garmentId=garment_id, tag=tag.strip().lower()))

    await db.flush()

    # Update vector store embedding
    try:
        await db.refresh(garment, ["occasion_tags"])
        garment_dict = _garment_to_dict(garment, request)
        vs = get_vector_store()
        vs.update_garment(garment_dict, user_id)
    except Exception as e:
        logger.error(f"[GarmentsRoute] Vector store update failed: {e}")

    await db.refresh(garment, ["occasion_tags"])
    return _garment_to_dict(garment, request)


# ── DELETE /garments/{id} ─────────────────────────────────────────────────────
@router.delete("/{garment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_garment(
    garment_id: str,
    user_id: str = "demo-user",
    db: AsyncSession = Depends(get_db),
):
    wardrobe = await _get_or_create_wardrobe(user_id, db)
    result = await db.execute(
        select(Garment).where(
            Garment.garmentId == garment_id,
            Garment.wardrobeId == wardrobe.wardrobeId,
        )
    )
    garment = result.scalar_one_or_none()
    if not garment:
        raise HTTPException(status_code=404, detail="Garment not found")

    # Delete local photo from UPLOADS_DIR if it exists
    if garment.imageUrl:
        try:
            filename = garment.imageUrl.split("/static/uploads/")[-1]
            filepath = UPLOADS_DIR / filename
            if filepath.exists() and filepath.is_file():
                filepath.unlink()
                logger.info(f"[GarmentsRoute] Deleted image file: {filepath}")
        except Exception as e:
            logger.error(f"[GarmentsRoute] Failed to delete image file: {e}")

    # Delete from vector store
    try:
        vs = get_vector_store()
        vs.delete_garment(garment_id)
    except Exception as e:
        logger.error(f"[GarmentsRoute] Vector store delete failed: {e}")

    await db.delete(garment)
