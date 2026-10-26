"""
Retrieval-Augmented Generation (RAG) Interactive Assistant
TPC Automated Clearance Assistant (MiniCAP)

Features:
1. ChromaDB Persistent Vector Database initialization and indexing.
2. Dense semantic similarity search over TPC handbook chunks (all-MiniLM-L6-v2).
3. Interactive Terminal Mode: 2 questions per prompt (1 in-scope + 1 hallucination test).
4. Grounded Chat Completion via Gemini API with strict hallucination prevention.
"""

import os
import sys
import logging
import warnings
import chromadb
from google import genai
from google.genai import types
from dotenv import load_dotenv

try:
    from src.pipeline import read_pdf, clean_text, chunk_text, SentenceTransformer
except ImportError:
    from pipeline import read_pdf, clean_text, chunk_text, SentenceTransformer

# Suppress background library warnings
warnings.filterwarnings("ignore")
logging.getLogger("google.genai").setLevel(logging.ERROR)
os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"

# Ensure UTF-8 output encoding in Windows terminal
if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

# Safely load environment variables (.env)
load_dotenv()

# Load the embedding model globally once
embedding_model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')

# --- 3 Engineered System Prompts ---
PROMPT_1_GENERAL = (
    "You are the official TPC Automated Clearance & Academic Policy Assistant. "
    "Answer questions based ONLY on the provided context retrieved from the TPC Student Handbook "
    "and the Web-Based Clearance System manual. If the answer is not contained within the provided context, "
    "you must state exactly: 'I dont have an answer for that'. Do not use outside knowledge."
)

PROMPT_2_STEPS = (
    "You are the TPC Clearance Step-by-Step Guide. Your job is to read the provided context and extract any actionable "
    "requirements or steps. Format your answer as a strict, numbered checklist. Do not include introductory fluff or conversational text. "
    "If the context does not contain actionable steps related to the query, output: 'No actionable steps found in context.'"
)

PROMPT_3_DOCS = (
    "You are the TPC Document Extractor. Analyze the provided context and list ONLY the physical or digital documents "
    "required for the process mentioned in the query. Format as a bulleted list. Do not include process steps, locations, or conversational text. "
    "If no documents are mentioned, output 'No documents required.'"
)

PROMPTS = {
    1: {
        "title": "Prompt 1: General Q&A Assistant (Policy Q&A + Hallucination Prevention)",
        "prompt": PROMPT_1_GENERAL,
        "style": "Answers policy queries strictly from context. Refuses with 'I dont have an answer for that'.",
        "suggestions": [
            "What are the signatory offices involved in the student clearance process?",
            "Can TPC students apply for a tuition discount through the Foreign Aviation Flight School program?"
        ]
    },
    2: {
        "title": "Prompt 2: Step-by-Step Extractor (Numbered Checklist)",
        "prompt": PROMPT_2_STEPS,
        "style": "Extracts actionable procedures into numbered checklists (1, 2, 3). Refuses non-procedures.",
        "suggestions": [
            "What are the steps to submit and complete a clearance request in the web-based clearance system?",
            "What are the step-by-step procedures to apply for a student visa for studying abroad in Japan?"
        ]
    },
    3: {
        "title": "Prompt 3: Document / Requirement Extractor (Bulleted List)",
        "prompt": PROMPT_3_DOCS,
        "style": "Isolates only required documents, slips, and receipts. Ignores narrative text.",
        "suggestions": [
            "What documents or clearance forms do students need for final clearance?",
            "What are the behavioral rules and conduct expected inside the campus library?"
        ]
    }
}


def setup_chromadb(chunks=None):
    """Initializes persistent ChromaDB and indexes chunks if not already present."""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    db_path = os.path.join(base_dir, 'tpc_chroma_db')
    
    chroma_client = chromadb.PersistentClient(path=db_path)
    collection = chroma_client.get_or_create_collection(name="tpc_clearance")
    
    if collection.count() == 0 and chunks:
        print("[ChromaDB] Indexing chunks into vector database...", flush=True)
        embeddings = embedding_model.encode(chunks).tolist()
        
        ids = [f"chunk_{i}" for i in range(len(chunks))]
        metadatas = [{"chunk_index": i} for i in range(len(chunks))]
        
        collection.add(
            embeddings=embeddings,
            documents=chunks,
            metadatas=metadatas,
            ids=ids
        )
        print(f"[ChromaDB] Indexed {len(chunks)} chunks successfully.\n", flush=True)
    else:
        print(f"[ChromaDB] Connected. Active collection contains {collection.count()} chunks.\n", flush=True)
        
    return collection, chroma_client


