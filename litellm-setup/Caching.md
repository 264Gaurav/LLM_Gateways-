# Caching with LiteLLM (at LLM/AI Gateway)
> **Goal:** Optimise latency, reduce API costs, and mitigate upstream LLM rate limits for identical, similar, and redundant queries.

---

## 1. Quick Reference: Local Tools & Dashboards

| Service / Dashboard | URL | Usage |
| :--- | :--- | :--- |
| **Redis Insight UI** | [http://localhost:8001](http://localhost:8001) | Inspect vector indexes, active cache keys, TTLs, and cache hit metrics |
| **LiteLLM Proxy UI** | [http://localhost:4000/ui](http://localhost:4000/ui) | View spend logs, latency traces, and proxy-level cache status |

---

## 2. Caching Taxonomy & Selection Matrix

LiteLLM supports two operational modes of caching:
1. **Exact Match (KV Caching):** Key is hashed directly from prompt text/messages. Instant lookup ($O(1)$ complexity), zero vector compute overhead.
2. **Semantic Caching:** Prompt is transformed into an embedding vector, and cosine similarity is evaluated against stored vector indexes. Returns cached responses for semantically equivalent queries.

### Selection Matrix

| Cache Adapter | Type | Latency | Scalability | Persistence | Recommended Use Case |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **In-Memory** | Exact | $< 1\text{ ms}$ | Single Node | Volatile | Local development, single-instance testing |
| **Disk Cache** | Exact | $\sim 1\text{--}5\text{ ms}$ | Single Node | Persistent | High-volume single node without Redis dependency |
| **Redis Cache** | Exact | $\sim 2\text{--}10\text{ ms}$ | Distributed | Persistent / Hybrid | Enterprise production default for multi-node deployments |
| **Redis Semantic** | Semantic | $\sim 15\text{--}40\text{ ms}$ | Distributed | Persistent | High-traffic applications with frequent rephrased prompts |
| **Qdrant Semantic** | Semantic | $\sim 15\text{--}50\text{ ms}$ | High-Scale Distributed | Persistent | Dedicated vector DB setups handling heavy vector workloads |
| **Valkey Semantic** | Semantic | $\sim 15\text{--}40\text{ ms}$ | Distributed | Persistent | Open-source Redis drop-in alternative (Linux Foundation) |
| **S3 Bucket** | Exact | $\sim 50\text{--}150\text{ ms}$ | Cloud Native | Cold / Durable | Long-term archival of high-token outputs; serverless tasks |
| **GCS Bucket** | Exact | $\sim 50\text{--}150\text{ ms}$ | Cloud Native | Cold / Durable | GCP-native long-term response persistence |

---

## 3. Supported Cache Adapters & Configuration

### A. Exact-Match Cache Configurations

#### 1. Redis Cache (Recommended Default)
Distributed, low-latency key-value store suitable for multi-replica LiteLLM instances.

```yaml
litellm_settings:
  cache: true
  cache_params:
    type: "redis"
    host: os.environ/REDIS_HOST
    port: os.environ/REDIS_PORT
    password: os.environ/REDIS_PASSWORD
    ttl: 3600  # Time to live in seconds (1 hour)
    # Exclude embeddings to prevent static cache collisions
    supported_call_types: ["completion", "acompletion"]