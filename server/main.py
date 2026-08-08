import os
import re
from pathlib import Path
from typing import Any, AsyncGenerator, Dict, List, Optional, Union

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse
from nemoguardrails import LLMRails, RailsConfig
from pydantic import BaseModel, Field

from .logger import get_logger

ROOT_DIR = Path(__file__).resolve().parents[1]
load_dotenv(ROOT_DIR / ".env")

LITELLM_PROXY_URL = os.getenv("LITELLM_PROXY_URL", "http://localhost:4000/v1").rstrip("/")
LITELLM_MASTER_KEY = os.getenv("LITELLM_MASTER_KEY") or os.getenv("OPENAI_API_KEY") or ""
DEFAULT_CHAT_MODEL = "gateway-model"
DEFAULT_EMBEDDING_MODEL = "openai/text-embedding-3-small"
GUARDRAILS_CONFIG_DIR = ROOT_DIR / "guardRails" / "config"

logger = get_logger(__name__)
app = FastAPI(title="LLM Gateways API", version="0.1.0")

guardrails: Optional[LLMRails] = None


class ChatCompletionRequest(BaseModel):
    model: Optional[str] = Field(default=DEFAULT_CHAT_MODEL)
    messages: List[Dict[str, str]] = Field(..., description="OpenAI-compatible message list")
    stream: bool = Field(default=False)
    temperature: Optional[float] = Field(default=0.0)
    top_p: Optional[float] = Field(default=1.0)
    max_tokens: Optional[int] = Field(default=None)
    n: Optional[int] = Field(default=1)


class EmbeddingsRequest(BaseModel):
    model: Optional[str] = Field(default=DEFAULT_EMBEDDING_MODEL)
    input: Union[str, List[str]] = Field(...)


