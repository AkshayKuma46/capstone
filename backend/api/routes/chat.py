"""
chat.py — Chat routes
POST /chat  → send a message, get outfit recommendations back
GET  /chat/sessions/{session_id}  → get session history
"""
import uuid
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from db.database import get_db
from db.models import Garment, Wardrobe, ChatSession, ChatMessage, User, GarmentOccasionTag
from api.schemas import ChatMessageIn, ChatMessageOut, OutfitCard
from api.routes.garments import _get_or_create_wardrobe, _garment_to_dict

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/chat", tags=["chat"])

# Lazy imports of heavy dependencies (initialized once in main.py)
_rag_pipeline = None

def get_rag_pipeline():
    global _rag_pipeline
    return _rag_pipeline

def set_rag_pipeline(pipeline):
    global _rag_pipeline
    _rag_pipeline = pipeline


@router.post("", response_model=ChatMessageOut)
async def chat(
    body: ChatMessageIn,
    db: AsyncSession = Depends(get_db),
):
    """Send a message and get styled outfit recommendations."""
    # ── Validate length (Property 9) ──────────────────────────────────────────
    if len(body.content) > 1000:
        raise HTTPException(
            status_code=400,
            detail="Message exceeds 1,000 character limit. Please shorten your message.",
        )

    user_id = body.userId

    # ── Get or create session ──────────────────────────────────────────────────
    session_id = body.sessionId
    if session_id:
        result = await db.execute(
            select(ChatSession).where(ChatSession.sessionId == session_id)
        )
        session = result.scalar_one_or_none()
        if not session:
            raise HTTPException(status_code=404, detail="Chat session not found")
    else:
        await _get_or_create_wardrobe(user_id, db)
        session = ChatSession(
            sessionId=str(uuid.uuid4()),
            userId=user_id,
        )
        db.add(session)
        await db.flush()
        session_id = session.sessionId

    # ── Save user message ──────────────────────────────────────────────────────
    user_msg = ChatMessage(
        messageId=str(uuid.uuid4()),
        sessionId=session_id,
        role="user",
        content=body.content,
    )
    db.add(user_msg)
    await db.flush()

    # ── Load conversation history (last 5 pairs = Property 10) ────────────────
    history_result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.sessionId == session_id)
        .order_by(ChatMessage.createdAt.desc())
        .limit(10)   # last 10 messages = 5 pairs
    )
    history_msgs = list(reversed(history_result.scalars().all()))
    conversation_history = [
        {"role": m.role, "content": m.content}
        for m in history_msgs
        if m.messageId != user_msg.messageId
    ]

    # ── Load user's wardrobe garments ──────────────────────────────────────────
    wardrobe = await _get_or_create_wardrobe(user_id, db)
    garment_result = await db.execute(
        select(Garment).where(Garment.wardrobeId == wardrobe.wardrobeId)
    )
    garments_orm = garment_result.scalars().all()
    garments = []
    for g in garments_orm:
        await db.refresh(g, ["occasion_tags"])
        garments.append(_garment_to_dict(g))

    # ── Run RAG Pipeline ───────────────────────────────────────────────────────
    pipeline = get_rag_pipeline()
    if not pipeline:
        raise HTTPException(status_code=503, detail="Styling service temporarily unavailable.")

    rag_result = pipeline.handle_query(
        session_id=session_id,
        user_id=user_id,
        user_query=body.content,
        garments=garments,
        conversation_history=conversation_history,
        occasion=body.occasion,
        k=body.k,
    )

    # ── Build assistant response ───────────────────────────────────────────────
    intent = rag_result.get("intent", "unknown")
    recommendations = rag_result.get("recommendations", [])
    clarifying = rag_result.get("clarifyingPrompt")
    error = rag_result.get("error")
    low_confidence = rag_result.get("lowConfidence", False)

    # Build response content
    if clarifying:
        response_content = clarifying
    elif error:
        response_content = "I encountered an issue processing your request. Please try again."
    elif recommendations:
        first = recommendations[0]
        if first.get("advice"):
            response_content = first["advice"]
        else:
            names = first.get("garmentNames", [])
            score = first.get("compatibilityScore", "N/A")
            response_content = (
                f"Here are your top outfit recommendations! "
                f"The best match scores {score}/100. "
                f"{first.get('explanation', '')}"
            )
        if low_confidence:
            response_content += " ⚠️ Low confidence — limited wardrobe data available."
    else:
        response_content = "No recommendations available. Try adding more garments to your wardrobe."

    # Serialize outfit cards
    outfit_cards = None
    if recommendations and recommendations[0].get("compatibilityScore") is not None:
        outfit_cards = [
            {
                "outfitId": r.get("outfitId"),
                "garmentNames": r.get("garmentNames"),
                "compatibilityScore": r.get("compatibilityScore"),
                "confidenceScore": r.get("confidenceScore"),
                "lowConfidence": r.get("lowConfidence", False),
                "explanation": r.get("explanation"),
                "explanationUnavailable": r.get("explanationUnavailable", False),
            }
            for r in recommendations
        ]

    # ── Save assistant message ─────────────────────────────────────────────────
    assistant_msg = ChatMessage(
        messageId=str(uuid.uuid4()),
        sessionId=session_id,
        role="assistant",
        content=response_content,
        intent=intent if intent != "unknown" else None,
        outfits=outfit_cards,
    )
    db.add(assistant_msg)
    await db.flush()

    return ChatMessageOut(
        messageId=assistant_msg.messageId,
        sessionId=session_id,
        role="assistant",
        content=response_content,
        intent=intent,
        outfits=[OutfitCard(**c) for c in (outfit_cards or [])],
        timestamp=assistant_msg.createdAt.isoformat(),
    )


@router.get("/sessions/{session_id}")
async def get_session(
    session_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Retrieve full chat session history."""
    result = await db.execute(
        select(ChatSession).where(ChatSession.sessionId == session_id)
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    await db.refresh(session, ["messages"])
    return {
        "sessionId": session.sessionId,
        "userId": session.userId,
        "createdAt": session.createdAt.isoformat(),
        "messages": [
            {
                "messageId": m.messageId,
                "role": m.role,
                "content": m.content,
                "intent": m.intent,
                "outfits": m.outfits,
                "timestamp": m.createdAt.isoformat(),
            }
            for m in session.messages
        ],
    }
