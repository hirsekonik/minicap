# TPC Automated Clearance Assistant

Generative AI Capstone project repository for the TPC Automated Clearance Assistant. This project implements a Retrieval-Augmented Generation (RAG) pipeline to provide accurate answers regarding the TPC Student Handbook and Web-Based Clearance System.

## Project Architecture

The repository is structured into the following directories:

*   **`/data`**: Contains the source documents for the knowledge base.
    *   `TPC Student Handbook.pdf`
    *   `Capstone-Dalandan Mini.docx`
*   **`/src`**: Contains the Python source code for the data pipeline and RAG integration.
    *   `pipeline.py`: Script to parse, clean, chunk, and generate dense vector embeddings for documents.
    *   `rag.py`: Script to store embeddings in ChromaDB and query the LLM (Gemini) using retrieved context and prompt engineering.
*   **`/notebooks`**: Contains the interactive exploratory and preprocessing notebook.
    *   `01_text_preprocessing.ipynb`: Interactive Jupyter Notebook with cleaning, normalization, and tokenization demonstrations.
*   **`/docs`**: Directory for project documentation and design portfolios.

## Dependency Installation

To run this project, ensure the virtual environment dependencies are installed:

```bash
pip install sentence-transformers chromadb google-genai tiktoken PyPDF2 python-docx python-dotenv
```

## Running the Application

1. **Process Data & Embeddings**: Run `pipeline.py` to test document ingestion, cleaning, chunking, and embedding generation:
   ```bash
   python src/pipeline.py
   ```
2. **Run RAG Query**: Run `rag.py` to index documents into the persistent local ChromaDB instance and test hallucination-prevention prompt queries:
   ```bash
   python src/rag.py
   ```
   * *Note*: Ensure that `GEMINI_API_KEY` is configured in your `.env` file.
