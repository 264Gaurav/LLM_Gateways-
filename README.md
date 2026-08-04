# LLM Gateways and Production AI Patterns

This repository is a hands-on learning workspace for building modern LLM applications with LiteLLM, retrieval strategies, caching, reranking, observability, and guardrails. It combines practical examples, configuration files, and supporting notes for moving from prototype AI apps to production-ready systems.

## What this project covers

This repository demonstrates several important capabilities for real-world AI systems:

- Unified access to multiple LLM providers through a single gateway interface
- Model routing, fallbacks, and complexity-based selection
- Exact and semantic caching to reduce latency and cost
- Embedding model comparison and retrieval strategy design
- Re-ranking and fusion techniques for better RAG quality
- Guardrails for safety, validation, and policy enforcement
- Observability with Logfire and LangSmith
- Local Docker-based setup for a LiteLLM proxy

## Key capabilities

### 1. LLM Gateway and routing
The LiteLLM proxy setup provides a centralized gateway for routing requests across providers such as Gemini, OpenRouter, Groq, Nvidia, and GitHub Copilot.

### 2. Fallbacks and smart routing
The configuration includes tiered routing and fallback chains so requests can move smoothly between models when a provider is slow, rate-limited, or unavailable.

### 3. Caching
The repository includes examples and documentation for exact-match caching and semantic caching, which help reduce repeated LLM cost and improve response time.

### 4. Embeddings and retrieval
The repository includes material on embedding model selection, vector indexing, dense vs sparse retrieval, and hybrid retrieval approaches.

### 5. Re-ranking and fusion
The docs explain how reranking and fusion methods improve result quality in retrieval-based systems.

### 6. Guardrails
The guardrails section demonstrates policy-based checking and validation patterns for safer LLM use.

### 7. Observability
The setup includes tracing and monitoring examples using Logfire and LangSmith for request inspection and debugging.

## Repository structure

- [basics](basics) – introductory notebooks and notes for LLM gateway concepts
- [guardRails](guardRails) – guardrails examples, notes, and supporting scripts
- [litellm-setup](litellm-setup) – Dockerized LiteLLM proxy, config, and supporting documentation
- [requirements.txt](requirements.txt) – Python dependencies used across the project

## Learning path

Start with the most relevant document for your goal:

- [LLM_Gateway_README.md](basics/README.md) – high-level overview of LLM gateway concepts
- [Embedding_COMPARISON.md](litellm-setup/Embedding_COMPARISON.md) – embedding model selection and tradeoffs
- [RE_RANKING.md](litellm-setup/RE_RANKING.md) – reranking and retrieval quality strategies
- [Caching.md](litellm-setup/Caching.md) – caching options and recommendations
- [GuardRails.md](guardRails/Notes_drawing/GuardRails.md) – guardrails overview

## Quick start

### Prerequisites

- Python 3.10+ (recommended)
- Docker Desktop and Docker Compose
- API keys for the providers you want to use

### 1. Install Python dependencies

```bash
pip install -r requirements.txt
```

### 2. Create environment variables

Create a .env file in the repository root or inside [litellm-setup](litellm-setup) with the values you need, for example:

```env
GEMINI_API_KEY=your_key_here
OPENROUTER_API_KEY=your_key_here
GROQ_API_KEY=your_key_here
NVIDIA_API_KEY=your_key_here
LITELLM_MASTER_KEY=sk-master-key-12345
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=your_redis_password
DATABASE_URL=postgresql://postgres:postgres@postgres:5432/litellm
LOGFIRE_TOKEN=your_logfire_token
```

### 3. Start the LiteLLM stack

```bash
cd litellm-setup
docker compose up -d
```

Once running, the local gateway should be available at:

- LiteLLM proxy: http://localhost:4000
- LiteLLM UI: http://localhost:4000/ui
- Redis Insight: http://localhost:8001

### 4. Explore the examples

You can then run the notebooks and scripts in the repository to test routing, caching, embeddings, observability, and guardrails.

## Summary

This project is best understood as a practical reference for building an LLM gateway stack with:

- multi-provider access
- routing and failover
- caching and performance tuning
- retrieval and reranking strategies
- safety controls
- production-style observability