def get_gemini_api_key():
    """Retrieves the Gemini API key supporting any variable name or casing variation."""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    env_path = os.path.join(base_dir, '.env')
    if os.path.exists(env_path):
        load_dotenv(env_path)

    for key_name in ["GEMINI_API_KEY", "API_KEY", "API KEY", "APIKey", "GOOGLE_API_KEY", "api_key", "apikey", "Api_Key"]:
        val = os.environ.get(key_name)
        if val and val.strip():
            return val.strip().strip('"').strip("'")

    for k, v in os.environ.items():
        clean_k = k.replace("_", "").replace(" ", "").replace("-", "").lower()
        if clean_k in ["apikey", "geminiapikey", "googleapikey", "geminikey", "googlekey"]:
            if v and v.strip():
                return v.strip().strip('"').strip("'")
    return None


def query_rag_engine(collection, query: str, system_prompt: str, api_key: str = None):
    """Executes semantic search against ChromaDB and generates grounded response via Gemini LLM."""
    if not api_key:
        api_key = get_gemini_api_key()

    # 1. Similarity Search
    query_embedding = embedding_model.encode(query).tolist()
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=3
    )

    retrieved_docs = results['documents'][0] if results.get('documents') and len(results['documents']) > 0 else []
    retrieved_context = "\n\n".join(retrieved_docs)

    if not api_key:
        return {
            "answer": "Gemini API key is not configured. Please add GEMINI_API_KEY to your .env file or environment variables.",
            "retrieved_chunks": retrieved_docs,
            "model_used": "none",
            "error": "missing_api_key"
        }

    # 2. Call Gemini LLM with context grounding
    user_prompt = f"Context:\n{retrieved_context}\n\nQuestion: {query}"
    candidate_models = ['gemini-2.0-flash', 'gemini-1.5-flash', 'gemini-2.0-flash-lite', 'gemini-1.5-pro']

    client = genai.Client(api_key=api_key)
    last_err = None

    for model_name in candidate_models:
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=user_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    temperature=0.0
                )
            )
            answer_text = (response.text or "").strip()
            if not answer_text and response.candidates and len(response.candidates) > 0:
                candidate = response.candidates[0]
                if candidate.content and candidate.content.parts:
                    answer_text = "".join([p.text for p in candidate.content.parts if hasattr(p, 'text') and p.text]).strip()

            if not answer_text:
                answer_text = "I dont have an answer for that."

            return {
                "answer": answer_text,
                "retrieved_chunks": retrieved_docs,
                "model_used": model_name,
                "error": None
            }
        except Exception as e:
            last_err = str(e)
            continue

    return {
        "answer": f"Unable to complete query due to API error: {last_err or 'quota limit reached'}",
        "retrieved_chunks": retrieved_docs,
        "model_used": "none",
        "error": last_err
    }


def perform_rag_query(collection, query: str, system_prompt: str, prompt_label: str = ""):
    """Retrieves top-3 context chunks and queries Gemini LLM for terminal display."""
    print("\n" + "=" * 65, flush=True)
    if prompt_label:
        print(f"MODE : {prompt_label}", flush=True)
    print(f"QUERY: {query}", flush=True)
    print("=" * 65, flush=True)

    result = query_rag_engine(collection, query, system_prompt)

    print("\n--- Retrieved Context Preview ---", flush=True)
    if result["retrieved_chunks"]:
        preview = result["retrieved_chunks"][0][:250].strip()
        print(f"{preview}...\n[Top {len(result['retrieved_chunks'])} chunks retrieved]", flush=True)
    else:
        print("No matching context chunks found.", flush=True)

    print("\n" + "-" * 65, flush=True)
    print(f"BOT RESPONSE ({result['model_used']}):", flush=True)
    print("-" * 65, flush=True)
    print(result["answer"], flush=True)
    print("-" * 65 + "\n", flush=True)


