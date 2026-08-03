import os
import asyncio
from nemoguardrails import LLMRails, RailsConfig

# NeMo requires OPENAI_API_KEY to send the HTTP header to LiteLLM.
# Pass your LITELLM_MASTER_KEY - to use the LiteLLM Proxy for routing requests to Gemini or other LLMs.
os.environ["OPENAI_API_KEY"] = os.getenv("LITELLM_MASTER_KEY")

async def main():
    config = RailsConfig.from_path("./config")
    rails = LLMRails(config)

    # 1. Test direct response (Handled locally by rail rules - 0 LLM calls)
    res_greeting = await rails.generate_async(
        messages=[{"role": "user", "content": "hi"}]
    )
    print("Greeting Response:", res_greeting["content"])

    # 2. Test request through LiteLLM Gateway
    res_prompt = await rails.generate_async(
        messages=[{"role": "user", "content": "What is 2 + 2?"}]
    )
    print("LLM Response:", res_prompt["content"])

if __name__ == "__main__":
    asyncio.run(main())