def sanitize_user_query(query: str) -> tuple[str, Optional[str]]:
    if not query:
        return query, None

    low = query.lower()
    secret_patterns = [
        r"\bapi[_-]?key\b",
        r"\bsecret\b",
        r"\btoken\b",
        r"sk-[A-Za-z0-9_-]{16,}\b",
        r"ghp_[A-Za-z0-9_-]{36,}",
        r"xox[baprs]-[A-Za-z0-9-]{10,}",
    ]
    for pattern in secret_patterns:
        if re.search(pattern, low):
            return "", "Detected a secret or API key in the request. Remove any keys, tokens, or secrets before retrying."

    sanitized = re.sub(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", "[EMAIL_REDACTED]", query)
    sanitized = re.sub(r"\b(?:\+?\d[\d\s().-]{7,}\d)\b", "[PHONE_REDACTED]", sanitized)
    sanitized = re.sub(r"\b\d{3}[- ]?\d{2}[- ]?\d{4}\b", "[SSN_REDACTED]", sanitized)

    if sanitized != query:
        logger.info("[PII] Sensitive data masked before forwarding to Guardrails.")

    return sanitized, None


@app.on_event("startup")
async def startup_event() -> None:
    global guardrails
    if not GUARDRAILS_CONFIG_DIR.exists():
        logger.warning("Guardrails config directory not found: %s", GUARDRAILS_CONFIG_DIR)
        return

    logger.info("Loading Guardrails configuration from %s", GUARDRAILS_CONFIG_DIR)
    rails_config = RailsConfig.from_path(str(GUARDRAILS_CONFIG_DIR))
    guardrails = LLMRails(rails_config)
    logger.info("Guardrails initialized successfully.")


async def run_input_guard(user_query: str) -> tuple[bool, str]:
    if not user_query.strip():
        return True, ""

    if guardrails is None:
        logger.warning("Guardrails instance is not available; skipping input guard check.")
        return True, ""

    try:
        result = await guardrails.generate_async(messages=[{"role": "user", "content": user_query}])
        raw_content = str(result.get("content", "")).strip()
        logger.info("Guardrails response: %s", raw_content)

        normalized = raw_content.lower()
        blocked = "unsafe" in normalized or "violates" in normalized or "blocked" in normalized
        if blocked:
            return False, raw_content

        return True, raw_content

    except Exception as exc:
        logger.error("Guardrails input check failed: %s", exc, exc_info=True)
        return True, ""


def build_proxy_headers() -> Dict[str, str]:
    headers = {"Content-Type": "application/json"}
    if LITELLM_MASTER_KEY:
        headers["Authorization"] = f"Bearer {LITELLM_MASTER_KEY}"
    return headers


async def call_litellm_api(endpoint: str, payload: Dict[str, Any], stream: bool = False) -> Any:
    headers = build_proxy_headers()
    if stream:
        async def event_stream() -> AsyncGenerator[bytes, None]:
            async with httpx.AsyncClient(timeout=None) as client:
                async with client.stream("POST", endpoint, json=payload, headers=headers) as response:
                    if response.status_code >= 400:
                        body = await response.aread()
                        raise HTTPException(status_code=response.status_code, detail=body.decode(errors="ignore"))
                    async for chunk in response.aiter_bytes(chunk_size=1024):
                        if chunk:
                            yield chunk

        return event_stream()

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(endpoint, json=payload, headers=headers)
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise HTTPException(status_code=exc.response.status_code, detail=exc.response.text)
        return response.json()


@app.get("/health")
async def health_check() -> Dict[str, str]:
    return {"status": "ok", "service": "llm-gateway"}


@app.post("/ai/llms")
@app.post("/v1/chat/completions", include_in_schema=False)
async def ai_llms(request: ChatCompletionRequest) -> Any:
    user_messages = [m["content"] for m in request.messages if m.get("role") == "user"]
    prompt = "\n".join(user_messages).strip()

    sanitized_prompt, sanitize_error = sanitize_user_query(prompt)
    if sanitize_error:
        logger.warning("Sanitizer blocked request: %s", sanitize_error)
        raise HTTPException(status_code=400, detail=sanitize_error)

    is_safe, guardrails_output = await run_input_guard(sanitized_prompt)
    if not is_safe:
        logger.warning("Input blocked by Guardrails: %s", guardrails_output)
        return JSONResponse(status_code=403, content={"error": "input_blocked", "reason": guardrails_output})

    endpoint = f"{LITELLM_PROXY_URL}/chat/completions"
    payload = {
        "model": request.model or DEFAULT_CHAT_MODEL,
        "messages": request.messages,
        "temperature": request.temperature,
        "top_p": request.top_p,
        "max_tokens": request.max_tokens,
        "n": request.n,
        "stream": request.stream,
    }

    if request.stream:
        logger.info("Starting streaming chat completion through LiteLLM proxy")
        generator = await call_litellm_api(endpoint, payload, stream=True)
        return StreamingResponse(generator, media_type="text/event-stream")

    logger.info("Starting standard chat completion through LiteLLM proxy")
    return await call_litellm_api(endpoint, payload, stream=False)


@app.post("/ai/embeddings")
@app.post("/v1/embeddings", include_in_schema=False)
async def ai_embeddings(request: EmbeddingsRequest) -> Any:
    if isinstance(request.input, str):
        sanitized_input, sanitize_error = sanitize_user_query(request.input)
        if sanitize_error:
            raise HTTPException(status_code=400, detail=sanitize_error)
    elif isinstance(request.input, list):
        for item in request.input:
            if not isinstance(item, str):
                raise HTTPException(status_code=400, detail="All embedding inputs must be strings.")
            sanitized_item, sanitize_error = sanitize_user_query(item)
            if sanitize_error:
                raise HTTPException(status_code=400, detail=sanitize_error)

    endpoint = f"{LITELLM_PROXY_URL}/embeddings"
    payload = {
        "model": request.model or DEFAULT_EMBEDDING_MODEL,
        "input": request.input,
    }

    logger.info("Sending embedding request to LiteLLM proxy")
    return await call_litellm_api(endpoint, payload, stream=False)
