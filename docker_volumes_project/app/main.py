import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, Field

import config
import model_manager

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

STATIC_DIR = Path(__file__).parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up — checking model repository")
    try:
        model_manager.ensure_ready()
    except Exception:
        logger.error("Model initialization failed; API will report not-ready status")

    app.state.mongo = AsyncIOMotorClient(config.MONGO_URL)
    logger.info("MongoDB client connected")
    yield
    app.state.mongo.close()
    logger.info("MongoDB client closed")


app = FastAPI(title="AI Model Repository", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


class GenerateRequest(BaseModel):
    prompt: str = Field(..., min_length=1)
    max_tokens: int = Field(default=128, ge=1, le=512)


class GenerateResponse(BaseModel):
    response: str


@app.get("/")
async def index():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/status")
async def status():
    return model_manager.get_status()


@app.get("/health")
async def health():
    s = model_manager.get_status()
    return {"ready": s["ready"]}


@app.post("/api/generate", response_model=GenerateResponse)
async def generate(req: GenerateRequest, request: Request):
    s = model_manager.get_status()
    if not s["ready"]:
        raise HTTPException(status_code=503, detail=f"Model not ready (state={s['state']})")

    try:
        response_text = model_manager.generate(req.prompt, req.max_tokens)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    doc = {
        "prompt": req.prompt,
        "response": response_text,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    try:
        col = request.app.state.mongo[config.MONGO_DB][config.MONGO_COLLECTION]
        await col.insert_one(doc)
    except Exception:
        logger.exception("Failed to save history entry to MongoDB")

    return GenerateResponse(response=response_text)


@app.get("/api/history")
async def history(request: Request):
    col = request.app.state.mongo[config.MONGO_DB][config.MONGO_COLLECTION]
    docs = await col.find({}, {"_id": 0}).sort("timestamp", -1).limit(50).to_list(50)
    return docs
