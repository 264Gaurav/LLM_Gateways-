import os
import logfire
from openai import OpenAI
from dotenv import load_dotenv
import numpy as np

from observability.logger import get_logger

logger = get_logger(__name__)

# Load environment variables
logger.info("Loading environment variables from .env file")
load_dotenv()

# 1. Initialize Logfire
logger.info("Initializing Logfire configuration")
logfire.configure(
    token=os.getenv("LOGFIRE_TOKEN"),
    service_name="litellm-semantic-inspector",
)
logger.info("Logfire configuration completed successfully")

# 2. Auto-instrument OpenAI client calls
logger.info("Instrumenting OpenAI client calls with Logfire")
logfire.instrument_openai()

# 3. Instantiate OpenAI client pointing to LiteLLM Proxy
base_url = os.getenv("LITELLM_PROXY_URL", "http://localhost:4000/v1")
logger.info("Instantiating OpenAI client connecting to LiteLLM Proxy at: %s", base_url)

client = OpenAI(
    base_url=base_url,
    api_key=os.getenv("LITELLM_MASTER_KEY", "sk-master-key-12345"),
)
logger.info("OpenAI client instantiated successfully")


def get_embedding_and_inspect(text: str):
    """Generates embeddings and attaches raw vector numbers to Logfire trace"""
    logger.info("Requesting embedding generation for prompt: '%s'", text)
    
    with logfire.span("Generating Vector Embedding", prompt_text=text) as span:
        response = client.embeddings.create(
            model="text-embedding-3-small",
            input=text,
            encoding_format="float"  # Forces standard float array
        )
        
        vector_numbers = response.data[0].embedding
        vector_dim = len(vector_numbers)
        
        logger.info(
            "Successfully generated embedding for text. Vector dimension: %d", 
            vector_dim
        )
        
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
    logger.info("Executing query against semantic cache with prompt: '%s'", prompt)
    
    with logfire.span("Pipeline Exec: Semantic Query Evaluation", prompt=prompt) as span:
        
        # 1. Explicitly generate/log vector for the prompt
        vector = get_embedding_and_inspect(prompt)
        
        # 2. Send request through LiteLLM Proxy (Checks Redis Semantic Cache)
        logger.info("Sending chat completion request to LiteLLM proxy")
        response = client.chat.completions.create(
            model="gateway-model",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0
        )
        
        # 3. Extract content
        content = response.choices[0].message.content
        logger.info("Received chat completion response successfully")
        
        # Attach details to the parent Logfire trace
        span.set_attribute("response.content", content)
        
        print("\n--- Response ---")
        print(content)


def cosine_distance(v1, v2):
    logger.info("Calculating cosine distance between two vectors")
    distance = 1 - (np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2)))
    logger.info("Computed cosine distance: %.4f", distance)
    return distance


if __name__ == "__main__":
    logger.info("=== Starting LiteLLM Semantic Inspector Pipeline ===")

    # Demonstrate Vector Distance Comparison
    logger.info("--- Comparing DRY vs SOLID Principle Vector Distances ---")
    v_dry = get_embedding_and_inspect("What is DRY Principle?")
    v_solid = get_embedding_and_inspect("What is SOLID Principle")

    print("DRY   [0:5]:", v_dry[:5])
    print("SOLID [0:5]:", v_solid[:5])

    dist = cosine_distance(v_dry, v_solid)
    print(f"Cosine Distance: {dist:.4f}")

    # First call: Cache Miss (Generates embedding & queries LLM)
    logger.info("Executing Query 1 (Expect Cache Miss)")
    print("\nExecuting Query 1 (Expect Cache Miss)...")
    query_semantic_cache("What is Load balancer?")

    # Second call (Reworded): Cache Hit (Triggers semantic match threshold)
    logger.info("Executing Query 2 (Expect Semantic Cache Hit)")
    print("\nExecuting Query 2 (Expect Semantic Cache Hit)...")
    query_semantic_cache("Tell me about Load Balancer")

    logger.info("=== Pipeline Execution Complete ===")




# import os
# import logfire
# from openai import OpenAI
# from dotenv import load_dotenv
# import numpy as np

# from observability.logger import get_logger
# logger = get_logger(__name__)

# load_dotenv()

# # 1. Initialize Logfire
# logfire.configure(
#     token=os.getenv("LOGFIRE_TOKEN"),
#     service_name="litellm-semantic-inspector"
# )

# # 2. Auto-instrument OpenAI client calls
# logfire.instrument_openai()

# # 3. Instantiate OpenAI client pointing to LiteLLM Proxy
# client = OpenAI(
#     base_url=os.getenv("LITELLM_PROXY_URL", "http://localhost:4000/v1"),
#     api_key=os.getenv("LITELLM_MASTER_KEY", "sk-master-key-12345")
# )


# def get_embedding_and_inspect(text: str):
#     """Generates embeddings and attaches raw vector numbers to Logfire trace"""
#     with logfire.span("Generating Vector Embedding", prompt_text=text) as span:
#         response = client.embeddings.create(
#             model="text-embedding-3-small",
#             input=text,
#             encoding_format="float"  # Forces standard float array
#         )
        
#         vector_numbers = response.data[0].embedding
#         vector_dim = len(vector_numbers)
        
#         span.set_attribute("vector.dimensions", vector_dim)
#         span.set_attribute("vector.raw_numbers", vector_numbers[:10])
#         span.set_attribute("vector.full_vector", vector_numbers)
        
#         logfire.info(
#             "Vector generated successfully",
#             dimensions=vector_dim,
#             sample_vector_values=vector_numbers[:5]
#         )
        
#         return vector_numbers
    
    

# def query_semantic_cache(prompt: str):
#     """Executes query and captures cache hits & similarity scores"""
#     with logfire.span("Pipeline Exec: Semantic Query Evaluation", prompt=prompt) as span:
        
#         # 1. Explicitly generate/log vector for the prompt
#         vector = get_embedding_and_inspect(prompt)
        
#         # 2. Send request through LiteLLM Proxy (Checks Redis Semantic Cache)
#         response = client.chat.completions.create(
#             model="gateway-model",
#             messages=[{"role": "user", "content": prompt}],
#             temperature=0.0
#         )
        
#         # 3. Extract metadata returned from Proxy HTTP headers
#         # LiteLLM appends cache metadata in headers or response objects
#         content = response.choices[0].message.content
        
#         # Attach details to the parent Logfire trace
#         span.set_attribute("response.content", content)
        
#         print("\n--- Response ---")
#         print(content)



# def cosine_distance(v1, v2):
#     return 1 - (np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2)))

# v_dry = get_embedding_and_inspect("What is DRY Principle?")
# v_solid = get_embedding_and_inspect("What is SOLID Principle")

# print("DRY  [0:5]:", v_dry[:5])
# print("SOLID[0:5]:", v_solid[:5])

# dist = cosine_distance(v_dry, v_solid)
# print(f"Cosine Distance: {dist:.4f}")
# # If distance < threshold, Redis cache treats them as the same prompt.

# if __name__ == "__main__":
#     # First call: Cache Miss (Generates embedding & queries LLM)
#     print("Executing Query 1 (Expect Cache Miss)...")
#     query_semantic_cache("What is Load balancer?")

#     # Second call (Reworded): Cache Hit (Triggers semantic match threshold)
#     print("\nExecuting Query 2 (Expect Semantic Cache Hit)...")
#     query_semantic_cache("Tell me about Load Balancer")
