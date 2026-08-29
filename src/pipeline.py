"""
Data Ingestion, Text Preprocessing, and Embedding Pipeline
TPC Automated Clearance Assistant (MiniCAP)

Features:
1. Document Ingestion (PDF & DOCX extraction).
2. Multi-Stage Text Cleaning & Normalization:
   - Header/footer removal (handbook and clearance system titles)
   - Decoupling glued page numbers (e.g., '30Section 5' -> 'Section 5')
   - Unicode artifact repair ('\ufffd' -> "'") and line-wrap de-hyphenation
   - Whitespace and newline compaction
3. Token-Bounded Sliding-Window Chunking (500 tokens, 50-token overlap via TikToken).
4. Dense Vector Embedding Generation (384-dimensional vectors via all-MiniLM-L6-v2).
"""

import os
import sys
import re
import unicodedata
from typing import List, Dict, Tuple, Any
import tiktoken
import PyPDF2

# Ensure UTF-8 output encoding in Windows terminal
if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

try:
    import docx
except ImportError:
    docx = None

try:
    from sentence_transformers import SentenceTransformer
except Exception:
    import torch
    import torch.nn.functional as F
    from transformers import AutoTokenizer, AutoModel

    class SentenceTransformer:
        def __init__(self, model_name='sentence-transformers/all-MiniLM-L6-v2'):
            self.tokenizer = AutoTokenizer.from_pretrained(model_name)
            self.model = AutoModel.from_pretrained(model_name)
            self.model.eval()

        def encode(self, sentences, **kwargs):
            is_single = isinstance(sentences, str)
            if is_single:
                sentences = [sentences]
            encoded = self.tokenizer(sentences, padding=True, truncation=True, return_tensors='pt', max_length=512)
            with torch.no_grad():
                out = self.model(**encoded)
                token_embeddings = out[0]
                attention_mask = encoded['attention_mask'].unsqueeze(-1).expand(token_embeddings.size()).float()
                sum_embeddings = torch.sum(token_embeddings * attention_mask, 1)
                sum_mask = torch.clamp(attention_mask.sum(1), min=1e-9)
                embeddings = sum_embeddings / sum_mask
                embeddings = F.normalize(embeddings, p=2, dim=1)
            res = embeddings.cpu().numpy()
            return res[0] if is_single else res


