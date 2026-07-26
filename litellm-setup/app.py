import os
import logfire
from openai import OpenAI
from dotenv import load_dotenv

# 1. Load environment variables (.env file)
load_dotenv()

# 2. Configure Logfire using your LOGFIRE_TOKEN
logfire.configure(
    token=os.getenv("LOGFIRE_TOKEN"),
    service_name="litellm-python-client"
)

# 3. Auto-instrument all calls made by the OpenAI SDK
logfire.instrument_openai()

# 4. Initialize the client to talk to your LOCAL LiteLLM Gateway
client = OpenAI(
    base_url=os.getenv("LITELLM_PROXY_URL", "http://localhost:4000/v1"),
    api_key=os.getenv("LITELLM_MASTER_KEY", "sk-master-key-12345"),
)

def main():
    print("Sending request to local LiteLLM Proxy...")
    
    with logfire.span("User Flow: System Architecture Query"):
        response = client.chat.completions.create(
            model="gateway-model",  # Model alias from litellm_config.yaml
            messages=[
                {"role": "system", "content": "You are a concise engineering assistant."},
                {"role": "user", "content": "Confirm you are responding through the LiteLLM Proxy."}
            ]
        )
        
        print("\n--- Model Response ---")
        print(response.choices[0].message.content)

if __name__ == "__main__":
    main()
    
    
    


# import os
# import asyncio
# import logfire
# import litellm
# from dotenv import load_dotenv

# # 1. Load environment variables (.env file containing LOGFIRE_TOKEN and LITELLM_MASTER_KEY)
# load_dotenv()

# # 2. Configure Logfire (Reads LOGFIRE_TOKEN automatically)
# logfire.configure()

# # 3. Instrument LiteLLM with Logfire
# logfire.instrument_litellm()

# # 4. LiteLLM Proxy settings
# LITELLM_PROXY_URL = os.getenv("LITELLM_PROXY_URL", "http://localhost:4000")
# LITELLM_MASTER_KEY = os.getenv("LITELLM_MASTER_KEY", "sk-master-key-12345")


# def run_sync_request():
#     """Example synchronous LLM request via LiteLLM Proxy"""
#     with logfire.span("User Pipeline Step: Sync Chat"):
#         response = litellm.completion(
#             model="gateway-model",  # Defined in your litellm_config.yaml
#             api_base=LITELLM_PROXY_URL,
#             api_key=LITELLM_MASTER_KEY,
#             messages=[
#                 {"role": "user", "content": "Explain how database indexing works in 2 sentences."}
#             ],
#             temperature=0.3,
#             metadata={"environment": "development", "user_id": "dev-user-1"}
#         )
#         print("Response:", response.choices[0].message.content)


# async def run_async_request():
#     """Example asynchronous LLM request via LiteLLM Proxy"""
#     async with logfire.span("User Pipeline Step: Async Chat"):
#         response = await litellm.acompletion(
#             model="gateway-model",
#             api_base=LITELLM_PROXY_URL,
#             api_key=LITELLM_MASTER_KEY,
#             messages=[
#                 {"role": "user", "content": "Summarize the benefit of containerizing LLM proxies."}
#             ],
#             temperature=0.2,
#         )
#         print("Async Response:", response.choices[0].message.content)


# if __name__ == "__main__":
#     print("Sending synchronous completion request...")
#     run_sync_request()

#     print("\nSending asynchronous completion request...")
#     asyncio.run(run_async_request())