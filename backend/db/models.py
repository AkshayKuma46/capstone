"""
models.py — Phase 3: SQLAlchemy ORM models

Tables: USER, WARDROBE, GARMENT, GARMENT_OCCASION_TAG, OUTFIT, OUTFIT_GARMENT,
        CHAT_SESSION, CHAT_MESSAGE, RULE_CORPUS_VERSION

Matches the ER diagram in design.md §Data Models.
"""

import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column, String, Integer, Float, Boolean, Text,
    ForeignKey, DateTime, JSON, Enum as SAEnum
)
from sqlalchemy.orm import relationship
from .database import Base

# ── Enums ─────────────────────────────────────────────────────────────────────
GARMENT_CATEGORIES = ["top", "bottom", "outerwear", "footwear", "accessory", "full_outfit"]
OCCASION_TAGS = [
    "casual", "formal", "business casual", "outdoor", "sport",
    "date night", "travel", "festival", "wedding", "everyday"
]
FIT_TYPES = [
    "slim fit", "regular fit", "relaxed fit", "oversized fit",
    "tailored fit", "skinny fit", "athletic fit", "loose fit", "wide fit"
]
USER_ROLES = ["user", "admin"]
CHAT_ROLES = ["user", "assistant"]
JOB_STATUSES = ["queued", "running", "completed", "failed"]
QUERY_INTENTS = [
    "outfit_suggestion", "color_pairing", "fabric_pairing",
    "wardrobe_gap_analysis", "style_tips", "unknown"
]


def _uuid():
    return str(uuid.uuid4())

def _now():
    return datetime.now(timezone.utc)


# ── USER ──────────────────────────────────────────────────────────────────────
class User(Base):
    __tablename__ = "users"

    userId = Column(String, primary_key=True, default=_uuid)
    email = Column(String, unique=True, nullable=False, index=True)
    role = Column(SAEnum(*USER_ROLES, name="user_role"), default="user", nullable=False)
    createdAt = Column(DateTime(timezone=True), default=_now, nullable=False)

    wardrobe = relationship("Wardrobe", back_populates="user", uselist=False, cascade="all, delete-orphan")
    outfits = relationship("Outfit", back_populates="user", cascade="all, delete-orphan")
    chat_sessions = relationship("ChatSession", back_populates="user", cascade="all, delete-orphan")


# ── WARDROBE ──────────────────────────────────────────────────────────────────
class Wardrobe(Base):
    __tablename__ = "wardrobes"

    wardrobeId = Column(String, primary_key=True, default=_uuid)
    userId = Column(String, ForeignKey("users.userId", ondelete="CASCADE"), nullable=False, unique=True)
    updatedAt = Column(DateTime(timezone=True), default=_now, onupdate=_now, nullable=False)

    user = relationship("User", back_populates="wardrobe")
    garments = relationship("Garment", back_populates="wardrobe", cascade="all, delete-orphan")


# ── GARMENT ───────────────────────────────────────────────────────────────────
class Garment(Base):
    __tablename__ = "garments"

    garmentId = Column(String, primary_key=True, default=_uuid)
    wardrobeId = Column(String, ForeignKey("wardrobes.wardrobeId", ondelete="CASCADE"), nullable=False)
    name = Column(String(100), nullable=False)
    category = Column(SAEnum(*GARMENT_CATEGORIES, name="garment_category"), nullable=False)
    primaryColor = Column(String(50), nullable=False)
    secondaryColor = Column(String(50), nullable=True)
    fabricType = Column(String(100), nullable=False)
    patternType = Column(String(50), nullable=True)
    fitType = Column(SAEnum(*FIT_TYPES, name="fit_type"), nullable=True)
    styleTag = Column(String(100), nullable=True)
    imageUrl = Column(String(500), nullable=True)
    embeddingId = Column(String, nullable=True)
    createdAt = Column(DateTime(timezone=True), default=_now, nullable=False)
    updatedAt = Column(DateTime(timezone=True), default=_now, onupdate=_now, nullable=False)

    wardrobe = relationship("Wardrobe", back_populates="garments")
    occasion_tags = relationship("GarmentOccasionTag", back_populates="garment", cascade="all, delete-orphan")
    outfit_links = relationship("OutfitGarment", back_populates="garment")


