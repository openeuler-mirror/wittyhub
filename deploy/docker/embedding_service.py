"""
Simple embedding service using sentence-transformers
"""
import os
from typing import List

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

import torch
from sentence_transformers import SentenceTransformer

app = FastAPI(title="Embedding Service")

MODEL_NAME = os.getenv("MODEL_NAME", "BAAI/bge-base-zh-v1.5")
DIMENSION = int(os.getenv("DIMENSION", "768"))

print(f"Loading model: {MODEL_NAME}")
try:
    model = SentenceTransformer(MODEL_NAME)
    print(f"Model loaded successfully. Dimension: {DIMENSION}")
except Exception as e:
    print(f"Failed to load model: {e}")
    model = None


class EmbedRequest(BaseModel):
    input: List[str]
    model: str = MODEL_NAME


class EmbedItem(BaseModel):
    embedding: List[float]
    index: int


class EmbedResponse(BaseModel):
    model: str
    data: List[EmbedItem]


@app.post("/v1/embeddings")
async def create_embeddings(request: EmbedRequest) -> JSONResponse:
    if model is None:
        raise HTTPException(status_code=503, detail="Model not loaded")

    try:
        embeddings = model.encode(request.input, convert_to_numpy=True)

        data = []
        for i, emb in enumerate(embeddings):
            embedding_list = emb.tolist()
            if len(embedding_list) != DIMENSION:
                embedding_list = embedding_list[:DIMENSION]
                while len(embedding_list) < DIMENSION:
                    embedding_list.append(0.0)

            data.append({
                "embedding": embedding_list,
                "index": i
            })

        return JSONResponse(content={
            "model": request.model,
            "data": data
        })

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health():
    return {"status": "healthy", "model": MODEL_NAME, "dimension": DIMENSION}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8081)
