import logging
import os
import shutil
import threading
from typing import Optional

from huggingface_hub import hf_hub_download
from llama_cpp import Llama

import config

logger = logging.getLogger(__name__)

_lock = threading.Lock()
_llama: Optional[Llama] = None
_state = "idle"
_error: Optional[str] = None


def _set_state(state: str, error: Optional[str] = None) -> None:
    global _state, _error
    _state = state
    _error = error


def _model_exists() -> bool:
    return os.path.isfile(config.MODEL_PATH) and os.path.getsize(config.MODEL_PATH) > 0


def _file_size_mb() -> Optional[float]:
    if not _model_exists():
        return None
    return round(os.path.getsize(config.MODEL_PATH) / (1024 * 1024), 2)


def get_status() -> dict:
    return {
        "state": _state,
        "model_path": config.MODEL_PATH,
        "exists_on_disk": _model_exists(),
        "file_size_mb": _file_size_mb(),
        "ready": _state == "ready",
        "error": _error,
    }


def _download_model() -> None:
    os.makedirs(config.MODEL_DIR, exist_ok=True)
    logger.info("Model not found at %s — downloading from HuggingFace", config.MODEL_PATH)
    _set_state("downloading")

    downloaded_path = hf_hub_download(
        repo_id=config.HF_REPO,
        filename=config.HF_FILENAME,
        local_dir=config.MODEL_DIR,
    )

    target = config.MODEL_PATH
    if os.path.abspath(downloaded_path) != os.path.abspath(target):
        if os.path.exists(target):
            os.remove(target)
        shutil.move(downloaded_path, target)

    logger.info("Download complete: %s (%.2f MB)", target, _file_size_mb())


def _load_model() -> None:
    global _llama
    logger.info("Loading model from %s", config.MODEL_PATH)
    _set_state("loading")
    _llama = Llama(
        model_path=config.MODEL_PATH,
        n_ctx=config.N_CTX,
        n_threads=config.N_THREADS,
        verbose=False,
    )
    logger.info("Model loaded and ready")
    _set_state("ready")


def ensure_ready() -> None:
    with _lock:
        if _state == "ready":
            return
        if _state in ("downloading", "loading"):
            return

        try:
            if not _model_exists():
                _download_model()
            else:
                logger.info("Model found on disk at %s — skipping download", config.MODEL_PATH)

            _load_model()
        except Exception as exc:
            logger.exception("Failed to prepare model")
            _set_state("error", str(exc))
            raise


def generate(prompt: str, max_tokens: int = config.DEFAULT_MAX_TOKENS) -> str:
    if _state != "ready" or _llama is None:
        raise RuntimeError(f"Model is not ready (state={_state})")

    result = _llama.create_chat_completion(
        messages=[{"role": "user", "content": prompt}],
        max_tokens=max_tokens,
        temperature=0.7,
    )
    return result["choices"][0]["message"]["content"]
