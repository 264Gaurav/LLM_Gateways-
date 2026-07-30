# This Project contains - Litellm implementation and uses. Along with that Embedding, different Indexing/Searching strategies, ReRanking , Fusion strategy , Selection of Embedding models and their impact: 

## LiteLLM - LLM Gateway (ai gateway): See basics here 
[LiteLLM](/basics/README.md)

## Learn about Different Embedding models selection as per need, use cases and by knowing their limitation/tradeoffs: 
[Embedding_and_Indexing_Strategies](/litellm-setup/Embedding_COMPARISON.md)

## Learn about different strategy of Re-Ranking (After First stage of Retrival - ReRanking is important to achieve context precision):
[ReRanking](/litellm-setup/RE_RANKING.md)

## Learn about Caching Strategies in LiteLLM (LLM Gateways) and their selection: 
[Caching](/litellm-setup/Caching.md)


## LiteLLM Setup - with docker (medium to advanced)
This repository provides a complete local setup for a [LiteLLM Proxy](https://docs.litellm.ai/docs/proxy/quick_start) with a PostgreSQL database. It enables routing, load balancing, cost tracking, and unified access to multiple LLM providers through a standard OpenAI-compatible API.

## Features

- **Centralized LLM Gateway**: Access multiple providers (Gemini, OpenRouter, Nvidia, GitHub Copilot, etc.) via a single endpoint.
- **Smart Routing & Fallbacks**: Configure complex routing rules based on model performance or pricing.
- **Database Backend**: PostgreSQL is included for tracking usage, users, and analytics.

## Getting Started

### Prerequisites
- Docker and Docker Compose
- Provider API keys (e.g., GEMINI_API_KEY, OPENROUTER_API_KEY, NVIDIA_API_KEY)

### Installation

1. Clone the repository and navigate into it:
   ```bash
   cd litellm-setup
   ```

2. Create a `.env` file based on your needed API keys:
   ```bash
   touch .env
   # Add your keys: GEMINI_API_KEY=..., OPENROUTER_API_KEY=..., etc.
   ```

3. Start the services:
   ```bash
   docker compose up -d
   ```

LiteLLM will be available at `http://localhost:4000`.

## GitHub Copilot OAuth Token for LiteLLM

Use this when you run `github_copilot/*` models in LiteLLM Proxy.

### Why this is needed

- LiteLLM `github_copilot/*` does not use a `github_pat_*` PAT directly.
- It needs a Copilot OAuth token generated through GitHub Device Flow.
- The token is stored in `copilot_tokens/access-token` and mounted into the container.

### One-time setup

1. Make sure Docker volume mapping exists in `docker-compose.yml`:

```yaml
services:
  litellm:
    volumes:
      - ./copilot_tokens:/root/.config/litellm/github_copilot
    environment:
      GITHUB_COPILOT_TOKEN_DIR: /root/.config/litellm/github_copilot
```

2. Create the local token directory:

```bash
mkdir -p ./copilot_tokens
```

3. Trigger Device Flow from host (this prints a login code):

```bash
GITHUB_COPILOT_TOKEN_DIR=$(pwd)/copilot_tokens \
python3 -c "
from litellm import completion
resp = completion(model='github_copilot/gpt-4', messages=[{'role':'user','content':'hi'}], max_tokens=5)
print(resp.choices[0].message.content)
"
```

4. Open the shown URL and enter the shown device code:

- https://github.com/login/device

5. Restart LiteLLM:

```bash
docker compose down
docker compose up -d
```

### Verify token is persisted

```bash
ls -l ./copilot_tokens
```

You should see an `access-token` file.

### Troubleshooting

- If logs show `403 Forbidden` on `/copilot_internal/v2/token`, the token is usually not a valid Copilot OAuth token.
- A `github_pat_*` token is not enough for this endpoint.
- Remove invalid token and repeat Device Flow:

```bash
rm -f ./copilot_tokens/access-token
```

