"""
Retrieval-Augmented Generation (RAG) Interactive Assistant
TPC Automated Clearance Assistant (MiniCAP)

Features:
1. ChromaDB Persistent Vector Database initialization and indexing (Handbook PDF + Real System Codebase Flow).
2. Dense semantic similarity search over TPC handbook & system codebase chunks (all-MiniLM-L6-v2).
3. Live Host System / Portal DOM Context Integration.
4. Grounded Chat Completion via Gemini API with strict hallucination prevention.
"""

import os
import sys
import re
import logging
import warnings
import chromadb
from google import genai
from google.genai import types
from dotenv import load_dotenv

try:
    from src.pipeline import read_pdf, clean_text, chunk_text, load_all_knowledge_chunks, SentenceTransformer
except ImportError:
    from pipeline import read_pdf, clean_text, chunk_text, load_all_knowledge_chunks, SentenceTransformer

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

# --- Unified Institutional Chatbot Persona (Anthropic / OpenAI Grade + Exact Real Codebase Flow) ---
SYSTEM_PROMPT = (
    "You are the official **Talibon Polytechnic College (TPC) Student Clearance Assistant**—an intelligent, articulate, and deeply helpful AI advisor designed with the conversational polish of Anthropic Claude and OpenAI ChatGPT.\n\n"
    "### 🎯 Your Core Mission\n"
    "Help TPC students, faculty, staff, and administrators navigate the **Web-Based Student Clearance System** (built with Laravel 11, Vue 3, Inertia.js, and Tailwind CSS), understand the **14 official signatory offices**, inspect their **live portal dashboard status** (when provided in `Live Host System Screen Context`), resolve holds or rejections, and find accurate answers from both the **real system codebase/user manual** and the **TPC Student Handbook (v.04)**.\n\n"
    "### 🏛️ Canonical Clearance Architecture — The 14 Official Signatory Offices (`OfficeSeeder.php` Sort Order 1–14)\n"
    "In the TPC Web-Based Student Clearance System, every student clearance application routes through **14 designated signatory offices** (13 regular offices where `is_final_approver = false`, followed by the 14th final executive office where `is_final_approver = true`), grouped into two categories:\n"
    "**A. Student Services Signatories (Sort Order 1 to 9):**\n"
    "1. **Guidance Office** (`Sort Order 1`) — Counseling records, exit interview, and guidance clearance\n"
    "2. **Medical-Dental Clinic** (`Sort Order 2`) — Health records and clinic clearance\n"
    "3. **Library** (`Sort Order 3`) — Book returns, borrower's card, and settlement of library fines\n"
    "4. **Security and Safety Office** (`Sort Order 4`) — Campus safety compliance, ID/parking, and violation records\n"
    "5. **Equipment and Facilities** (`Sort Order 5`) — Laboratory apparatus, tools, and borrowed campus equipment (Property Custodian)\n"
    "6. **Supreme Student Government (SSG)** (`Sort Order 6`) — Student council dues, event attendance, and officer turnover/liquidation\n"
    "7. **PE/Sports** (`Sort Order 7`) — Athletics gear, sports uniforms, and PE equipment clearance\n"
    "8. **Canteen** (`Sort Order 8`) — Settlement of any outstanding meal or canteen balances\n"
    "9. **Registrar** (`Sort Order 9`) — Academic records, grades submission, Form 137/credentials, and academic units verification\n\n"
    "**B. Offices and Administration Signatories (Sort Order 10 to 14):**\n"
    "10. **Program Head** (`Sort Order 10`) — Department requirements and hardbound Capstone/Thesis submission\n"
    "11. **Office of Student Affairs and Services (OSAS)** (`Sort Order 11`) — Disciplinary clearance, Good Moral eligibility, and mandatory Student ID surrender\n"
    "12. **Office of the Vice President for Academic Affairs (VPAA)** (`Sort Order 12`) — Academic affairs compliance validation\n"
    "13. **Office of the Vice President for Administration (VPA)** (`Sort Order 13`) — Administrative and financial compliance sign-off\n"
    "14. **Office of the College President** (`Sort Order 14`, `is_final_approver = true`) — Sole **Final Approver** that unlocks only after all 13 regular offices are `Approved`, generating the official Clearance Receipt & QR Code\n\n"
    "**CRITICAL RULE ON SIGNATORIES:**\n"
    "Whenever a user asks about signatory offices, required departments, or who approves clearance, you MUST list all **14 official offices** above in their exact order, clearly organized into **Student Services (1–9)** and **Offices and Administration (10–14)**.\n\n"
    "### 🔄 Exact System Workflows & Role Rules (From the Real Codebase)\n"
    "- **7 Supported Academic Courses (`CourseSeeder.php`)**: `BSIS` (BS in Information System), `BAEL` (BA in English Language), `BAPS` (BS in Political Science), `BSA` (BS in Agriculture), `BSAIS` (BS in Accounting Information System), `BECED` (Bachelor of Early Childhood Education), and `BSCRIM` (BS in Criminology).\n"
    "- **Student Workflow (`/dashboard`)**:\n"
    "  1. **Self-Registration (`/register`)**: Students register with their Student ID, Full Name, Course, Year Level (`1st`–`4th Year`), Email, and Password.\n"
    "  2. **Dashboard Overview & 5-Second Live Polling**: Displays 4 summary cards (**Approved**, **Pending**, **Not Cleared**, and **Final Status**: `Not Started` / `In Progress` / `Fully Approved`), an **Overall Progress Bar (`0%`–`100%`)**, and polls automatically every 5 seconds.\n"
    "  3. **Submit Clearance Request (`POST /student/clearance-requests`)**: When the Clearance Period is `open`, click **\"Submit Clearance Request\"** (and **\"Select All Available\"**) to request offices that have 0 unmet prerequisites (transitions from `not_requested` to `pending`). Offices with unmet prerequisites show a **Locked** badge specifying which prerequisite offices must be cleared first.\n"
    "  4. **Request More Offices (`PATCH /student/clearance-requests/request-more-offices`)**: As prerequisite offices approve, dependent offices automatically unlock. Click **\"Request More Offices\"** to submit to newly unlocked offices.\n"
    "  5. **Resolve a Rejection (`PATCH /student/clearance-approvals/{approval}/mark-as-complied`)**: If an office rejects a request (`rejected`), the office card turns red and displays the mandatory staff **Remarks** explaining the exact deficiency. After settling the deficiency with that office, click **\"Mark as Complied\"** on the card—this resets the status from `rejected` back to `pending` and notifies the office staff to re-evaluate.\n"
    "  6. **Final Approval & Official Receipt (`/clearance-receipts/{id}` & `/clearance-receipts/{id}/download`)**: Once **all 13 regular offices (100%) are `Approved`**, the **Office of the College President** unlocks. After the President approves, overall status becomes `Cleared` (`Fully Approved`), generating an **Official Receipt Number (`TPC-CLR-YYYY-XXXXXX`)**, a **32-character cryptographic Verification Code**, and an **Anti-Fraud QR Code**. Students click **\"View Clearance Receipt\"** to **Print Receipt** or **\"Download PDF\"**.\n"
    "- **Office Staff Workflow (`/staff/pending-requests`)**: Scoped strictly to their assigned `office_id`. Staff can filter by `Pending`/`Approved`/`Rejected`, search by Student ID/Name, filter by Course/Year, click **\"Approve\"** (single) or **\"Approve All\"** (bulk), click **\"Reject\"** (requires mandatory deficiency `remarks` up to 1000 chars), or click **\"Mark as Complied\"** on behalf of a student.\n"
    "- **College President Workflow (`/president/final-approvals`)**: Sole Final Approver. Students only enter the **Ready for Final Approval** queue when all 13 regular offices are `Approved`. Can click **\"Approve\"** (single), **\"Auto Approve All Ready\"** (bulk final approval), **\"Reject\"** (with mandatory remarks), or **\"Mark as Complied\"**.\n"
    "- **OSAS Admin Workflow (`/admin/dashboard`)**: Manages User Accounts (`/admin/users`), Course Modules (`/admin/course-modules`), Office Prerequisites (`/admin/office-prerequisites`), Master Audit View (`/admin/clearance-requests`), Reports with **Export CSV** & **Print Report** (`/admin/reports`), and System Settings (`/admin/settings`) where Admin can **Start/Stop Clearance Period** (`clearance_status` = `open`/`closed`), broadcast a **Clearance Notice Banner** (`clearance_notice`), or update the **Active Semester & School Year** by typing `RESET CLEARANCES` (preserving all past records while starting a new term cycle).\n"
    "- **Public Anti-Fraud QR Verification (`/verify-clearance/{verificationCode}`)**: Anyone can scan the QR code on a printed or PDF receipt without logging in to verify authenticity (`VALID AND FULLY CLEARED` green banner).\n\n"
    "### 🖥️ Using Live Host System Screen Context vs. RAG Context\n"
    "1. **Live Screen Context (`Live Host System Screen Context`)**:\n"
    "   - The embedded widget automatically scans the active page of the student's clearance portal (logged-in student's name, Student ID, course, year level, clearance progress percentage, approved/pending/rejected department counts, and active OSAS banners).\n"
    "   - If the user asks *'What is my name?'*, *'Who am I?'*, *'What is my Student ID / course?'*, *'What is my current clearance status?'*, or *'Why can\\'t I submit my clearance right now?'*, use the **`Live Host System Screen Context`** (or any name they introduced in `Recent Conversation History`) to answer accurately!\n"
    "   - **NEVER** guess the capstone researcher/author names from the PDF cover page (*San Ryan Farlolen Auguis*, *Sean Leo Ramos Añabieza*, or *Madel Dehillo Romana*) as the current user's name!\n"
    "2. **Out-of-Scope & Unanswerable Questions**:\n"
    "   - If a user asks about topics outside Talibon Polytechnic College clearance, their active portal dashboard, and student handbook guidelines (e.g., booking flights, cooking recipes, weather, general coding, sports trivia, or policies not present in the retrieved TPC context), **do not make things up or use general internet knowledge**.\n"
    "   - Politely explain that as the official **TPC Student Clearance Assistant**, you only answer questions grounded in the **Talibon Polytechnic College Student Handbook and Clearance System**, and suggest 2–3 relevant TPC clearance questions they can ask instead.\n\n"
    "### ✨ Communication & Formatting Standards (Claude / ChatGPT Style)\n"
    "1. **Zero Robotic Boilerplate**: **NEVER** start a message with *'Based on the provided document context...'*, *'According to the retrieved chunks...'*, or *'From the text provided...'*. Speak directly, naturally, and authoritatively like a seasoned university advisor.\n"
    "2. **Executive Summary First**: Begin every policy or procedural answer with a clear, direct 1–2 sentence summary that immediately answers the question.\n"
    "3. **Clean Visual Hierarchy**:\n"
    "   - Use descriptive Markdown subheaders (`### 📋 Step-by-Step Procedure`, `### 🏛️ The 14 Required Signatory Offices`, `### ⚠️ How to Resolve a Rejection`).\n"
    "   - Use numbered lists (`1.`, `2.`, `3.`) with **bold action titles** for workflows.\n"
    "   - Use bullet points for required documents, prerequisites, or office rules.\n"
    "   - Include a concise `> 💡 **Tip:** ...` blockquote when a practical portal tip helps the user.\n"
    "4. **Concise & Scannable**: Keep responses well-paced, easy to scan, and free of repetitive filler."
)

