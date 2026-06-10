"""
config.py — Central configuration for AI Wardrobe Stylist backend.
Loads settings from environment variables / .env file.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# ── Load .env from project root ──────────────────────────────────────────────
ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / ".env")

# ── API Keys ──────────────────────────────────────────────────────────────────
GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")

# ── Database ──────────────────────────────────────────────────────────────────
DATABASE_URL: str = os.getenv(
    "DATABASE_URL", "sqlite+aiosqlite:///./wardrobe.db"
)

# ── Vector Store ──────────────────────────────────────────────────────────────
VECTOR_STORE_BACKEND: str = os.getenv("VECTOR_STORE_BACKEND", "chroma")
CHROMA_PERSIST_DIR: Path = Path(
    os.getenv("CHROMA_PERSIST_DIR", str(ROOT_DIR / "chroma_db"))
)

# ── Embedding ─────────────────────────────────────────────────────────────────
EMBEDDING_BACKEND: str = os.getenv("EMBEDDING_BACKEND", "local")
# Local model: all-MiniLM-L6-v2 (384-dim), fast, no API key needed
LOCAL_EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
GEMINI_EMBEDDING_MODEL: str = "models/text-embedding-004"

# ── Paths ─────────────────────────────────────────────────────────────────────
RULE_CORPUS_DIR: Path = Path(os.getenv("RULE_CORPUS_DIR", str(ROOT_DIR / "data")))
MODELS_DIR: Path = Path(os.getenv("MODELS_DIR", str(ROOT_DIR / "models")))
DATA_DIR: Path = ROOT_DIR / "data"

# Ensure directories exist
CHROMA_PERSIST_DIR.mkdir(parents=True, exist_ok=True)
MODELS_DIR.mkdir(parents=True, exist_ok=True)
DATA_DIR.mkdir(parents=True, exist_ok=True)

# ── Retrieval ─────────────────────────────────────────────────────────────────
RAG_DEFAULT_K: int = 5
RAG_MIN_K: int = 1
RAG_MAX_K: int = 20
RAG_SIMILARITY_THRESHOLD: float = 0.7
RAG_LOW_CONFIDENCE_MIN_RESULTS: int = 3

# ── Scoring ───────────────────────────────────────────────────────────────────
LOW_CONFIDENCE_THRESHOLD: float = 0.6
TOP_N_OUTFITS: int = 3

# ── Chat ──────────────────────────────────────────────────────────────────────
CHAT_MAX_MESSAGE_CHARS: int = 1000
CHAT_HISTORY_WINDOW: int = 5       # last N user-assistant pairs sent to LLM

# ── LLM ──────────────────────────────────────────────────────────────────────
LLM_TIMEOUT_SECONDS: int = 8
LLM_MODEL: str = "gemini-1.5-flash"
VISION_MODEL: str = "gemini-1.5-flash"

# ── Retraining ────────────────────────────────────────────────────────────────
RETRAIN_MAX_SCORE_DELTA: float = 10.0   # alert if mean deviation > this

# ── Logging ───────────────────────────────────────────────────────────────────
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
APP_ENV: str = os.getenv("APP_ENV", "development")