def ask_questions_for_prompt(collection, prompt_id: int, target_count: int = 2):
    """Allows the user to interactively type 2 questions for a specific prompt."""
    p_info = PROMPTS[prompt_id]
    
    print("\n" + "#" * 65)
    print(f"  ACTIVE: {p_info['title']}")
    print(f"  BEHAVIOR: {p_info['style']}")
    print("#" * 65)
    
    q_num = 1
    while q_num <= target_count:
        suggested = p_info["suggestions"][(q_num - 1) % len(p_info["suggestions"])]
        q_type = "In-Scope Question" if q_num == 1 else "Hallucination Prevention Test"
        
        print(f"\n[Question {q_num}/{target_count} - {q_type}]")
        print(f"  * Suggested: \"{suggested}\"")
        print("  * Type your question, press ENTER to use suggested, or type 'back' for menu:")
        
        user_input = input(">> ").strip()
        
        if user_input.lower() in ['back', 'exit', 'quit', 'menu']:
            return
            
        final_query = user_input if user_input else suggested
        perform_rag_query(collection, final_query, p_info["prompt"], p_info["title"])
        q_num += 1

    print(f"\n[Notice] Completed {target_count} questions for this prompt.")
    cont = input("Ask an extra question for this prompt? (y/n): ").strip().lower()
    if cont == 'y':
        extra_query = input("Enter extra question: ").strip()
        if extra_query:
            perform_rag_query(collection, extra_query, p_info["prompt"], p_info["title"])


def guided_interactive_mode(collection):
    """Guided mode: Walk through each of the 3 prompts asking 2 questions each."""
    print("\n" + "=" * 65)
    print("STARTING GUIDED MODE: 2 Questions for Each of the 3 Prompts")
    print("=" * 65)
    
    for pid in [1, 2, 3]:
        ask_questions_for_prompt(collection, prompt_id=pid, target_count=2)
        
    print("\n" + "=" * 65)
    print("ALL 3 PROMPT EVALUATIONS COMPLETED SUCCESSFULLY!")
    print("=" * 65)


def run_auto_benchmark(collection):
    """Automated benchmark demonstration running predefined queries."""
    print("\n" + "=" * 65)
    print("RUNNING AUTOMATED BENCHMARK DEMO (3 PROMPTS)")
    print("=" * 65)
    import time
    for pid in [1, 2, 3]:
        p_info = PROMPTS[pid]
        for query in p_info["suggestions"]:
            perform_rag_query(collection, query, p_info["prompt"], p_info["title"])
            time.sleep(1)


def main():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    pdf_path = os.path.join(base_dir, 'data', 'Master_Capstone_Dataset.pdf')
    
    print("=" * 65)
    print("TPC AUTOMATED CLEARANCE ASSISTANT - INTERACTIVE RAG")
    print("=" * 65)
    print("Initializing document knowledge base...")
    raw_text = read_pdf(pdf_path)
    cleaned_text = clean_text(raw_text)
    chunks = chunk_text(cleaned_text, chunk_size=500, overlap=50)
    collection, _ = setup_chromadb(chunks)
    
    while True:
        print("\n" + "=" * 65)
        print("                   MAIN INTERACTIVE MENU")
        print("=" * 65)
        print("  [1] Prompt 1: General Q&A Assistant (2 Questions)")
        print("  [2] Prompt 2: Step-by-Step Extractor (2 Questions)")
        print("  [3] Prompt 3: Document Extractor (2 Questions)")
        print("  [4] Guided 2-Questions Walkthrough (All Prompts)")
        print("  [5] Run Quick Automated Demo")
        print("  [0] Exit")
        print("=" * 65)
        
        choice = input("Enter your choice (0-5): ").strip()
        
        if choice == '1':
            ask_questions_for_prompt(collection, prompt_id=1, target_count=2)
        elif choice == '2':
            ask_questions_for_prompt(collection, prompt_id=2, target_count=2)
        elif choice == '3':
            ask_questions_for_prompt(collection, prompt_id=3, target_count=2)
        elif choice == '4':
            guided_interactive_mode(collection)
        elif choice == '5':
            run_auto_benchmark(collection)
        elif choice in ['0', 'exit', 'quit']:
            print("\nExiting TPC Assistant. Goodbye!\n")
            break
        else:
            print("[Warning] Invalid option. Please enter 0, 1, 2, 3, 4, or 5.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nSession terminated by user. Goodbye!")
