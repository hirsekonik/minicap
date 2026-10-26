import os
import sys
from typing import Optional, List
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from dotenv import load_dotenv

# Explicitly load .env from project root
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
env_path = os.path.join(base_dir, '.env')
if os.path.exists(env_path):
    load_dotenv(env_path)
else:
    load_dotenv()

# Safe imports for internal modules
try:
    from src.rag import setup_chromadb, query_rag_engine, PROMPTS, get_gemini_api_key
    from src.pipeline import read_pdf, clean_text, chunk_text
except ImportError:
    from rag import setup_chromadb, query_rag_engine, PROMPTS, get_gemini_api_key
    from pipeline import read_pdf, clean_text, chunk_text

app = FastAPI(
    title="TPC Automated Clearance Assistant (MiniCAP)",
    description="Context-grounded RAG API & Web Interface for the TPC Student Handbook & Web-Based Clearance System",
    version="1.0.0"
)

# Enable CORS for external client applications / ERP systems
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global collection reference
collection = None

def get_or_init_collection():
    global collection
    if collection is None:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        pdf_path = os.path.join(base_dir, 'data', 'Master_Capstone_Dataset.pdf')
        
        # Check if DB already populated
        c, _ = setup_chromadb()
        if c.count() == 0 and os.path.exists(pdf_path):
            raw_text = read_pdf(pdf_path)
            cleaned_text = clean_text(raw_text)
            chunks = chunk_text(cleaned_text, chunk_size=500, overlap=50)
            c, _ = setup_chromadb(chunks)
        collection = c
    return collection

@app.on_event("startup")
def startup_event():
    get_or_init_collection()

class QueryRequest(BaseModel):
    query: str
    prompt_id: int = 1
    custom_prompt: Optional[str] = None

class QueryResponse(BaseModel):
    query: str
    answer: str
    prompt_id: int
    prompt_title: str
    retrieved_chunks: List[str]
    model_used: str
    error: Optional[str] = None

@app.get("/health")
def health_check():
    col = get_or_init_collection()
    return {
        "status": "healthy",
        "service": "TPC Automated Clearance Assistant (MiniCAP)",
        "indexed_chunks": col.count() if col else 0,
        "gemini_api_configured": bool(get_gemini_api_key())
    }

@app.get("/api/prompts")
def get_prompts():
    return PROMPTS

@app.post("/api/query", response_model=QueryResponse)
def query_rag(request: QueryRequest):
    if not request.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty.")
    
    col = get_or_init_collection()
    if not col:
        raise HTTPException(status_code=500, detail="ChromaDB collection is not available.")
    
    prompt_info = PROMPTS.get(request.prompt_id, PROMPTS[1])
    system_prompt = request.custom_prompt if request.custom_prompt else prompt_info["prompt"]
    
    result = query_rag_engine(
        collection=col,
        query=request.query,
        system_prompt=system_prompt,
        api_key=get_gemini_api_key()
    )
    
    return QueryResponse(
        query=request.query,
        answer=result["answer"],
        prompt_id=request.prompt_id,
        prompt_title=prompt_info["title"],
        retrieved_chunks=result["retrieved_chunks"],
        model_used=result["model_used"],
        error=result.get("error")
    )

@app.get("/", response_class=FileResponse)
def serve_index():
    static_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static", "index.html")
    return FileResponse(static_file, media_type="text/html; charset=utf-8")