# ── GARMENT_OCCASION_TAG ──────────────────────────────────────────────────────
class GarmentOccasionTag(Base):
    __tablename__ = "garment_occasion_tags"

    id = Column(Integer, primary_key=True, autoincrement=True)
    garmentId = Column(String, ForeignKey("garments.garmentId", ondelete="CASCADE"), nullable=False)
    tag = Column(SAEnum(*OCCASION_TAGS, name="occasion_tag"), nullable=False)

    garment = relationship("Garment", back_populates="occasion_tags")


# ── OUTFIT ────────────────────────────────────────────────────────────────────
class Outfit(Base):
    __tablename__ = "outfits"

    outfitId = Column(String, primary_key=True, default=_uuid)
    userId = Column(String, ForeignKey("users.userId", ondelete="CASCADE"), nullable=False)
    occasion = Column(SAEnum(*OCCASION_TAGS, name="outfit_occasion_tag"), nullable=True)
    collectionName = Column(String(50), nullable=True)
    compatibilityScore = Column(Integer, nullable=True)     # 0-100 or -1
    confidenceScore = Column(Float, nullable=True)          # 0.0-1.0
    explanation = Column(Text, nullable=True)               # 20-100 words
    corpusVersion = Column(String(20), nullable=True)
    featureVector = Column(JSON, nullable=True)             # stored OutfitFeatureVector
    createdAt = Column(DateTime(timezone=True), default=_now, nullable=False)

    user = relationship("User", back_populates="outfits")
    garment_links = relationship("OutfitGarment", back_populates="outfit", cascade="all, delete-orphan",
                                 order_by="OutfitGarment.position")


# ── OUTFIT_GARMENT ─────────────────────────────────────────────────────────────
class OutfitGarment(Base):
    __tablename__ = "outfit_garments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    outfitId = Column(String, ForeignKey("outfits.outfitId", ondelete="CASCADE"), nullable=False)
    garmentId = Column(String, ForeignKey("garments.garmentId", ondelete="CASCADE"), nullable=False)
    position = Column(Integer, nullable=False)   # 0=top,1=bottom,2=footwear,3=outerwear,4=accessory

    outfit = relationship("Outfit", back_populates="garment_links")
    garment = relationship("Garment", back_populates="outfit_links")


# ── CHAT_SESSION ──────────────────────────────────────────────────────────────
class ChatSession(Base):
    __tablename__ = "chat_sessions"

    sessionId = Column(String, primary_key=True, default=_uuid)
    userId = Column(String, ForeignKey("users.userId", ondelete="CASCADE"), nullable=False)
    createdAt = Column(DateTime(timezone=True), default=_now, nullable=False)
    updatedAt = Column(DateTime(timezone=True), default=_now, onupdate=_now, nullable=False)

    user = relationship("User", back_populates="chat_sessions")
    messages = relationship("ChatMessage", back_populates="session",
                            cascade="all, delete-orphan", order_by="ChatMessage.createdAt")


# ── CHAT_MESSAGE ──────────────────────────────────────────────────────────────
class ChatMessage(Base):
    __tablename__ = "chat_messages"

    messageId = Column(String, primary_key=True, default=_uuid)
    sessionId = Column(String, ForeignKey("chat_sessions.sessionId", ondelete="CASCADE"), nullable=False)
    role = Column(SAEnum(*CHAT_ROLES, name="chat_role"), nullable=False)
    content = Column(Text, nullable=False)
    intent = Column(SAEnum(*QUERY_INTENTS, name="query_intent"), nullable=True)
    outfits = Column(JSON, nullable=True)    # serialized list of Outfit dicts on assistant messages
    createdAt = Column(DateTime(timezone=True), default=_now, nullable=False)

    session = relationship("ChatSession", back_populates="messages")


# ── RULE_CORPUS_VERSION ────────────────────────────────────────────────────────
class RuleCorpusVersion(Base):
    __tablename__ = "rule_corpus_versions"

    version = Column(String(20), primary_key=True)
    sourceHash = Column(String(64), nullable=False)
    ruleCount = Column(Integer, nullable=False)
    generatedAt = Column(DateTime(timezone=True), nullable=False)
    isActive = Column(Boolean, default=False, nullable=False)
