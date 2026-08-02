"""All settings for the app live here, in one place."""


import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

# ENV VAR / SECRET
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()
JINA_API_KEY = os.getenv("JINA_API_KEY", "").strip()

# TRACING
LANGSMITH_TRACING = os.getenv("LANGSMITH_TRACING", "false").strip().lower()
LANGSMITH_ENDPOINT = os.getenv("LANGSMITH_ENDPOINT", "").strip()
LANGSMITH_API_KEY = os.getenv("LANGSMITH_API_KEY", "").strip()
LANGSMITH_PROJECT = os.getenv("LANGSMITH_PROJECT", "").strip()





# VECTOR_STORE_PATH = os.path.join("data", "faiss_index")

## MODELS 
# LLM and EMBEDING MODEL 

LLM_MODEL_NAME = "openai/gpt-oss-20b"

EMBEDDING_MODEL_NAME = "jina-embeddings-v2-base-en"

## CHUNK / TEXT SPLITTING CONFIG 

CHUNK_SIZE = 500
CHUNK_OVERLAP = 60

# RETRIVAL RESULTS 
TOP_K_RESULTS = 3


## SYSTEM INSTRUCTIONS 

SYSTEM_PROMPT = (
    "You are a friendly HR assistant. Always use the search_hr_policy tool to look up "
    "facts before answering. If the answer isn't in the search results, say you don't know "
    "instead of guessing."
)


def check_api_keys() -> None:
    """Stop early with a clear message if a required API key is missing."""
    missing = []
    if not GROQ_API_KEY:
        missing.append("GROQ_API_KEY")
    if not JINA_API_KEY:
        missing.append("JINA_API_KEY")

    if missing:
        raise ValueError(
            f"Missing required API key(s): {', '.join(missing)}. Please add them to your .env file."
        )