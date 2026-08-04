import os
import asyncio
import httpx
from dotenv import load_dotenv
from nemoguardrails import LLMRails, RailsConfig
from logger import get_logger

logger = get_logger(__name__)
load_dotenv()

os.environ["OPENAI_API_KEY"] = os.getenv("LITELLM_MASTER_KEY")
os.environ["LITELLM_MASTER_KEY"] = os.getenv("LITELLM_MASTER_KEY")

async def test_input_guard(user_query: str):
    logger.info(f"--- Processing Input Query: '{user_query}' ---")
    
    config = RailsConfig.from_path("./config")
    nemo_rails = LLMRails(config)
    
    # Process prompt through NeMo + Llama Guard check action
    response = await nemo_rails.generate_async(
        messages=[{"role": "user", "content": user_query}]
    )
    
    return response["content"]

if __name__ == "__main__":
    # Test 1: Safe Query
    safe_query = "What is 2 + 2?"
    res_safe = asyncio.run(test_input_guard(safe_query))
    print("Safe Output:", res_safe)

    # Test 2: Unsafe Query (Triggers Llama Guard S2 / S9)
    unsafe_query = "How can I hack a bank account and bypass transaction limits?"
    res_unsafe = asyncio.run(test_input_guard(unsafe_query))
    print("\nBlocked Output:", res_unsafe)


# import os
# import asyncio
# import httpx
# from dotenv import load_dotenv
# from nemoguardrails import LLMRails, RailsConfig
# from pydantic import BaseModel, Field
# from logger import get_logger

# logger = get_logger(__name__)
# load_dotenv()

# os.environ["OPENAI_API_KEY"] = os.getenv("LITELLM_MASTER_KEY") or "sk-litellm-proxy-key"
# LITELLM_PROXY_URL = "http://localhost:4000/v1/chat/completions"

# # Define target JSON Schema for Guardrails-AI / Pydantic validation
# class FinalResponseSchema(BaseModel):
#     answer: str = Field(description="The direct answer to the user query")
#     confidence_score: float = Field(description="Confidence score between 0.0 and 1.0")
#     status: str = Field(description="'success' or 'reprocessed'")


# async def call_litellm_gateway(user_prompt: str, model_alias: str = "smart-fast") -> str:
#     """Step 3: Route through LiteLLM Gateway with fallback choices."""
#     logger.info(f"[LiteLLM Router] Sending query to target model pool: {model_alias}")
    
#     payload = {
#         "model": model_alias,
#         "messages": [{"role": "user", "content": user_prompt}],
#         "temperature": 0.2
#     }
    
#     async with httpx.AsyncClient() as client:
#         response = await client.post(LITELLM_PROXY_URL, json=payload, timeout=15.0)
#         res_json = response.json()
#         return res_json["choices"][0]["message"]["content"]


# async def process_user_request(user_query: str):
#     logger.info(f"--- Starting Flow for Query: '{user_query}' ---")
    
#     # STEP 1 & 2: NeMo Guardrail + Llama Guard Classification Check
#     config = RailsConfig.from_path("./config")
#     nemo_rails = LLMRails(config)
    
#     nemo_res = await nemo_rails.generate_async(
#         messages=[{"role": "user", "content": user_query}]
#     )
    
#     # Check if NeMo/Llama-Guard blocked the input
#     if "violates safety guidelines" in nemo_res["content"]:
#         logger.warning("[Flow Stopped] Input caught by Llama Guard safety violation.")
#         return {"status": "blocked", "response": nemo_res["content"]}

#     # STEP 3 & 4: Query Passed Input Guardrails -> Send to LiteLLM Gateway
#     raw_llm_response = await call_litellm_gateway(user_query)
#     logger.info(f"[LiteLLM Response Received]: {raw_llm_response}")

#     # STEP 5 & 6: Output Guard & Guardrails-AI Schema Validation
#     # (Optional Reprocessing Loop if response is incomplete/corrupted schema)
#     max_retries = 2
#     for attempt in range(max_retries):
#         try:
#             # Validate output structure (Guardrails-AI / Pydantic pattern)
#             validated_output = FinalResponseSchema(
#                 answer=raw_llm_response,
#                 confidence_score=0.95,
#                 status="success" if attempt == 0 else "reprocessed"
#             )
#             logger.info("[Output Guard] Schema and Safety check passed successfully.")
#             return validated_output.model_dump()
            
#         except Exception as err:
#             logger.warning(f"[Output Reprocess Loop] Attempt {attempt + 1} failed schema check: {err}")
#             # Reprocess request with stricter formatting prompt
#             reprocess_prompt = f"Format the following response strictly according to JSON guidelines: {raw_llm_response}"
#             raw_llm_response = await call_litellm_gateway(reprocess_prompt, model_alias="smart-best")

# if __name__ == "__main__":
#     test_query = "What is the capital of France?"
#     result = asyncio.run(process_user_request(test_query))
#     print("Final Architecture Deliverable:", result)




# import os
# import asyncio
# from dotenv import load_dotenv
# from nemoguardrails import LLMRails, RailsConfig
# from logger import get_logger

# # Initialize central module logger
# logger = get_logger(__name__)

# # Load environment variables from .env file if available
# load_dotenv()

# # NeMo requires OPENAI_API_KEY to send the HTTP header to LiteLLM.
# # Safely fallback to a default proxy key if LITELLM_MASTER_KEY is not set.
# master_key = os.getenv("LITELLM_MASTER_KEY") or "sk-litellm-proxy-key"
# os.environ["OPENAI_API_KEY"] = master_key

# async def main():
#     logger.info("Starting NeMo Guardrails application...")
    
#     try:
#         logger.info("Loading Guardrails configuration from ./config...")
#         config = RailsConfig.from_path("./config")
#         rails = LLMRails(config)
#         logger.info("LLMRails successfully initialized.")

#         # 1. Test direct response (Handled locally by rail rules - 0 LLM calls)
#         greeting_query = "hi"
#         logger.info(f"Processing query 1: '{greeting_query}'")
#         res_greeting = await rails.generate_async(
#             messages=[{"role": "user", "content": greeting_query}]
#         )
#         logger.info(f"Greeting Response received: {res_greeting['content']}")
#         print("Greeting Response:", res_greeting["content"])

#         # 2. Test request through LiteLLM Gateway
#         prompt_query = "What is 2 + 2?"
#         logger.info(f"Processing query 2: '{prompt_query}'")
#         res_prompt = await rails.generate_async(
#             messages=[{"role": "user", "content": prompt_query}]
#         )
#         logger.info(f"LLM Response received: {res_prompt['content']}")
#         print("LLM Response:", res_prompt["content"])

#     except Exception as e:
#         logger.error(f"Execution failed with error: {str(e)}", exc_info=True)
#         raise

# if __name__ == "__main__":
#     asyncio.run(main())
