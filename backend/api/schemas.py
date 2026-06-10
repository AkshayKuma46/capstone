"""
schemas.py — Phase 5: Pydantic request/response schemas for the FastAPI API.
Matches TypeScript interfaces in design.md.
"""
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator
import uuid


# ── Garment ───────────────────────────────────────────────────────────────────
class GarmentCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    category: str
    primaryColor: str
    secondaryColor: Optional[str] = None
    fabricType: str
    patternType: Optional[str] = None
    fitType: Optional[str] = None
    styleTag: Optional[str] = None
    occasionTags: List[str] = Field(..., min_length=1)
    imageUrl: Optional[str] = None

    @field_validator("occasionTags")
    @classmethod
    def at_least_one_tag(cls, v):
        if not v:
            raise ValueError("At least one occasionTag is required")
        return v


class GarmentUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    category: Optional[str] = None
    primaryColor: Optional[str] = None
    secondaryColor: Optional[str] = None
    fabricType: Optional[str] = None
    patternType: Optional[str] = None
    fitType: Optional[str] = None
    styleTag: Optional[str] = None
    occasionTags: Optional[List[str]] = None
    imageUrl: Optional[str] = None


class GarmentOut(BaseModel):
    garmentId: str
    wardrobeId: str
    name: str
    category: str
    primaryColor: str
    secondaryColor: Optional[str]
    fabricType: str
    patternType: Optional[str]
    fitType: Optional[str]
    styleTag: Optional[str]
    occasionTags: List[str]
    imageUrl: Optional[str]
    embeddingId: Optional[str]
    createdAt: str
    updatedAt: str

    class Config:
        from_attributes = True


# ── Outfit ────────────────────────────────────────────────────────────────────
class OutfitCard(BaseModel):
    outfitId: Optional[str]
    garmentIds: Optional[List[str]] = None
    garmentNames: Optional[List[str]] = None
    compatibilityScore: Optional[int] = None    # 0-100 or -1
    confidenceScore: Optional[float] = None
    lowConfidence: Optional[bool] = None
    explanation: Optional[str] = None
    explanationUnavailable: Optional[bool] = False
    corpusVersion: Optional[str] = None
    occasion: Optional[str] = None
    advice: Optional[str] = None                # for non-outfit-suggestion responses


class SaveOutfitRequest(BaseModel):
    outfitId: str
    collectionName: str = Field(..., min_length=1, max_length=50)
    garmentIds: List[str]
    occasion: Optional[str] = None
    compatibilityScore: Optional[int] = None
    confidenceScore: Optional[float] = None
    explanation: Optional[str] = None
    corpusVersion: Optional[str] = None


# ── Recommend ─────────────────────────────────────────────────────────────────
class RecommendRequest(BaseModel):
    userId: str
    occasion: str
    k: int = Field(default=5, ge=1, le=20)


class RecommendResponse(BaseModel):
    recommendations: List[OutfitCard]
    lowConfidence: bool
    requestId: str
    corpusVersion: str


# ── Chat ──────────────────────────────────────────────────────────────────────
class ChatMessageIn(BaseModel):
    sessionId: Optional[str] = None   # create new if None
    userId: str
    content: str = Field(..., max_length=1000)
    occasion: Optional[str] = None
    k: int = Field(default=5, ge=1, le=20)


class ChatMessageOut(BaseModel):
    messageId: str
    sessionId: str
    role: str
    content: str
    intent: Optional[str]
    outfits: Optional[List[OutfitCard]]
    timestamp: str


# ── Vision ────────────────────────────────────────────────────────────────────
class VisionExtractResponse(BaseModel):
    category: str
    primaryColor: str
    secondaryColor: Optional[str]
    fabricType: str
    patternType: Optional[str]
    fitType: Optional[str]
    confidence: float
    lowConfidenceFields: List[str]    # fields with confidence < 0.6
    imageUrl: Optional[str] = None


# ── Admin ─────────────────────────────────────────────────────────────────────
class ExtractRequest(BaseModel):
    corpusVersion: str
    inputFile: str     # filename of already-uploaded + preprocessed file


class RetrainRequest(BaseModel):
    corpusVersion: str


class RetrainResponse(BaseModel):
    jobId: str
    status: str
    corpusVersion: str
    triggeredAt: str


# ── Common ────────────────────────────────────────────────────────────────────
class ErrorResponse(BaseModel):
    code: str
    message: str
    requestId: Optional[str] = None
    missingFields: Optional[List[str]] = None
