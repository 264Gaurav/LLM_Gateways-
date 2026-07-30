from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Union, Optional, Dict
from FlagEmbedding import BGEM3FlagModel

app = FastAPI(title="BGE-M3 Sparse + Dense Embedding Service")

# Load model onto CPU (or GPU if available)
model = BGEM3FlagModel('BAAI/bge-m3', use_fp16=False, device='cpu')

class HybridEmbeddingRequest(BaseModel):
    model: Optional[str] = "bge-m3"
    input: Union[str, List[str]]
    return_dense: bool = True
    return_sparse: bool = True
    return_colbert: bool = False

@app.get("/health")
def health_check():
    return {"status": "healthy"}

@app.post("/v1/hybrid_embeddings")
async def get_hybrid_embeddings(payload: HybridEmbeddingRequest):
    try:
        sentences = [payload.input] if isinstance(payload.input, str) else payload.input
        if not sentences:
            raise HTTPException(status_code=400, detail="Input cannot be empty.")

        # FlagEmbedding 1.2.x return keys: 'dense_vecs', 'lexical_weights', 'colbert_vecs'
        outputs = model.encode(
            sentences,
            return_dense=payload.return_dense,
            return_sparse=payload.return_sparse,
            return_colbert_vecs=payload.return_colbert
        )

        records = []
        for i in range(len(sentences)):
            record = {"index": i}
            
            # 1. Dense vector (1024-dim float array)
            if payload.return_dense:
                record["dense_embedding"] = outputs['dense_vecs'][i].tolist()
            
            # 2. Sparse lexical weights dict: {"token_id": weight_float}
            if payload.return_sparse:
                # Convert keys/values to JSON-serializable types
                sparse_dict = outputs['lexical_weights'][i]
                record["sparse_embedding"] = {
                    str(k): float(v) for k, v in sparse_dict.items()
                }

            # 3. Optional ColBERT vectors (Multi-Vector)
            if payload.return_colbert:
                record["colbert_embedding"] = outputs['colbert_vecs'][i].tolist()

            records.append(record)

        return {
            "object": "list",
            "data": records,
            "model": payload.model
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))