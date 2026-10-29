import os
import sys
from typing import Optional, List, Dict, Any
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
    from src.pipeline import read_pdf, clean_text, chunk_text, load_all_knowledge_chunks
except ImportError:
    from rag import setup_chromadb, query_rag_engine, PROMPTS, get_gemini_api_key
    from pipeline import read_pdf, clean_text, chunk_text, load_all_knowledge_chunks

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
        c, _ = setup_chromadb()
        collection = c
    return collection

@app.on_event("startup")
def startup_event():
    get_or_init_collection()

class QueryRequest(BaseModel):
    query: str
    prompt_id: int = 1
    custom_prompt: Optional[str] = None
    history: Optional[List[Dict[str, Any]]] = None
    page_context: Optional[str] = None

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

@app.get("/api/models")
def get_available_models():
    api_key = get_gemini_api_key()
    if not api_key:
        return {"status": "error", "message": "API key not found"}
    try:
        from google import genai
        client = genai.Client(api_key=api_key)
        models = []
        for m in client.models.list():
            actions = getattr(m, 'supported_actions', []) or []
            models.append({
                "name": m.name,
                "display_name": getattr(m, 'display_name', None),
                "supported_actions": actions
            })
        return {"status": "ok", "count": len(models), "models": models}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/api/debug-gemini")
def debug_gemini(model: str = "gemini-flash-latest"):
    api_key = get_gemini_api_key()
    if not api_key:
        return {"error": "API key not configured"}
    try:
        from google import genai
        client = genai.Client(api_key=api_key)
        res = client.models.generate_content(
            model=model,
            contents="Say hello"
        )
        return {"status": "success", "response": res.text}
    except Exception as e:
        return {"status": "error", "model": model, "exception_type": type(e).__name__, "message": str(e)}

@app.post("/api/query", response_model=QueryResponse)
def query_rag(request: QueryRequest):
    if not request.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty.")
    
    col = get_or_init_collection()
    if not col:
        raise HTTPException(status_code=500, detail="ChromaDB collection is not available.")
    
    prompt_info = PROMPTS.get(request.prompt_id, PROMPTS.get(1, {}))
    system_prompt = request.custom_prompt if request.custom_prompt else prompt_info.get("prompt")
    
    result = query_rag_engine(
        collection=col,
        query=request.query,
        system_prompt=system_prompt,
        api_key=get_gemini_api_key(),
        history=request.history,
        page_context=request.page_context
    )
    
    return QueryResponse(
        query=request.query,
        answer=result["answer"],
        prompt_id=request.prompt_id or 1,
        prompt_title=prompt_info.get("title", "TPC Clearance Assistant"),
        retrieved_chunks=result["retrieved_chunks"],
        model_used=result["model_used"],
        error=result.get("error")
    )

@app.get("/", response_class=FileResponse)
def serve_index():
    static_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static", "index.html")
    return FileResponse(static_file, media_type="text/html; charset=utf-8")

@app.get("/widget", response_class=FileResponse)
def serve_widget():
    static_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static", "widget.html")
    return FileResponse(static_file, media_type="text/html; charset=utf-8")

@app.get("/widget.js", response_class=FileResponse)
def serve_widget_js():
    static_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static", "widget.js")
    return FileResponse(static_file, media_type="application/javascript")
