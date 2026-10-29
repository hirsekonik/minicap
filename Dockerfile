FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000 \
    PYTHONPATH=/app \
    TOKENIZERS_PARALLELISM=false \
    HF_HUB_DISABLE_SYMLINKS_WARNING=1

# Install minimal system tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy dependency definition
COPY requirements.txt .

# Install PyTorch CPU first to optimize image size and build speed, then other dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu && \
    pip install --no-cache-dir -r requirements.txt

# Pre-cache embedding model weights
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')"

# Copy application code and dataset
COPY . .

# Pre-index knowledge base (Real System Codebase Flow + Handbook PDF) into persistent ChromaDB
RUN python -c "from src.pipeline import load_all_knowledge_chunks; from src.rag import setup_chromadb; setup_chromadb(load_all_knowledge_chunks())"

EXPOSE 8080
EXPOSE 8000

CMD ["python", "src/entrypoint.py"]
