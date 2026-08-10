# Streamlit Client UI

This folder contains the interactive Streamlit frontend for the LLM Gateways project.

## What it does

The Streamlit app provides a developer console for:

- sending chat requests to the FastAPI gateway
- switching between `Guardrails + LiteLLM` and `Direct LiteLLM` modes
- streaming chat output as responses arrive
- generating embeddings through the gateway or direct LiteLLM proxy
- testing raw API endpoints and previewing payloads
- reviewing and exporting chat history

## UI workflow

1. Start the LiteLLM Docker stack (`litellm-setup/docker compose up -d`).
2. Start the FastAPI server from the repository root:

   ```bash
   uvicorn server.main:app --host 0.0.0.0 --port 8000 --reload
   ```

3. Start the Streamlit UI:

   ```bash
   streamlit run client/streamlit.py
   ```

4. Open the UI in the browser at the address shown by Streamlit.

5. In the sidebar:

- set `API base URL` to your gateway server (default: `http://localhost:8000`)
- optionally enter a `Bearer API key`
- choose `Gateway mode`:
  - `Guardrails + LiteLLM` to route chat through the project gateway with Guardrails validation
  - `Direct LiteLLM` to call the underlying LiteLLM proxy directly
- adjust chat settings such as `model`, `temperature`, `top_p`, `max_tokens`, `choices`, and `stream response`

6. Enter a chat message and press Enter.

7. Optionally use the developer tabs for:

- embeddings generation
- raw API explorer
- request payload preview

## Supported routes

The Streamlit frontend uses these endpoints depending on mode:

- `Guardrails + LiteLLM`
  - `POST /ai/llms`
  - `POST /ai/embeddings`
- `Direct LiteLLM`
  - `POST /ai/litellm/chat`
  - `POST /ai/litellm/embeddings`

## Notes

- Streaming must be enabled in the sidebar to receive incremental chat text.
- The app preserves chat history during the session and allows exporting conversation JSON.
- Use the raw API explorer for debugging alternate endpoints.
