# TPC Automated Clearance Assistant

Generative AI Capstone project repository for the TPC Automated Clearance Assistant. This project implements a Retrieval-Augmented Generation (RAG) pipeline to provide accurate answers regarding the TPC Student Handbook and Web-Based Clearance System.

## Project Architecture

The repository is structured into the following directories:

*   **`/data`**: Contains the source documents for the knowledge base.
    *   `TPC Student Handbook.pdf`
    *   `Capstone-Dalandan Mini.docx`
*   **`/src`**: Contains the Python source code for the data pipeline and RAG integration.
    *   `checkpoint1_pipeline.py`: Script to parse, clean, chunk, and embed the documents.
    *   `checkpoint2_rag.py`: Script to store embeddings in ChromaDB and query OpenAI's LLM using the retrieved context.
*   **`/docs`**: Directory for project documentation.

## Dependency Installation

To run this project, you must install the following Python packages:

```bash
pip install sentence-transformers chromadb openai tiktoken PyPDF2 python-docx beautifulsoup4
```

## Running the Application

1. **Process Data**: Run `checkpoint1_pipeline.py` to test the parsing, cleaning, and embedding steps.
2. **Run RAG Query**: Run `checkpoint2_rag.py` to index the documents into a local ChromaDB instance and test querying the system.
   *   *Note*: Ensure that the `OPENAI_API_KEY` environment variable is set with your OpenAI API key before running the RAG integration.
