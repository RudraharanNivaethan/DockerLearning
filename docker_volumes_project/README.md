# Docker Volume Mini Project – Shared AI Model Repository

Create a Docker-based mini project that demonstrates persistent storage using Docker volumes or bind mounts.

## Requirements

- Store all AI models in `D:\ai_models` on the host machine.
- Models must be downloaded only once.
- If a model already exists, the application must reuse it instead of downloading it again.
- Multiple Docker projects and containers must be able to access the same model repository.
- Model files must not be included inside Docker images.
- The solution must survive container deletion, image rebuilds, and system restarts.
- Implement startup logic that:
  - Checks for the model in `/ai_models`
  - Downloads the model only if it is missing
  - Loads the existing model otherwise
- Demonstrate persistence by deleting and recreating containers without re-downloading the model.

## Host Storage

```text
D:\ai_models
├── mistral-7b-instruct.gguf
├── phi-3-mini.gguf
└── tinyllama.gguf
```

## Container Mount

```text
D:\ai_models  -->  /ai_models
```

## Web App

This project includes a FastAPI web app in [`app/`](app/) that downloads **TinyLlama** (~637 MB) on first run, loads it with `llama-cpp-python`, and serves a simple chat UI.

### Quick start

```powershell
mkdir D:\ai_models
cd docker_volumes_project\app
docker compose up --build
```

Open [http://localhost:8000](http://localhost:8000).

- **First run:** the app downloads `tinyllama.gguf` into `D:\ai_models`, then loads it.
- **Later runs:** the file already exists on disk — download is skipped, model loads directly.

> First Docker build may take 5–10 minutes (`llama-cpp-python` compiles C++). First model download adds ~637 MB.

### API

| Endpoint | Method | Description |
|---|---|---|
| `/` | GET | Chat UI |
| `/api/status` | GET | Model state, path, file size |
| `/api/generate` | POST | `{ "prompt": "...", "max_tokens": 128 }` → `{ "response": "..." }` |
| `/health` | GET | `{ "ready": true/false }` |

### Persistence demo

1. **First run** — open the UI, watch status go `Downloading` → `Ready`, send a chat prompt.
2. **Recreate container** — `docker compose down && docker compose up` — logs show "model found on disk"; no re-download.
3. **Rebuild image** — `docker compose down --rmi local && docker compose up --build` — image rebuilt, model still on `D:\ai_models`; no re-download.
4. **Cross-project sharing** — mount the same path in another container:

   ```bash
   docker run -v D:/ai_models:/ai_models -p 8001:8000 my-ai-app
   ```

### Project layout

```text
docker_volumes_project/
├── README.md
└── app/
    ├── Dockerfile
    ├── docker-compose.yaml
    ├── config.py
    ├── model_manager.py
    ├── main.py
    └── static/
        └── index.html
```

## Recommended Approach

Instead of a Docker-managed named volume, use a **bind mount** to a specific folder on `D:`. Bind mounts let you choose the exact host path, such as `D:\ai_models`, and share it with any container. Docker's documentation recommends bind mounts when you need direct access to files on the host filesystem. ([Docker Documentation](https://docs.docker.com/engine/storage/bind-mounts/))

**Create the folder:**

```powershell
mkdir D:\ai_models
```

**Docker run:**

```bash
docker run -v D:\ai_models:/ai_models my-ai-app
```

**Docker Compose:**

```yaml
services:
  ai-app:
    build: .
    volumes:
      - D:/ai_models:/ai_models
```

**Application logic:**

```python
MODEL_PATH = "/ai_models/tinyllama.gguf"

if not os.path.exists(MODEL_PATH):
    download_model()

load_model(MODEL_PATH)
```

## Benefits

| | |
|---|---|
| ✅ | Models stored on D: drive |
| ✅ | Download once, use forever |
| ✅ | Shared across all projects |
| ✅ | No model duplication in images |
| ✅ | Faster container startup |
| ✅ | Easy backup by copying `D:\ai_models` |

> For a mini project, using a small model such as **TinyLlama** or **Phi-3 Mini** is ideal — the download size is manageable while still demonstrating persistent model storage.

## Future extensions

The same `model_manager` pattern supports additional models (`phi-3-mini.gguf`, `mistral-7b-instruct.gguf`) by adding config entries and a model selector in the UI.
