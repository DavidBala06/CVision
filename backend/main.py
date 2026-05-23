from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import json
import re

from ai.RAG_engine import build_vector_database, create_retriever_chain

app = FastAPI()

# Enable CORS for the frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
    "http://localhost:5173", 
    "http://127.0.0.1:5173", 
    "http://localhost:3000",
    "http://127.0.0.1:3000"
], # React default ports
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize RAG engine
print("Initializing Vector Database...")
db = build_vector_database()
if db:
    print("Initializing Retriever Chain...")
    matcher = create_retriever_chain(db)
else:
    print("Warning: Vector database could not be built. Ensure OBSIDIAN_VAULT_PATH has valid documents.")
    matcher = None

class MatchRequest(BaseModel):
    query: str

@app.post("/api/match")
async def match_candidates(request: MatchRequest):
    if not matcher:
        # If DB was empty or not built, we can't query it.
        # But for testing, return empty array
        return []
    
    try:
        response = matcher.invoke({"input": request.query})
        answer = response.get("answer", "")
        
        # Clean up the answer in case LLM added markdown backticks
        answer = answer.strip()
        if answer.startswith("```json"):
            answer = answer[7:]
        elif answer.startswith("```"):
            answer = answer[3:]
        if answer.endswith("```"):
            answer = answer[:-3]
            
        answer = answer.strip()
        
        # If the LLM returned empty or our prompt failed to match
        if not answer or answer == "[]":
            return []
            
        try:
            candidates = json.loads(answer)
            return candidates
        except json.JSONDecodeError as e:
            print(f"Error parsing JSON from LLM: {answer}")
            return []
            
    except Exception as e:
        print(f"Error during matching: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
