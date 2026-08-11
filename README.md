# LLM Gateways, Guardrails, Semantic Caching Experimentation:

A hands-on workspace for building and experimenting with production-oriented LLM systems using **LiteLLM, FastAPI, Guardrails, model routing, fallbacks, caching, embeddings, reranking, and observability**.

This repository provides a complete local stack:

```text
Streamlit UI
     │
     ▼
FastAPI Gateway
     │
     ├── Guardrails + LiteLLM
     │
     └── Direct LiteLLM
              │
              ▼
       Multiple LLM Providers
```

---

## Features

- Unified LLM access through LiteLLM
- Guardrails-based request validation and safety checks
- Direct LiteLLM chat and embeddings paths for comparison
- Streaming chat responses
- Exact and semantic caching concepts
- Embedding model comparison
- Fallback and routing patterns
- Observability with Logfire and LangSmith support
- FastAPI application gateway
- Streamlit interactive client
- Docker Compose-based LiteLLM infrastructure
- One-command startup via `scripts/dev.py` or `start.bat`

---

## Repository Structure

```text
LLM_Gateways/
│
├── basics/                  # Gateway concept notes and examples
│   └── README.md
│
├── client/                  # Streamlit frontend
│   ├── streamlit.py
│   └── README.md
│
├── guardRails/              # Guardrails config, notebooks, logs
│   ├── config/
│   ├── guardrails_basic.ipynb
│   └── Notes_drawing/
│       └── GuardRails.md
│
├── litellm-setup/           # LiteLLM proxy configuration and docs
│   ├── docker-compose.yml
│   ├── Caching.md
│   ├── Embedding_COMPARISON.md
│   ├── RE_RANKING.md
│   └── litellm_config.yaml
│
├── scripts/
│   └── dev.py
│
├── server/
│   ├── logger.py
│   └── main.py
│
├── .env.example
├── .python-version
├── pyproject.toml
├── requirements.txt
├── start.bat
└── README.md
```

---

## Prerequisites

Install:

- **Python 3.13+**
- **uv**
- **Docker Desktop**
- **Docker Compose**
- API keys for the providers you want to use

The repository uses `uv` for environment and dependency management.

> The current project configuration requires Python `>=3.13`.

---

## Quick Start

### 1. Clone the repo

```bash
git clone <repository-url>
cd LLM_Gateways
```

### 2. Create and sync the uv environment

```bash
uv sync
```

This creates or updates:

```text
.venv/
uv.lock
```

### 3. Install dependencies

```bash
uv pip install -r requirements.txt
```

### 4. Configure environment variables

Copy the example env file and update the values you need:

```bash
copy .env.example .env
```

Set provider and LiteLLM variables in `.env`.

---

## Development Startup

Start the full local stack from the repository root:

```bash
uv run python scripts/dev.py
```

On Windows you can also use:

```powershell
.\start.bat
```

This launcher starts:

1. LiteLLM Docker stack
2. Waits for LiteLLM to become available
3. Starts the FastAPI gateway
4. Waits for `http://localhost:8000/health`
5. Starts the Streamlit UI

---

## Manual Startup

### LiteLLM

```bash
cd litellm-setup
docker compose up -d
```

Then return to the repo root:

```bash
cd ..
```

### FastAPI

```bash
uv run uvicorn server.main:app --host 0.0.0.0 --port 8000 --reload
```

Health check:

```bash
curl http://localhost:8000/health
```

### Streamlit

```bash
uv run streamlit run client/streamlit.py
```

Open the UI at:

```text
http://localhost:8501
```

---

## Gateway Endpoints

### Guardrails + LiteLLM

- `POST /ai/llms`
- alias: `POST /v1/chat/completions`

This path runs user input through Guardrails before sending it to LiteLLM.

### Direct LiteLLM

- `POST /ai/litellm/chat`
- alias: `POST /v1/litellm/chat/completions`

This path bypasses Guardrails and forwards the request directly to the LiteLLM proxy.

### Embeddings

- Gateway embeddings: `POST /ai/embeddings`
- alias: `POST /v1/embeddings`

- Direct LiteLLM embeddings: `POST /ai/litellm/embeddings`
- alias: `POST /v1/litellm/embeddings`

### Health

- `GET /health`

---

## What the FastAPI Server Does

The FastAPI app is implemented in `server/main.py`.

It includes:

- request sanitization for secrets and PII
- Guardrails validation via `guardRails/config`
- streaming LiteLLM chat support
- direct LiteLLM chat and embedding proxy routes
- fallback behavior when Guardrails are unavailable

---

## Streamlit Client

The client is implemented in `client/streamlit.py`.

The UI lets you:

- switch between `Guardrails + LiteLLM` and `Direct LiteLLM`
- send chat requests with streaming responses
- generate embeddings
- preview raw API payloads
- export conversation history

See `client/README.md` for usage details.

---

## Notes and Documentation

- [Gateway fundamentals and architecture](basics/README.md)
- [Streamlit client setup and usage](client/README.md)
- [Embedding comparison and guidance](litellm-setup/Embedding_COMPARISON.md)
- [Re-ranking and fusion notes](litellm-setup/RE_RANKING.md)
- [Caching tradeoffs and patterns](litellm-setup/Caching.md)
- [Guardrails concepts and policy notes](guardRails/Notes_drawing/GuardRails.md)

---

## Common Commands

```bash
uv sync
uv pip install -r requirements.txt
uv run python scripts/dev.py
uv run uvicorn server.main:app --host 0.0.0.0 --port 8000 --reload
uv run streamlit run client/streamlit.py
```

LiteLLM manual commands:

```bash
cd litellm-setup
docker compose up -d
docker compose down
```

---

## Troubleshooting

### `ModuleNotFoundError`

If a dependency is missing, install it in the uv environment:

```bash
uv pip install -r requirements.txt
```

Verify with:

```bash
uv run python -c "import nemoguardrails; print('Guardrails OK')"
```

### Wrong Python Version

Verify the interpreter:

```bash
uv run python --version
```

The project requires:

```text
pyproject.toml: requires-python = ">=3.13"
```

### FastAPI Cannot Connect to LiteLLM

Check LiteLLM on:

```bash
http://localhost:4000
```

or:

```bash
cd litellm-setup
docker compose ps
```

Inspect logs:

```bash
docker compose logs -f
```

### FastAPI Health Check Fails

Check:

```bash
http://localhost:8000/health
```

### Port Conflicts

Default ports:

| Service | Port |
|---|---:|
| LiteLLM | `4000` |
| FastAPI | `8000` |
| Streamlit | `8501` |
| Redis Insight | `8001` |

---

## Summary

This repository provides a local, modular LLM gateway environment combining:

- **uv** for Python environment management
- **Docker Compose** for LiteLLM infrastructure
- **FastAPI** for the gateway
- **LiteLLM** for provider routing and fallback behavior
- **Guardrails** for input validation and policy enforcement
- **Streamlit** for interactive experimentation
- **Logfire / LangSmith** for observability

For normal development:

```bash
uv run python scripts/dev.py
```

On Windows:

```powershell
.\start.bat
```
