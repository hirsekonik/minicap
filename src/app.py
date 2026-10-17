import os
import sys
from typing import Optional, List
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Safe imports for internal modules
try:
    from src.rag import setup_chromadb, query_rag_engine, PROMPTS
    from src.pipeline import read_pdf, clean_text, chunk_text
except ImportError:
    from rag import setup_chromadb, query_rag_engine, PROMPTS
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
        "gemini_api_configured": bool(os.environ.get("GEMINI_API_KEY"))
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
        api_key=os.environ.get("GEMINI_API_KEY")
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

@app.get("/", response_class=HTMLResponse)
def serve_index():
    return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>TPC Automated Clearance Assistant | MiniCAP RAG</title>
    <meta name="description" content="Official TPC Automated Clearance & Academic Policy RAG Assistant. Powered by ChromaDB and Gemini LLM.">
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-primary: #0a0e17;
            --bg-secondary: #111827;
            --bg-card: rgba(17, 24, 39, 0.75);
            --bg-hover: #1f293d;
            --border-color: rgba(255, 255, 255, 0.08);
            --border-active: rgba(99, 102, 241, 0.5);
            --primary: #6366f1;
            --primary-glow: rgba(99, 102, 241, 0.25);
            --primary-gradient: linear-gradient(135deg, #6366f1 0%, #8b5cf6 50%, #ec4899 100%);
            --text-primary: #f9fafb;
            --text-secondary: #9ca3af;
            --text-muted: #6b7280;
            --accent-green: #10b981;
            --accent-yellow: #f59e0b;
            --shadow-lg: 0 20px 25px -5px rgba(0, 0, 0, 0.5), 0 8px 10px -6px rgba(0, 0, 0, 0.5);
        }

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
            font-family: 'Plus Jakarta Sans', sans-serif;
            -webkit-font-smoothing: antialiased;
        }

        body {
            background-color: var(--bg-primary);
            color: var(--text-primary);
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            overflow-x: hidden;
            background-image: 
                radial-gradient(circle at 15% 15%, rgba(99, 102, 241, 0.08) 0%, transparent 40%),
                radial-gradient(circle at 85% 85%, rgba(236, 72, 153, 0.06) 0%, transparent 40%);
        }

        header {
            border-bottom: 1px solid var(--border-color);
            background: rgba(10, 14, 23, 0.85);
            backdrop-filter: blur(16px);
            position: sticky;
            top: 0;
            z-index: 50;
            padding: 1rem 1.5rem;
        }

        .header-container {
            max-width: 1200px;
            margin: 0 auto;
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 1rem;
        }

        .brand-badge {
            display: flex;
            align-items: center;
            gap: 0.75rem;
        }

        .brand-logo {
            width: 40px;
            height: 40px;
            border-radius: 10px;
            background: var(--primary-gradient);
            display: flex;
            align-items: center;
            justify-content: center;
            box-shadow: 0 4px 14px var(--primary-glow);
            font-weight: 800;
            font-size: 1.2rem;
            color: white;
        }

        .brand-title h1 {
            font-size: 1.15rem;
            font-weight: 700;
            letter-spacing: -0.02em;
            background: linear-gradient(180deg, #ffffff 0%, #cbd5e1 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }

        .brand-title p {
            font-size: 0.78rem;
            color: var(--text-secondary);
        }

        .header-actions {
            display: flex;
            align-items: center;
            gap: 0.75rem;
        }

        .status-pill {
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
            padding: 0.35rem 0.75rem;
            border-radius: 9999px;
            font-size: 0.75rem;
            font-weight: 600;
            background: rgba(16, 185, 129, 0.1);
            color: var(--accent-green);
            border: 1px solid rgba(16, 185, 129, 0.2);
        }

        .status-dot {
            width: 7px;
            height: 7px;
            border-radius: 50%;
            background-color: var(--accent-green);
            box-shadow: 0 0 8px var(--accent-green);
            animation: pulse 2s infinite;
        }

        @keyframes pulse {
            0%, 100% { opacity: 1; transform: scale(1); }
            50% { opacity: 0.4; transform: scale(0.9); }
        }

        .api-link {
            text-decoration: none;
            padding: 0.35rem 0.85rem;
            border-radius: 8px;
            font-size: 0.75rem;
            font-weight: 600;
            color: var(--text-secondary);
            border: 1px solid var(--border-color);
            transition: all 0.2s ease;
        }

        .api-link:hover {
            color: var(--text-primary);
            border-color: var(--primary);
            background: var(--bg-hover);
        }

        main {
            flex: 1;
            max-width: 1200px;
            width: 100%;
            margin: 0 auto;
            padding: 1.5rem;
            display: grid;
            grid-template-columns: 360px 1fr;
            gap: 1.5rem;
        }

        @media (max-width: 900px) {
            main {
                grid-template-columns: 1fr;
            }
        }

        .sidebar {
            display: flex;
            flex-direction: column;
            gap: 1.25rem;
        }

        .glass-card {
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 16px;
            padding: 1.25rem;
            backdrop-filter: blur(12px);
            box-shadow: var(--shadow-lg);
        }

        .section-heading {
            font-size: 0.82rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: var(--text-muted);
            margin-bottom: 0.75rem;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }

        .mode-button {
            width: 100%;
            background: transparent;
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 0.85rem;
            text-align: left;
            cursor: pointer;
            transition: all 0.2s ease;
            margin-bottom: 0.6rem;
            display: block;
        }

        .mode-button:hover {
            background: var(--bg-hover);
            border-color: rgba(255, 255, 255, 0.2);
        }

        .mode-button.active {
            background: rgba(99, 102, 241, 0.12);
            border-color: var(--border-active);
            box-shadow: 0 0 16px rgba(99, 102, 241, 0.15);
        }

        .mode-title {
            font-size: 0.88rem;
            font-weight: 700;
            color: var(--text-primary);
            margin-bottom: 0.2rem;
        }

        .mode-desc {
            font-size: 0.74rem;
            color: var(--text-secondary);
            line-height: 1.4;
        }

        .suggestion-group {
            display: flex;
            flex-direction: column;
            gap: 0.5rem;
            margin-top: 0.5rem;
        }

        .suggestion-chip {
            background: var(--bg-secondary);
            border: 1px solid var(--border-color);
            border-radius: 10px;
            padding: 0.65rem 0.85rem;
            font-size: 0.78rem;
            color: var(--text-secondary);
            cursor: pointer;
            transition: all 0.2s;
            text-align: left;
            line-height: 1.35;
        }

        .suggestion-chip:hover {
            background: var(--bg-hover);
            color: var(--text-primary);
            border-color: var(--primary);
            transform: translateX(2px);
        }

        .suggestion-chip.test-hallucination {
            border-left: 3px solid var(--accent-yellow);
        }

        .chat-container {
            display: flex;
            flex-direction: column;
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 16px;
            backdrop-filter: blur(12px);
            box-shadow: var(--shadow-lg);
            height: calc(100vh - 120px);
            min-height: 550px;
            overflow: hidden;
        }

        .chat-messages {
            flex: 1;
            padding: 1.5rem;
            overflow-y: auto;
            display: flex;
            flex-direction: column;
            gap: 1.25rem;
        }

        .message-bubble {
            max-width: 85%;
            padding: 1rem 1.25rem;
            border-radius: 16px;
            font-size: 0.92rem;
            line-height: 1.6;
        }

        .user-message {
            align-self: flex-end;
            background: var(--primary-gradient);
            color: white;
            border-bottom-right-radius: 4px;
            box-shadow: 0 4px 14px var(--primary-glow);
        }

        .bot-message {
            align-self: flex-start;
            background: var(--bg-secondary);
            border: 1px solid var(--border-color);
            color: var(--text-primary);
            border-bottom-left-radius: 4px;
        }

        .bot-meta {
            display: flex;
            align-items: center;
            gap: 0.5rem;
            margin-bottom: 0.5rem;
            font-size: 0.72rem;
            color: var(--text-muted);
        }

        .bot-model-tag {
            background: rgba(99, 102, 241, 0.15);
            color: #a5b4fc;
            padding: 0.15rem 0.45rem;
            border-radius: 4px;
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.7rem;
        }

        .sources-toggle {
            margin-top: 0.75rem;
            background: transparent;
            border: none;
            color: #818cf8;
            font-size: 0.75rem;
            font-weight: 600;
            cursor: pointer;
            display: inline-flex;
            align-items: center;
            gap: 0.35rem;
        }

        .sources-drawer {
            margin-top: 0.6rem;
            padding: 0.75rem;
            background: rgba(0, 0, 0, 0.3);
            border-radius: 8px;
            border-left: 3px solid var(--primary);
            display: none;
            font-size: 0.75rem;
            color: var(--text-secondary);
            font-family: 'JetBrains Mono', monospace;
            white-space: pre-wrap;
            max-height: 200px;
            overflow-y: auto;
        }

        .sources-drawer.open {
            display: block;
        }

        .chat-input-area {
            border-top: 1px solid var(--border-color);
            padding: 1rem 1.25rem;
            background: rgba(17, 24, 39, 0.95);
        }

        .chat-form {
            display: flex;
            gap: 0.75rem;
        }

        .chat-input {
            flex: 1;
            background: var(--bg-primary);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 0.85rem 1.15rem;
            color: var(--text-primary);
            font-size: 0.92rem;
            outline: none;
            transition: all 0.2s;
        }

        .chat-input:focus {
            border-color: var(--primary);
            box-shadow: 0 0 0 3px var(--primary-glow);
        }

        .send-button {
            background: var(--primary-gradient);
            border: none;
            border-radius: 12px;
            padding: 0 1.5rem;
            color: white;
            font-weight: 600;
            font-size: 0.92rem;
            cursor: pointer;
            box-shadow: 0 4px 14px var(--primary-glow);
            transition: all 0.2s;
            display: flex;
            align-items: center;
            justify-content: center;
        }

        .send-button:hover:not(:disabled) {
            transform: translateY(-1px);
            box-shadow: 0 6px 18px var(--primary-glow);
        }

        .send-button:disabled {
            opacity: 0.5;
            cursor: not-allowed;
        }

        .loading-dots span {
            display: inline-block;
            width: 6px;
            height: 6px;
            margin: 0 2px;
            background: #a5b4fc;
            border-radius: 50%;
            animation: bounce 1.4s infinite ease-in-out both;
        }
        .loading-dots span:nth-child(1) { animation-delay: -0.32s; }
        .loading-dots span:nth-child(2) { animation-delay: -0.16s; }

        @keyframes bounce {
            0%, 80%, 100% { transform: scale(0); }
            40% { transform: scale(1); }
        }
    </style>
</head>
<body>
    <header>
        <div class="header-container">
            <div class="brand-badge">
                <div class="brand-logo">T</div>
                <div class="brand-title">
                    <h1>TPC Automated Clearance Assistant</h1>
                    <p>MiniCAP Grounded RAG &bull; Student Handbook & Clearance Manual</p>
                </div>
            </div>
            <div class="header-actions">
                <span class="status-pill" id="health-status">
                    <span class="status-dot"></span>
                    <span id="health-text">Online &bull; ChromaDB Ready</span>
                </span>
                <a href="/docs" target="_blank" class="api-link" id="swagger-link">REST API Docs</a>
            </div>
        </div>
    </header>

    <main>
        <div class="sidebar">
            <div class="glass-card">
                <div class="section-heading">Select Prompt Mode</div>
                <button class="mode-button active" id="btn-mode-1" onclick="selectMode(1)">
                    <div class="mode-title">1. General Policy Q&A</div>
                    <div class="mode-desc">Strict context grounding. Refuses with "I dont have an answer for that".</div>
                </button>
                <button class="mode-button" id="btn-mode-2" onclick="selectMode(2)">
                    <div class="mode-title">2. Step-by-Step Extractor</div>
                    <div class="mode-desc">Extracts actionable procedures into numbered checklists (1, 2, 3).</div>
                </button>
                <button class="mode-button" id="btn-mode-3" onclick="selectMode(3)">
                    <div class="mode-title">3. Document Extractor</div>
                    <div class="mode-desc">Isolates only required slips, forms, and documents into a bulleted list.</div>
                </button>
            </div>

            <div class="glass-card">
                <div class="section-heading">Evaluator Suggested Queries</div>
                <div class="suggestion-group" id="suggestions-list">
                    <!-- Dynamic suggestions populated via JS -->
                </div>
            </div>
        </div>

        <div class="chat-container">
            <div class="chat-messages" id="chat-messages">
                <div class="message-bubble bot-message">
                    <div class="bot-meta">
                        <span>TPC Assistant</span>
                        <span class="bot-model-tag">MiniCAP RAG</span>
                    </div>
                    Hello! I am the TPC Automated Clearance & Academic Policy Assistant. Ask any question regarding the TPC Student Handbook or Web-Based Clearance System, or pick a sample question on the left to test retrieval and hallucination prevention!
                </div>
            </div>

            <div class="chat-input-area">
                <form class="chat-form" id="chat-form" onsubmit="handleSend(event)">
                    <input 
                        type="text" 
                        class="chat-input" 
                        id="user-query-input" 
                        placeholder="Ask about clearance steps, signatory offices, or policies..." 
                        autocomplete="off"
                        required
                    />
                    <button type="submit" class="send-button" id="send-button">
                        <span>Send</span>
                    </button>
                </form>
            </div>
        </div>
    </main>

    <script>
        let currentPromptId = 1;
        const suggestionsMap = {
            1: [
                { text: "What are the signatory offices involved in the student clearance process?", type: "in-scope" },
                { text: "Can TPC students apply for a tuition discount through the Foreign Aviation Flight School program?", type: "hallucination" }
            ],
            2: [
                { text: "What are the steps to submit and complete a clearance request in the web-based clearance system?", type: "in-scope" },
                { text: "What are the step-by-step procedures to apply for a student visa for studying abroad in Japan?", type: "hallucination" }
            ],
            3: [
                { text: "What documents or clearance forms do students need for final clearance?", type: "in-scope" },
                { text: "What are the behavioral rules and conduct expected inside the campus library?", type: "hallucination" }
            ]
        };

        function selectMode(id) {
            currentPromptId = id;
            [1, 2, 3].forEach(i => {
                const btn = document.getElementById(`btn-mode-${i}`);
                if (i === id) btn.classList.add('active');
                else btn.classList.remove('active');
            });
            renderSuggestions();
        }

        function renderSuggestions() {
            const container = document.getElementById('suggestions-list');
            container.innerHTML = '';
            const items = suggestionsMap[currentPromptId] || [];
            items.forEach((item, idx) => {
                const div = document.createElement('div');
                div.className = `suggestion-chip ${item.type === 'hallucination' ? 'test-hallucination' : ''}`;
                const label = item.type === 'hallucination' ? '⚠️ Hallucination Test' : '✓ In-Scope Query';
                div.innerHTML = `<strong>${label}:</strong><br>"${item.text}"`;
                div.onclick = () => {
                    document.getElementById('user-query-input').value = item.text;
                    document.getElementById('user-query-input').focus();
                };
                container.appendChild(div);
            });
        }

        renderSuggestions();

        async function handleSend(e) {
            e.preventDefault();
            const input = document.getElementById('user-query-input');
            const query = input.value.trim();
            if (!query) return;

            input.value = '';
            appendUserMessage(query);

            const sendBtn = document.getElementById('send-button');
            sendBtn.disabled = true;

            const loadingBubble = appendLoadingMessage();

            try {
                const response = await fetch('/api/query', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ query: query, prompt_id: currentPromptId })
                });

                const data = await response.json();
                loadingBubble.remove();

                if (response.ok) {
                    appendBotMessage(data.answer, data.model_used, data.retrieved_chunks);
                } else {
                    appendBotMessage(`Error: ${data.detail || 'Could not fetch response'}`, 'error', []);
                }
            } catch (err) {
                loadingBubble.remove();
                appendBotMessage(`Network Error: ${err.message}`, 'error', []);
            } finally {
                sendBtn.disabled = false;
                document.getElementById('user-query-input').focus();
            }
        }

        function appendUserMessage(text) {
            const chat = document.getElementById('chat-messages');
            const div = document.createElement('div');
            div.className = 'message-bubble user-message';
            div.textContent = text;
            chat.appendChild(div);
            chat.scrollTop = chat.scrollHeight;
        }

        function appendLoadingMessage() {
            const chat = document.getElementById('chat-messages');
            const div = document.createElement('div');
            div.className = 'message-bubble bot-message';
            div.innerHTML = `
                <div class="bot-meta"><span>Retrieving context & querying LLM...</span></div>
                <div class="loading-dots"><span></span><span></span><span></span></div>
            `;
            chat.appendChild(div);
            chat.scrollTop = chat.scrollHeight;
            return div;
        }

        function appendBotMessage(answer, model, chunks) {
            const chat = document.getElementById('chat-messages');
            const div = document.createElement('div');
            div.className = 'message-bubble bot-message';

            let sourcesHtml = '';
            if (chunks && chunks.length > 0) {
                const snippet = chunks.map((c, i) => `[Chunk ${i+1}]\n${c.trim()}`).join('\n\n---\n\n');
                sourcesHtml = `
                    <button class="sources-toggle" onclick="this.nextElementSibling.classList.toggle('open')">
                        🔍 View ${chunks.length} Grounded Context Chunks &darr;
                    </button>
                    <div class="sources-drawer">${escapeHtml(snippet)}</div>
                `;
            }

            div.innerHTML = `
                <div class="bot-meta">
                    <span>TPC Assistant</span>
                    <span class="bot-model-tag">${escapeHtml(model || 'Grounded')}</span>
                </div>
                <div>${formatResponseText(answer)}</div>
                ${sourcesHtml}
            `;
            chat.appendChild(div);
            chat.scrollTop = chat.scrollHeight;
        }

        function formatResponseText(text) {
            return escapeHtml(text).replace(/\\n/g, '<br>');
        }

        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }
    </script>
</body>
</html>
"""