PROMPTS = {
    1: {
        "title": "TPC Student Clearance Assistant",
        "prompt": SYSTEM_PROMPT,
        "style": "Conversational assistant grounded in official TPC clearance codebase workflows and student handbook policies.",
        "suggestions": [
            "How do I submit and track a clearance request in the portal?",
            "What signatory offices are required to approve my clearance?",
            "What happens if an office rejects my clearance request?",
            "How do I download my Clearance Receipt and how does QR verification work?"
        ]
    }
}


def setup_chromadb(chunks=None):
    """Initializes persistent ChromaDB and indexes chunks (auto-upgrading if codebase chunks are missing)."""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    db_path = os.path.join(base_dir, 'tpc_chroma_db')
    
    chroma_client = chromadb.PersistentClient(path=db_path)
    collection = chroma_client.get_or_create_collection(name="tpc_clearance")
    
    current_count = collection.count()
    # Auto-rebuild if empty OR if it only has the legacy 88 PDF chunks without TPC_System_Codebase_Flow.md (122 total)
    if current_count < 115:
        if not chunks:
            chunks = load_all_knowledge_chunks()
        if chunks and len(chunks) > current_count:
            print(f"[ChromaDB] Upgrading vector database ({current_count} -> {len(chunks)} chunks with Real System Codebase Flow)...", flush=True)
            if current_count > 0:
                try:
                    chroma_client.delete_collection(name="tpc_clearance")
                except Exception:
                    pass
                collection = chroma_client.get_or_create_collection(name="tpc_clearance")
            
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
        print(f"[ChromaDB] Connected. Active collection contains {current_count} chunks.\n", flush=True)
        
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


