"""
admin.py — Admin routes (role-gated)
POST /admin/preprocess  → run Data_Preprocessor on uploaded file
POST /admin/extract     → run Knowledge_Extractor
POST /admin/retrain     → trigger XGBoost retraining
GET  /admin/corpus      → list corpus versions
GET  /admin/logs/{job_id} → get extraction log
"""
import uuid
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from db.database import get_db
from db.models import RuleCorpusVersion
from api.schemas import ExtractRequest, RetrainRequest, RetrainResponse
from config import DATA_DIR, RULE_CORPUS_DIR, MODELS_DIR, GEMINI_API_KEY

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/admin", tags=["admin"])

MAX_FILE_BYTES = 10 * 1024 * 1024    # 10 MB


@router.post("/preprocess")
async def preprocess_file(file: UploadFile = File(...)):
    """Upload and preprocess a raw fashion text file."""
    data = await file.read()
    if len(data) > MAX_FILE_BYTES:
        raise HTTPException(status_code=413, detail="File exceeds the 10 MB limit.")

    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in ('.txt', '.pdf'):
        raise HTTPException(
            status_code=415,
            detail=f"Only .txt and .pdf formats are accepted. Got: {suffix or 'unknown'}"
        )

    # Save upload
    upload_path = DATA_DIR / f"upload_{uuid.uuid4().hex}{suffix}"
    upload_path.write_bytes(data)

    try:
        from data_pipeline.preprocessor import preprocess
        output_dir = DATA_DIR / "preprocessed"
        cleaned_path, report = preprocess(upload_path, output_dir)
        return {
            "cleanedFile": str(cleaned_path),
            "report": {
                "inputFileName": report.inputFileName,
                "inputSizeBytes": report.inputSizeBytes,
                "outputSizeBytes": report.outputSizeBytes,
                "charactersRemoved": report.charactersRemoved,
                "wordCountAfterProcessing": report.wordCountAfterProcessing,
                "warnings": report.warnings,
                "processedAt": report.processedAt,
            },
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if upload_path.exists():
            upload_path.unlink()


@router.post("/extract")
async def extract_corpus(body: ExtractRequest, db: AsyncSession = Depends(get_db)):
    """Run Knowledge_Extractor on a preprocessed file."""
    cleaned_path = DATA_DIR / "preprocessed" / body.inputFile
    if not cleaned_path.exists():
        raise HTTPException(status_code=404, detail=f"File not found: {body.inputFile}")

    try:
        from data_pipeline.knowledge_extractor import extract
        output_dir = DATA_DIR / "corpora"
        corpus_path, job = extract(
            cleaned_text_path=cleaned_path,
            output_dir=output_dir,
            corpus_version=body.corpusVersion,
            api_key=GEMINI_API_KEY,
        )

        # Register corpus version in DB
        if job.status == "completed":
            corpus_data = json.loads(corpus_path.read_text())
            version_record = RuleCorpusVersion(
                version=body.corpusVersion,
                sourceHash=job.inputFileHash,
                ruleCount=job.ruleCount or 0,
                generatedAt=datetime.fromisoformat(job.completedAt),
                isActive=False,
            )
            db.add(version_record)

        return {
            "jobId": job.jobId,
            "status": job.status,
            "corpusVersion": job.corpusVersion,
            "ruleCount": job.ruleCount,
            "unresolvedCount": len(job.unresolvedPassages),
            "completedAt": job.completedAt,
        }
    except Exception as e:
        logger.error(f"[AdminRoute] Extraction failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/retrain", response_model=RetrainResponse)
async def retrain_model(body: RetrainRequest, db: AsyncSession = Depends(get_db)):
    """Trigger XGBoost retraining with the specified corpus version."""
    job_id = f"retrain-{uuid.uuid4().hex[:8]}"
    triggered_at = datetime.now(timezone.utc).isoformat()

    try:
        from ml.outfit_scorer import OutfitScorerModel
        rules_path = RULE_CORPUS_DIR / "rules.json"
        scorer = OutfitScorerModel(rules_path=rules_path, models_dir=MODELS_DIR)
        summary = scorer.train()

        return RetrainResponse(
            jobId=job_id,
            status="completed",
            corpusVersion=body.corpusVersion,
            triggeredAt=triggered_at,
        )
    except Exception as e:
        logger.error(f"[AdminRoute] Retraining failed: {e}")
        raise HTTPException(status_code=500, detail=f"Retraining failed: {e}")


@router.get("/corpus")
async def list_corpus_versions(db: AsyncSession = Depends(get_db)):
    """List all registered Rule Corpus versions."""
    result = await db.execute(select(RuleCorpusVersion))
    versions = result.scalars().all()
    return {
        "versions": [
            {
                "version": v.version,
                "ruleCount": v.ruleCount,
                "isActive": v.isActive,
                "generatedAt": v.generatedAt.isoformat() if v.generatedAt else None,
            }
            for v in versions
        ]
    }


@router.get("/logs")
async def list_logs():
    """List available extraction logs."""
    log_dir = DATA_DIR / "corpora"
    if not log_dir.exists():
        return {"logs": []}
    logs = [
        {"filename": f.name, "sizeBytes": f.stat().st_size}
        for f in log_dir.glob("extraction_log_*.json")
    ]
    return {"logs": logs}


@router.get("/logs/{job_id}")
async def get_log(job_id: str):
    """Get extraction log for a specific job."""
    log_dir = DATA_DIR / "corpora"
    log_path = log_dir / f"extraction_log_{job_id}.json"
    if not log_path.exists():
        raise HTTPException(status_code=404, detail="Log not found")
    return json.loads(log_path.read_text())
