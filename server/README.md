# FastAPI LLM Gateway Server

This folder contains a FastAPI backend that routes requests through Guardrails -> LiteLLM -> LLMs and embeddings.

## Run

```bash
uvicorn server.main:app --host 0.0.0.0 --port 8000 --reload
```

## Endpoints

- `GET /health` - health check
- `POST /ai/llms` - chat completion with Guardrails + LiteLLM proxy
- `POST /v1/chat/completions` - alias for `/ai/llms`
- `POST /ai/embeddings` - embeddings through LiteLLM proxy
- `POST /v1/embeddings` - alias for `/ai/embeddings`
- `POST /ai/litellm/chat` - direct LiteLLM chat completions without Guardrails
- `POST /v1/litellm/chat/completions` - alias for `/ai/litellm/chat`
- `POST /ai/litellm/embeddings` - direct LiteLLM embeddings
- `POST /v1/litellm/embeddings` - alias for `/ai/litellm/embeddings`

## Streaming

Set `stream: true` in the chat request body to receive streaming output from LiteLLM.

## Request Examples

### Headers

Include these headers for all requests:

- `Content-Type: application/json`
- `Authorization: Bearer <your_litellm_master_key>`

### Chat Completion / LLM Request

```json
POST /ai/llms
Content-Type: application/json
Authorization: Bearer sk-...your-key...

{
  "model": "gateway-model",
  "messages": [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "What is the capital of France?"}
  ],
  "temperature": 0.7,
  "top_p": 1.0,
  "max_tokens": 200,
  "n": 1,
  "stream": false
}
```

### Streaming Chat Completion

```json
POST /ai/llms
Content-Type: application/json
Authorization: Bearer sk-...your-key...

{
  "model": "gateway-model",
  "messages": [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "Tell me a short story about a robot."}
  ],
  "stream": true
}
```

### Embeddings Request

```json
POST /ai/embeddings
Content-Type: application/json
Authorization: Bearer sk-...your-key...

{
  "model": "text-embedding-3-small",
  "input": "The quick brown fox jumps over the lazy dog."
}
```
