from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import json

from ai.RAG_engine import build_vector_database, create_retriever_chain

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173", 
        "http://127.0.0.1:5173", 
        "http://localhost:3000",
        "http://127.0.0.1:3000"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

print("Initializing Vector Database...")
db = build_vector_database()
if db:
    print("Vector database built successfully.")
else:
    print("Warning: Vector database could not be built.")

print("Initializing Retriever Chain...")
matcher = create_retriever_chain(db)

class MatchRequest(BaseModel):
    query: str

@app.post("/api/match")
async def match_candidates(request: MatchRequest):
    if not matcher:
        return []
    
    print(f"\n[API] Received query: {request.query}")
    try:
        # Deoarece RAG_engine conține '| parser', rezultatul este deja o listă/obiect Python valid
        candidates = matcher.invoke({"input": request.query})
        print(f"[API] Groq Extracted Output: {candidates}")
        
        if not candidates:
            return []
            
        # Plasă de siguranță în caz că modelul întoarce un singur obiect în loc de listă
        if isinstance(candidates, dict):
            candidates = [candidates]
            
        return candidates
            
    except Exception as e:
        print(f"[API] Error during matching: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)