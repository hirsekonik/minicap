import os
import re
import tiktoken
import PyPDF2
import docx
from sentence_transformers import SentenceTransformer

def read_pdf(file_path):
    text = ""
    try:
        with open(file_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            for page in reader.pages:
                text += page.extract_text() + "\n"
    except Exception as e:
        print(f"Error reading PDF {file_path}: {e}")
    return text

def read_docx(file_path):
    text = ""
    try:
        doc = docx.Document(file_path)
        for para in doc.paragraphs:
            text += para.text + "\n"
    except Exception as e:
        print(f"Error reading DOCX {file_path}: {e}")
    return text

def clean_text(text):
    # Remove headers
    text = re.sub(r'TPC STUDENT HANDBOOK v\.04', '', text, flags=re.IGNORECASE)
    # Remove standalone page numbers (e.g., just numbers on a line or surrounded by whitespace)
    text = re.sub(r'^\s*\d+\s*$', '', text, flags=re.MULTILINE)
    # Remove extra whitespace and newlines
    text = re.sub(r'\s+', ' ', text)
    # Strip leading/trailing spaces
    return text.strip()

def chunk_text(text, model_name="cl100k_base", chunk_size=500, overlap=50):
    tokenizer = tiktoken.get_encoding(model_name)
    tokens = tokenizer.encode(text)
    
    chunks = []
    # Sliding window
    for i in range(0, len(tokens), chunk_size - overlap):
        chunk_tokens = tokens[i:i + chunk_size]
        chunks.append(tokenizer.decode(chunk_tokens))
        if i + chunk_size >= len(tokens):
            break
            
    return chunks

def main():
    data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')
    pdf_path = os.path.join(data_dir, 'TPC Student Handbook.pdf')
    docx_path = os.path.join(data_dir, 'Capstone-Dalandan Mini.docx')

    print("--- Reading Documents ---")
    pdf_text = read_pdf(pdf_path)
    docx_text = read_docx(docx_path)
    
    raw_text = pdf_text + "\n" + docx_text
    
    print("\n--- Raw Text Demonstration (First 500 characters) ---")
    print(raw_text[:500])
    
    print("\n--- Cleaning Text ---")
    cleaned_text = clean_text(raw_text)
    
    print("\n--- Cleaned Text Demonstration (First 500 characters) ---")
    print(cleaned_text[:500])

    print("\n--- Chunking Text ---")
    chunks = chunk_text(cleaned_text)
    print(f"Total chunks created: {len(chunks)}")
    
    if len(chunks) > 0:
        print(f"First chunk length (characters): {len(chunks[0])}")

    print("\n--- Generating Embeddings ---")
    model = SentenceTransformer('all-MiniLM-L6-v2')
    
    # We will just embed a few chunks for demonstration to keep it fast, 
    # but the prompt asks to generate embeddings and output final vector dimensions.
    # Let's embed the first 5 chunks to show dimensions.
    demo_chunks = chunks[:5]
    if not demo_chunks:
        print("No chunks to embed.")
        return

    embeddings = model.encode(demo_chunks)
    
    print("\n--- Embedding Dimensions ---")
    print(f"Number of chunks embedded for demo: {len(demo_chunks)}")
    print(f"Final vector dimension (shape): {embeddings.shape}")
    print(f"Single vector dimension: {len(embeddings[0])}")

if __name__ == "__main__":
    main()
