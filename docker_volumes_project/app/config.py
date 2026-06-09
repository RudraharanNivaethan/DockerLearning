import os

MODEL_DIR = os.environ.get("MODEL_DIR", "/ai_models")
MODEL_FILENAME = "tinyllama.gguf"
MODEL_PATH = os.path.join(MODEL_DIR, MODEL_FILENAME)

HF_REPO = "TheBloke/TinyLlama-1.1B-Chat-v1.0-GGUF"
HF_FILENAME = "tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf"

N_CTX = 2048
N_THREADS = 4
DEFAULT_MAX_TOKENS = 128
