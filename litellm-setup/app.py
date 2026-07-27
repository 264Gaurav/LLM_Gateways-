import os
import logfire
from openai import OpenAI
from dotenv import load_dotenv
import numpy as np

load_dotenv()

# 1. Initialize Logfire
logfire.configure(
    token=os.getenv("LOGFIRE_TOKEN"),
    service_name="litellm-semantic-inspector"
)

# 2. Auto-instrument OpenAI client calls
logfire.instrument_openai()

# 3. Instantiate OpenAI client pointing to LiteLLM Proxy
client = OpenAI(
    base_url=os.getenv("LITELLM_PROXY_URL", "http://localhost:4000/v1"),
    api_key=os.getenv("LITELLM_MASTER_KEY", "sk-master-key-12345")
)


def get_embedding_and_inspect(text: str):
    """Generates embeddings and attaches raw vector numbers to Logfire trace"""
    with logfire.span("Generating Vector Embedding", prompt_text=text) as span:
        response = client.embeddings.create(
            model="text-embedding-3-small",
            input=text,
            encoding_format="float"  # Forces standard float array
        )
        
        vector_numbers = response.data[0].embedding
        vector_dim = len(vector_numbers)
        
        span.set_attribute("vector.dimensions", vector_dim)
        span.set_attribute("vector.raw_numbers", vector_numbers[:10])
        span.set_attribute("vector.full_vector", vector_numbers)
        
        logfire.info(
            "Vector generated successfully",
            dimensions=vector_dim,
            sample_vector_values=vector_numbers[:5]
        )
        
        return vector_numbers
    
    

def query_semantic_cache(prompt: str):
    """Executes query and captures cache hits & similarity scores"""
    with logfire.span("Pipeline Exec: Semantic Query Evaluation", prompt=prompt) as span:
        
        # 1. Explicitly generate/log vector for the prompt
        vector = get_embedding_and_inspect(prompt)
        
        # 2. Send request through LiteLLM Proxy (Checks Redis Semantic Cache)
        response = client.chat.completions.create(
            model="gateway-model",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0
        )
        
        # 3. Extract metadata returned from Proxy HTTP headers
        # LiteLLM appends cache metadata in headers or response objects
        content = response.choices[0].message.content
        
        # Attach details to the parent Logfire trace
        span.set_attribute("response.content", content)
        
        print("\n--- Response ---")
        print(content)



def cosine_distance(v1, v2):
    return 1 - (np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2)))

v_dry = get_embedding_and_inspect("What is DRY Principle?")
v_solid = get_embedding_and_inspect("What is SOLID Principle")

print("DRY  [0:5]:", v_dry[:5])
print("SOLID[0:5]:", v_solid[:5])

dist = cosine_distance(v_dry, v_solid)
print(f"Cosine Distance: {dist:.4f}")
# If distance < threshold, Redis cache treats them as the same prompt.

if __name__ == "__main__":
    # First call: Cache Miss (Generates embedding & queries LLM)
    print("Executing Query 1 (Expect Cache Miss)...")
    query_semantic_cache("What is Load balancer?")

    # Second call (Reworded): Cache Hit (Triggers semantic match threshold)
    print("\nExecuting Query 2 (Expect Semantic Cache Hit)...")
    query_semantic_cache("Tell me about Load Balancer")







# import os
# import logfire
# from openai import OpenAI
# from dotenv import load_dotenv

# # 1. Load environment variables (.env file)
# load_dotenv()

# # 2. Configure Logfire using your LOGFIRE_TOKEN
# logfire.configure(
#     token=os.getenv("LOGFIRE_TOKEN"),
#     service_name="litellm-python-client"
# )

# # 3. Auto-instrument all calls made by the OpenAI SDK
# logfire.instrument_openai()

# # 4. Initialize the client to talk to your LOCAL LiteLLM Gateway
# client = OpenAI(
#     base_url=os.getenv("LITELLM_PROXY_URL", "http://localhost:4000/v1"),
#     api_key=os.getenv("LITELLM_MASTER_KEY", "sk-master-key-12345"),
# )

# def main():
#     print("Sending request to local LiteLLM Proxy...")
    
#     with logfire.span("User Flow: System Architecture Query"):
#         response = client.chat.completions.create(
#             model="gateway-model",  # Model alias from litellm_config.yaml
#             messages=[
#                 {"role": "system", "content": "You are a concise engineering assistant."},
#                 {"role": "user", "content": "Confirm you are responding through the LiteLLM Proxy."}
#             ]
#         )
        
#         print("\n--- Model Response ---")
#         print(response.choices[0].message.content)

# if __name__ == "__main__":
#     main()