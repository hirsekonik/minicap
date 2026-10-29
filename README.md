# TPC Automated Clearance Assistant (MiniCAP)

## 1. Project Title & Purpose
**TPC Automated Clearance Assistant (MiniCAP)** is a context-grounded Retrieval-Augmented Generation (RAG) web application and embeddable chatbot built for **Talibon Polytechnic College (TPC)**.

- **Problem Solved:** Every semester, TPC students must complete clearance across **14 designated signatory offices** (9 under Student Services and 5 under Administration). Because institutional rules, prerequisites, and deficiency resolution steps are spread across a lengthy PDF Student Handbook and a separate Web-Based Clearance System Manual, students frequently struggle to find accurate answers, while the Office of Student Affairs and Services (OSAS) is overwhelmed with repetitive inquiries.
- **Purpose:** MiniCAP provides students with instant, source-cited, step-by-step guidance strictly grounded in official TPC documents—complete with expandable handbook source references and strict anti-hallucination guardrails for out-of-scope questions.

---

## 2. Live Deployed Application Link
- **Public Live App (No Login Required):** [https://minicap-production.up.railway.app](https://minicap-production.up.railway.app) *(Deployed on Railway; opens directly to the interactive TPC Student Clearance Portal with the floating AI Assistant)*
- **Standalone Full-Screen AI Workspace:** [https://minicap-production.up.railway.app/widget](https://minicap-production.up.railway.app/widget)
- **API Health & Indexed Chunks Check:** [https://minicap-production.up.railway.app/health](https://minicap-production.up.railway.app/health)
- **Interactive OpenAPI / Swagger Docs:** [https://minicap-production.up.railway.app/docs](https://minicap-production.up.railway.app/docs)

> **⚠️ Usage Limit & Free-Tier API Quota Notice (For Grading & Testing):**
> This application uses the **Google Gemini API (`google-genai`)** on the standard Free Tier quota (~15 requests per minute / 1,500 requests per day).
> - To ensure uninterrupted evaluation during grading, the backend (`src/rag.py`) automatically cascades across multiple active Gemini Flash/Pro model endpoints if a single model hits a per-minute rate limit.
> - Even if the external Gemini API quota is temporarily exhausted (`HTTP 429`), the system includes a built-in **ChromaDB Knowledge Base Fallback** that still retrieves and displays the top matching institutional handbook passages directly from our vector database.

---

## 3. Tech Stack
| Component | Technology Used | Purpose |
| :--- | :--- | :--- |
| **Backend & Orchestration Framework** | **FastAPI** (`Python 3.11`) + Custom RAG Pipeline (`src/pipeline.py`, `src/rag.py`) | REST API (`/api/query`, `/health`), document ingestion, and context routing |
| **Tokenizer & Chunking** | **TikToken** (`cl100k_base`) | Token-bounded sliding-window text chunking (`500` tokens per chunk, `50`-token overlap) |
| **Embedding Model** | **Hugging Face `sentence-transformers/all-MiniLM-L6-v2`** | Encodes document chunks and user queries into normalized **384-dimensional dense vectors** |
| **Vector Store** | **ChromaDB** (`chromadb.PersistentClient`) | Persistent local/container vector index (`tpc_chroma_db`) using **Cosine Similarity** |
| **Large Language Model (LLM)** | **Google Gemini** (`google-genai` SDK, `temperature=0.35`) | Context-grounded response synthesis with strict out-of-scope refusal guardrails |
| **Frontend Interface** | **HTML5 / CSS3 / Vanilla JS** + `marked.js` + Web Speech API | TPC Student Clearance Portal dashboard, Mobile Phone Simulator, and Standalone AI View with source citation drawers |
| **Deployment & Containerization** | **Docker** (`Dockerfile`) + **Railway** | Containerized cloud deployment with pre-cached embeddings and pre-indexed ChromaDB |

---

## 4. Where the Sample Documents Came From (Knowledge Source)
The knowledge base located in `/data` (`data/Master_Capstone_Dataset.pdf`) is compiled from two authentic institutional documents from **Talibon Polytechnic College (TPC)**:
1. **Official TPC Student Handbook (v.04):** Contains official college academic policies, grading guidelines, student conduct rules, retention policies, and institutional responsibilities.
2. **TPC Web-Based Student Clearance System Documentation & Manual:** Contains the canonical 14-signatory clearance workflow (9 Student Services offices: *Guidance, Medical-Dental Clinic, Library, Security & Safety, Equipment & Facilities, SSG, Registrar, PE/Sports, Canteen*; and 5 Administration offices: *Program Head, OSAS, VPAA, VPA, and College President*), clearance submission steps, rejection/re-evaluation procedures, and TOR prerequisites.

---

## 5. How the End-to-End RAG Pipeline Works
1. **Document Ingestion (`src/pipeline.py` — `read_pdf`)**: Extracts raw text from `data/Master_Capstone_Dataset.pdf` using `PyPDF2`.
2. **Multi-Stage Text Cleaning (`src/pipeline.py` — `TextCleaner`)**:
   - Strips repeating headers and footers (*"TPC STUDENT HANDBOOK v.04"*).
   - Decouples page numbers glued to section titles (e.g., `30Section 5` $\rightarrow$ `Section 5`).
   - Repairs broken line-wrap hyphenation and normalizes Unicode/whitespace artifacts.
3. **Sliding-Window Token Chunking (`src/pipeline.py` — `chunk_text`)**: Splits cleaned text into **500-token chunks** with a **50-token overlap** using `tiktoken` (`cl100k_base`) so policies spanning across paragraphs retain full semantic context.
4. **Dense Embedding & Vector Indexing (`src/rag.py` — `setup_chromadb`)**: Encodes all chunks into **384-dimensional normalized vectors** via `sentence-transformers/all-MiniLM-L6-v2` and stores them persistently in `tpc_chroma_db`.
5. **Semantic Retrieval (`src/rag.py` — `query_rag_engine`)**: When a user submits a question, the query is embedded with `all-MiniLM-L6-v2` and compared against ChromaDB using **Cosine Similarity** to retrieve the **top 10 most relevant handbook chunks**.
6. **Grounded Generation & Source Citation (`src/app.py` & `src/static/widget.html`)**: The retrieved chunks are injected into Google Gemini (`temperature=0.35`) alongside a strict system prompt. The UI renders the grounded Markdown answer AND attaches a **`📖 Verified References`** drawer displaying the exact retrieved passages used, while politely refusing any out-of-scope questions.

---

## 6. Repository Structure
* **`/data`**: Source documents (`Master_Capstone_Dataset.pdf`).
* **`/src`**: Application source code:
  * `pipeline.py`: PDF ingestion, regex text cleaning, 500-token sliding-window chunking, and MiniLM embedding generation.
  * `rag.py`: ChromaDB persistent vector store setup, similarity retrieval, and grounded Gemini LLM inference.
  * `app.py`: FastAPI web server exposing `/`, `/widget`, `/api/query`, `/health`, and `/docs`.
  * `static/`: Frontend portal (`index.html`), standalone/popup chat interface (`widget.html`), and embed script (`widget.js`).
* **`/notebooks`**: `01_text_preprocessing.ipynb` (interactive cleaning, normalization, and tokenization demos).
* **`/docs`**: Project Proposal, Data Reflection, Prompt Engineering Document, and Distance Metric Comparison.
* **`.env.example`**: Template showing required environment variables (`GEMINI_API_KEY`) with **no exposed secrets**.
* **`Dockerfile` & `requirements.txt`**: Reproducible container and package configuration.

---

## 7. How to Run Locally

### Option A: Local Python Environment
1. **Clone the repository and install dependencies**:
   ```bash
   git clone https://github.com/hirsekonik/minicap.git
   cd minicap
   pip install -r requirements.txt
   ```
2. **Configure your environment variables**:
   Copy `.env.example` to `.env` and add your Google Gemini API key:
   ```bash
   cp .env.example .env
   # Edit .env and set: GEMINI_API_KEY=your_api_key_here
   ```
3. **Start the FastAPI web application**:
   ```bash
   python src/entrypoint.py
   ```
   Open **`http://localhost:8000`** in your browser to use the TPC Student Clearance Portal & AI Assistant (or **`http://localhost:8000/widget`** for the standalone full-screen view).

4. **(Optional) Run the CLI Pipeline & Terminal RAG Demos**:
   ```bash
   python src/pipeline.py
   python src/rag.py
   ```

### Option B: Via Docker
```bash
docker build -t minicap-rag .
docker run -p 8000:8000 -e GEMINI_API_KEY="your_api_key_here" minicap-rag
```
Then open **`http://localhost:8000`** in your browser.