def _should_hide_references(query: str, answer_text: str) -> bool:
    """
    Returns True when the response is a conversational greeting, live portal profile check,
    or an out-of-scope / unanswerable refusal where showing 10 handbook chunks would be misleading.
    """
    q_low = (query or "").strip().lower()
    a_low = (answer_text or "").strip().lower()

    if re.match(r"^(hi|hello|hey|good\s+(morning|afternoon|evening)|thanks|thank\s+you|who\s+are\s+you|what\s+can\s+you\s+do|help)\W*$", q_low):
        return True

    if re.search(r"\b(what\s+is\s+my\s+name|what'?s\s+my\s+name|whats\s+my\s+name|who\s+am\s+i|do\s+you\s+know\s+my\s+name)\b", q_low):
        return True

    refusal_phrases = [
        "dedicated exclusively to",
        "don't have access to your personal name",
        "don't know your personal name",
        "do not store private",
        "not in our official documentation",
        "cannot answer questions",
        "only answer questions grounded",
        "i dont have an answer for that",
        "outside the scope",
        "unrelated to talibon polytechnic college"
    ]
    return any(p in a_low for p in refusal_phrases)


def query_rag_engine(collection, query: str, system_prompt: str, api_key: str = None, history: list = None, page_context: str = None):
    """Executes semantic search against ChromaDB and generates grounded response via Gemini LLM."""
    if not api_key:
        api_key = get_gemini_api_key()

    # 1. Similarity Search
    query_embedding = embedding_model.encode(query).tolist()
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=10
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

    # Format live host page context if scanned from the real portal/system
    page_context_block = ""
    if page_context and str(page_context).strip():
        page_context_block = f"Live Host System Screen Context (Scanned from User's Active Portal Page):\n{str(page_context).strip()}\n\n"

    # Format recent conversation history if provided
    history_block = ""
    if history and isinstance(history, list):
        turns = []
        for msg in history[-6:]:
            if isinstance(msg, dict) and msg.get("text"):
                role = "Student" if msg.get("sender") == "user" else "Assistant"
                turns.append(f"{role}: {msg.get('text')}")
        if turns:
            history_block = "Recent Conversation History:\n" + "\n".join(turns) + "\n\n"

    # 2. Call Gemini LLM with context grounding + live screen context
    user_prompt = f"{page_context_block}Retrieved Handbook & System Codebase Context:\n{retrieved_context}\n\n{history_block}Question: {query}"
    client = genai.Client(api_key=api_key)

    # Verified active Gemini models in priority order
    candidate_models = [
        'gemini-2.5-flash',
        'gemini-3.8-flash',
        'gemini-3.5-flash',
        'gemini-flash-latest',
        'gemini-3-flash-preview',
        'gemini-2.5-flash-lite',
        'gemini-3.1-flash-lite',
        'gemini-flash-lite-latest',
        'gemini-2.5-pro',
        'gemini-pro-latest'
    ]

    last_err = None
    attempted_log = []

    for model_name in candidate_models:
        try:
            print(f"[Gemini Attempt] Trying model: {model_name}...", flush=True)
            response = client.models.generate_content(
                model=model_name,
                contents=user_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    temperature=0.3
                )
            )
            answer_text = (response.text or "").strip()
            if not answer_text and response.candidates and len(response.candidates) > 0:
                candidate = response.candidates[0]
                if candidate.content and candidate.content.parts:
                    answer_text = "".join([p.text for p in candidate.content.parts if hasattr(p, 'text') and p.text]).strip()

            if not answer_text:
                answer_text = "I don't have an answer for that based on the official TPC documentation."

            print(f"[Gemini Success] Successfully generated response with {model_name}", flush=True)
            out_chunks = [] if _should_hide_references(query, answer_text) else retrieved_docs
            return {
                "answer": answer_text,
                "retrieved_chunks": out_chunks,
                "model_used": model_name,
                "error": None
            }
        except Exception as e:
            err_msg = str(e)
            print(f"[Gemini Error on {model_name}]: {err_msg}", flush=True)
            attempted_log.append(f"{model_name}: {err_msg}")
            last_err = err_msg

            if "free tier is not available" in err_msg.lower() or "aistudio.google.com/billing" in err_msg.lower():
                break
            continue

    is_billing_err = any("free tier is not available" in l.lower() or "aistudio.google.com/billing" in l.lower() for l in attempted_log)
    is_quota_err = any("429" in l or "resource_exhausted" in l.lower() for l in attempted_log)

    if is_billing_err:
        guide_msg = (
            "### ⚠️ Gemini API Project Notice\n"
            "The Google Cloud project linked to this API key does not have the free tier enabled. "
            "Please use an API key created in Google AI Studio (`https://aistudio.google.com/app/apikey`)."
        )
    elif is_quota_err:
        guide_msg = (
            "### 📖 Official TPC Handbook Guidance *(ChromaDB Vector Fallback)*\n"
            "Our live AI synthesizer is briefly cooling down due to the free-tier per-minute rate limit, "
            "so here are the **most relevant official passages** retrieved directly from our **ChromaDB Knowledge Base**:"
        )
    else:
        guide_msg = "### 📖 Official TPC Handbook Guidance\nHere are the relevant passages retrieved from the **TPC Student Handbook & Clearance Manual**:"

    if retrieved_docs:
        formatted_excerpts = "\n\n".join([f"> **Excerpt {i+1}:** {doc.strip()}" for i, doc in enumerate(retrieved_docs[:3])])
        guide_msg += f"\n\n{formatted_excerpts}"

    return {
        "answer": guide_msg,
        "retrieved_chunks": retrieved_docs,
        "model_used": "chromadb_fallback" if retrieved_docs else "none",
        "error": f"Attempted models ({len(attempted_log)}): {'; '.join(attempted_log[:3])}"
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
        print("No matching context chunks required/found.", flush=True)

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
    
    for pid in [1]:
        ask_questions_for_prompt(collection, prompt_id=pid, target_count=2)
        
    print("\n" + "=" * 65)
    print("PROMPT EVALUATIONS COMPLETED SUCCESSFULLY!")
    print("=" * 65)


def run_auto_benchmark(collection):
    """Automated benchmark demonstration running predefined queries."""
    print("\n" + "=" * 65)
    print("RUNNING AUTOMATED BENCHMARK DEMO")
    print("=" * 65)
    import time
    for pid in [1]:
        p_info = PROMPTS[pid]
        for query in p_info["suggestions"]:
            perform_rag_query(collection, query, p_info["prompt"], p_info["title"])
            time.sleep(1)


def main():
    print("=" * 65)
    print("TPC AUTOMATED CLEARANCE ASSISTANT - INTERACTIVE RAG")
    print("=" * 65)
    print("Initializing document knowledge base (Codebase Flow + Handbook PDF)...")
    chunks = load_all_knowledge_chunks(chunk_size=500, overlap=50)
    collection, _ = setup_chromadb(chunks)
    
    while True:
        print("\n" + "=" * 65)
        print("                   MAIN INTERACTIVE MENU")
        print("=" * 65)
        print("  [1] TPC Student Clearance Assistant (Interactive Q&A)")
        print("  [2] Run Quick Automated Demo")
        print("  [0] Exit")
        print("=" * 65)
        
        choice = input("Enter your choice (0-2): ").strip()
        
        if choice == '1':
            ask_questions_for_prompt(collection, prompt_id=1, target_count=2)
        elif choice == '2':
            run_auto_benchmark(collection)
        elif choice in ['0', 'exit', 'quit']:
            print("\nExiting TPC Assistant. Goodbye!\n")
            break
        else:
            print("[Warning] Invalid option. Please enter 0, 1, or 2.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nSession terminated by user. Goodbye!")
