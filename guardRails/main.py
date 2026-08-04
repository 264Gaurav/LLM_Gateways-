import os
import asyncio
from dotenv import load_dotenv
from nemoguardrails import LLMRails, RailsConfig
from logger import get_logger

# Initialize central module logger
logger = get_logger(__name__)

# Load environment variables from .env file if available
load_dotenv()

# NeMo requires OPENAI_API_KEY to send the HTTP header to LiteLLM.
# Safely fallback to a default proxy key if LITELLM_MASTER_KEY is not set.
master_key = os.getenv("LITELLM_MASTER_KEY") or "sk-litellm-proxy-key"
os.environ["OPENAI_API_KEY"] = master_key

async def main():
    logger.info("Starting NeMo Guardrails application...")
    
    try:
        logger.info("Loading Guardrails configuration from ./config...")
        config = RailsConfig.from_path("./config")
        rails = LLMRails(config)
        logger.info("LLMRails successfully initialized.")

        # 1. Test direct response (Handled locally by rail rules - 0 LLM calls)
        greeting_query = "hi"
        logger.info(f"Processing query 1: '{greeting_query}'")
        res_greeting = await rails.generate_async(
            messages=[{"role": "user", "content": greeting_query}]
        )
        logger.info(f"Greeting Response received: {res_greeting['content']}")
        print("Greeting Response:", res_greeting["content"])

        # 2. Test request through LiteLLM Gateway
        prompt_query = "What is 2 + 2?"
        logger.info(f"Processing query 2: '{prompt_query}'")
        res_prompt = await rails.generate_async(
            messages=[{"role": "user", "content": prompt_query}]
        )
        logger.info(f"LLM Response received: {res_prompt['content']}")
        print("LLM Response:", res_prompt["content"])

    except Exception as e:
        logger.error(f"Execution failed with error: {str(e)}", exc_info=True)
        raise

if __name__ == "__main__":
    asyncio.run(main())




# import os
# import asyncio
# from dotenv import load_dotenv
# from nemoguardrails import LLMRails, RailsConfig

# # Load environment variables from .env file if available
# load_dotenv()

# # NeMo requires OPENAI_API_KEY to send the HTTP header to LiteLLM.
# # Pass your LITELLM_MASTER_KEY - to use the LiteLLM Proxy for routing requests to Gemini or other LLMs.
# os.environ["OPENAI_API_KEY"] = os.getenv("LITELLM_MASTER_KEY")

# async def main():
#     config = RailsConfig.from_path("./config")
#     rails = LLMRails(config)

#     # 1. Test direct response (Handled locally by rail rules - 0 LLM calls)
#     res_greeting = await rails.generate_async(
#         messages=[{"role": "user", "content": "hi"}]
#     )
#     print("Greeting Response:", res_greeting["content"])

#     # 2. Test request through LiteLLM Gateway
#     res_prompt = await rails.generate_async(
#         messages=[{"role": "user", "content": "What is 2 + 2?"}]
#     )
#     print("LLM Response:", res_prompt["content"])

# if __name__ == "__main__":
#     asyncio.run(main())