def read_pdf(file_path: str) -> str:
    """Extracts raw text from a PDF file."""
    text = ""
    try:
        with open(file_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            for page in reader.pages:
                text += (page.extract_text() or "") + "\n"
    except Exception as e:
        print(f"[Error] Failed to read PDF {file_path}: {e}")
    return text


def read_docx(file_path: str) -> str:
    """Extracts text from a DOCX file."""
    if not docx:
        print("[Warning] python-docx not installed.")
        return ""
    text = ""
    try:
        doc = docx.Document(file_path)
        for para in doc.paragraphs:
            if para.text.strip():
                text += para.text + "\n"
    except Exception as e:
        print(f"[Error] Failed to read DOCX {file_path}: {e}")
    return text


class TextCleaner:
    """Modular text cleaning rules for institutional handbook and manual documents."""

    @staticmethod
    def remove_headers_and_footers(text: str) -> str:
        text = re.sub(r'TPC\s+STUDENT\s+HANDBOOK\s+v\.?\s*0\s*4', '', text, flags=re.IGNORECASE)
        text = re.sub(r'CAPSTONE\s+PROJECT\s+DOCUMENTATION:\s*WEB-BASED\s+STUDENT\s+CLEARANCE\s+SYSTEM', '', text, flags=re.IGNORECASE)
        return text

    @staticmethod
    def clean_page_numbers(text: str) -> str:
        # Standalone lines with numbers
        text = re.sub(r'^\s*\d+\s*$', '', text, flags=re.MULTILINE)
        # Numbers prepended directly to section headings (e.g., '30Section', '136 ARTICLE')
        text = re.sub(r'^\s*\d+\s*(?=[A-Za-z])', '', text, flags=re.MULTILINE)
        return text

    @staticmethod
    def fix_line_wrap_hyphenation(text: str) -> str:
        return re.sub(r'(\b\w+)-\s*\n\s*(\w+\b)', r'\1\2', text)

    @staticmethod
    def fix_unicode_artifacts(text: str) -> str:
        text = unicodedata.normalize('NFKC', text)
        text = text.replace('\ufffd', "'")
        text = text.replace('‘', "'").replace('’', "'").replace('“', '"').replace('”', '"')
        text = text.replace('–', '-').replace('—', '-')
        return text

    @staticmethod
    def normalize_whitespace(text: str) -> str:
        text = text.replace('\u00a0', ' ')
        text = re.sub(r'\n\s*\n+', '\n\n', text)
        text = re.sub(r'[ \t]+', ' ', text)
        text = re.sub(r' +(?=\n)', '', text)
        return text.strip()

    @classmethod
    def clean(cls, text: str) -> str:
        t = cls.remove_headers_and_footers(text)
        t = cls.clean_page_numbers(t)
        t = cls.fix_line_wrap_hyphenation(t)
        t = cls.fix_unicode_artifacts(t)
        t = cls.normalize_whitespace(t)
        return t


def clean_text(text: str) -> str:
    """Convenience wrapper for cleaning raw text."""
    return TextCleaner.clean(text)


def chunk_text(text: str, model_name: str = "cl100k_base", chunk_size: int = 500, overlap: int = 50) -> List[str]:
    """Splits normalized text into sliding-window chunks with token overlap."""
    tokenizer = tiktoken.get_encoding(model_name)
    tokens = tokenizer.encode(text)
    
    chunks = []
    step = max(1, chunk_size - overlap)
    for i in range(0, len(tokens), step):
        chunk_tokens = tokens[i:i + chunk_size]
        chunks.append(tokenizer.decode(chunk_tokens).strip())
        if i + chunk_size >= len(tokens):
            break
            
    return chunks


def main():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_dir = os.path.join(base_dir, 'data')
    pdf_path = os.path.join(data_dir, 'Master_Capstone_Dataset.pdf')

    print("=" * 60)
    print("TPC DATA PIPELINE & EMBEDDING GENERATION DEMO")
    print("=" * 60)

    # 1. Read Raw Documents
    print("\n[Step 1] Ingesting Raw Documents...")
    raw_text = read_pdf(pdf_path)
    print(f"  - Total Raw Characters: {len(raw_text):,}")
    print(f"  - Total Raw Lines: {len(raw_text.splitlines()):,}")

    # 2. Clean Text
    print("\n[Step 2] Cleaning & Normalizing Text...")
    cleaned_text = clean_text(raw_text)
    print(f"  - Cleaned Characters: {len(cleaned_text):,}")
    print(f"  - Noise Characters Stripped: {len(raw_text) - len(cleaned_text):,}")

    # 3. Before/After Example
    print("\n--- Before vs. After Cleaning Demonstration (Sample) ---")
    sample_dirty = "TPC STUDENT HANDBOOK v.0 4 \n30Section 5. In order to graduate with honors, 80% credits..."
    print(f"BEFORE: {repr(sample_dirty)}")
    print(f"AFTER : {repr(clean_text(sample_dirty))}")

    # 4. Chunk Text
    print("\n[Step 3] Token-Bounded Chunking (500 tokens, 50 overlap)...")
    chunks = chunk_text(cleaned_text, chunk_size=500, overlap=50)
    print(f"  - Total Chunks Created: {len(chunks)}")
    if chunks:
        print(f"  - Chunk 0 Character Length: {len(chunks[0])}")

    # 5. Generate Dense Vector Embeddings
    print("\n[Step 4] Generating Embeddings (sentence-transformers/all-MiniLM-L6-v2)...")
    model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
    
    demo_chunks = chunks[:5]
    if not demo_chunks:
        print("[Error] No chunks available to embed.")
        return

    embeddings = model.encode(demo_chunks)
    
    print("\n--- Embedding Dimensions & Verification ---")
    print(f"  - Chunks Embedded for Demo: {len(demo_chunks)}")
    print(f"  - Embedding Matrix Shape   : {embeddings.shape} -> (batch_size, vector_dimension)")
    print(f"  - Single Vector Dimension  : {embeddings.shape[1]}")
    print(f"  - Sample Vector Preview    : {embeddings[0][:6].round(4)} ... [384 floats total]")
    print("\n" + "=" * 60)
    print("PIPELINE EXECUTION COMPLETE - READY FOR RAG RETRIEVAL")
    print("=" * 60)


if __name__ == "__main__":
    main()
