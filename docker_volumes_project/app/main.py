import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

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
    yield


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
    status = model_manager.get_status()
    return {"ready": status["ready"]}


@app.post("/api/generate", response_model=GenerateResponse)
async def generate(req: GenerateRequest):
    status = model_manager.get_status()
    if not status["ready"]:
        raise HTTPException(status_code=503, detail=f"Model not ready (state={status['state']})")

    try:
        response = model_manager.generate(req.prompt, req.max_tokens)
        return GenerateResponse(response=response)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
