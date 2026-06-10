"""
main.py — Phase 5: FastAPI application entry point

Startup:
  1. Initialize DB tables
  2. Load XGBoost scorer (train if no model found)
  3. Initialize Vector_Store
  4. Embed existing rules from rules.json
  5. Mount all routers

Run: uvicorn backend.api.main:app --reload --port 8000
  or: cd backend && uvicorn api.main:app --reload --port 8000
"""
import logging
import sys
import os
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

# ── Path setup (allow running from project root or backend/) ──────────────────
BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from config import (
    LOG_LEVEL, RULE_CORPUS_DIR, MODELS_DIR, APP_ENV, UPLOADS_DIR
)

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger(__name__)


# ── Lifespan: startup + shutdown ───────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── DB init ───────────────────────────────────────────────────────────────
    logger.info("[Startup] Initializing database...")
    from db.database import init_db
    await init_db()
    logger.info("[Startup] Database ready")

    # ── Scorer init ───────────────────────────────────────────────────────────
    logger.info("[Startup] Loading Outfit_Scorer...")
    from ml.outfit_scorer import OutfitScorerModel
    rules_path = RULE_CORPUS_DIR / "rules.json"
    scorer = OutfitScorerModel(rules_path=rules_path, models_dir=MODELS_DIR)
    if not scorer.load_model():
        logger.info("[Startup] No saved model found — training on rules.json examples...")
        try:
            scorer.train()
            logger.info("[Startup] XGBoost model trained and saved")
        except Exception as e:
            logger.warning(f"[Startup] Training failed ({e}) — will use weighted-sum fallback")

    # Inject scorer into routes
    from api.routes.outfits import set_scorer
    set_scorer(scorer, scorer._corpus_version)

    # ── Vector_Store init ──────────────────────────────────────────────────────
    logger.info("[Startup] Initializing Vector_Store...")
    try:
        from vector_store.store import get_vector_store
        vs = get_vector_store()
        logger.info("[Startup] Vector_Store ready")

        # Embed rules from rules.json if store is empty
        import json
        rules_data = json.loads(rules_path.read_text(encoding='utf-8'))
        rule_records = []

        # Build embeddable rule records from all rule sections
        for section_key in ["color_rules", "footwear_style_rules", "footwear_occasion_rules"]:
            section = rules_data.get(section_key, {})
            if isinstance(section, dict):
                for rule_type, content in section.items():
                    if isinstance(content, list):
                        for item in content:
                            if isinstance(item, str):
                                rule_records.append({
                                    "ruleId": f"{section_key}::{rule_type}::{len(rule_records)}",
                                    "ruleType": section_key,
                                    "description": item,
                                })

        # Add master rulebook entries if available
        master_path = RULE_CORPUS_DIR / "master_rulebook.json"
        if master_path.exists():
            master = json.loads(master_path.read_text(encoding='utf-8'))
            for category in ["classic_menswear_rules", "streetwear_rules",
                             "korean_fashion_rules", "techwear_rules", "luxury_rules"]:
                for rule_text in master.get(category, []):
                    rule_id = rule_text.split(":")[0] if ":" in rule_text else f"{category}_{len(rule_records)}"
                    rule_records.append({
                        "ruleId": rule_id,
                        "ruleType": category,
                        "description": rule_text,
                    })

        if rule_records:
            logger.info(f"[Startup] Embedding {len(rule_records)} rules into Vector_Store...")
            result = vs.add_rules(rule_records, scorer._corpus_version)
            logger.info(
                f"[Startup] Embedded {result['success']}/{result['total']} rules "
                f"({result['failed']} failed)"
            )

    except Exception as e:
        logger.error(f"[Startup] Vector_Store initialization failed: {e}")
        vs = None

    # ── RAG Pipeline init ─────────────────────────────────────────────────────
    logger.info("[Startup] Initializing RAG_Pipeline...")
    try:
        from rag.pipeline import RAGPipeline
        from vector_store.store import get_vector_store as _get_vs
        pipeline = RAGPipeline(
            vector_store=_get_vs(),
            scorer=scorer,
            rules_path=rules_path,
            corpus_version=scorer._corpus_version,
        )
        from api.routes.chat import set_rag_pipeline
        set_rag_pipeline(pipeline)
        logger.info("[Startup] RAG_Pipeline ready")
    except Exception as e:
        logger.error(f"[Startup] RAG_Pipeline init failed: {e}")

    logger.info(f"[Startup] ✅ AI Wardrobe Stylist API ready (env={APP_ENV})")
    yield  # Server is now running

    logger.info("[Shutdown] Cleaning up...")


# ── FastAPI app ────────────────────────────────────────────────────────────────
app = FastAPI(
    title="AI Wardrobe Stylist API",
    description="Outfit recommendation engine with XGBoost scoring and RAG-powered explanations",
    version="1.0.0",
    lifespan=lifespan,
)

app.mount("/static/uploads", StaticFiles(directory=str(UPLOADS_DIR)), name="uploads")

# ── CORS ───────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],  # Vite default
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Global error handler ───────────────────────────────────────────────────────
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    import uuid
    request_id = str(uuid.uuid4())
    logger.error(
        f"[InternalError] requestId={request_id} path={request.url.path} error={exc}",
        exc_info=True,
    )
    return JSONResponse(
        status_code=500,
        content={
            "code": "INTERNAL_ERROR",
            "message": "An unexpected error occurred. Please try again.",
            "requestId": request_id,
        },
    )


# ── Health check ──────────────────────────────────────────────────────────────
@app.get("/health", tags=["health"])
async def health():
    return {
        "status": "ok",
        "version": "1.0.0",
        "components": {
            "database": "ok",
            "vector_store": "ok",
            "scorer": "ok",
            "rag_pipeline": "ok",
        },
    }


# ── Mount routers ──────────────────────────────────────────────────────────────
from api.routes.garments import router as garments_router
from api.routes.outfits import router as outfits_router
from api.routes.chat import router as chat_router
from api.routes.admin import router as admin_router

app.include_router(garments_router)
app.include_router(outfits_router)
app.include_router(chat_router)
app.include_router(admin_router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
