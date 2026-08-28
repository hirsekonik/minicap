import os
import logging
import chromadb
from google import genai
from google.genai import types
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer
import checkpoint1_pipeline as cp1

# Suppress terminal warnings and noise
logging.getLogger("google.genai").setLevel(logging.ERROR)
os.environ["TOKENIZERS_PARALLELISM"] = "false"

# Safely load the environment variables
load_dotenv()

# Load the embedding model ONCE globally so it doesn't reload on every query
embedding_model = SentenceTransformer('all-MiniLM-L6-v2')

def setup_chromadb(chunks):
    db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'tpc_chroma_db')
    
    # Initialize a persistent client
    chroma_client = chromadb.PersistentClient(path=db_path)
    collection = chroma_client.get_or_create_collection(name="tpc_clearance")
    
    if collection.count() == 0:
        embeddings = embedding_model.encode(chunks).tolist()
        
        ids = [f"chunk_{i}" for i in range(len(chunks))]
        metadatas = [{"chunk_index": i} for i in range(len(chunks))]
        
        collection.add(
            embeddings=embeddings,
            documents=chunks,
            metadatas=metadatas,
            ids=ids
        )
    return collection, chroma_client

def perform_rag_query(collection, query, system_prompt, test_name):
    print(f"\n{'='*50}")
    print(f"TEST: {test_name}")
    print(f"QUERY: {query}")
    print(f"{'='*50}")
    
    # Use the global embedding model without reloading weights
    query_embedding = embedding_model.encode(query).tolist()
    
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=3 
    )
    
    retrieved_context = "\n\n".join(results['documents'][0])
    
    print("\n--- Retrieved Context (Preview) ---")
    if len(retrieved_context) > 300:
        print(retrieved_context[:300] + "...\n[Context truncated for readability]")
    else:
        print(retrieved_context)
    
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("Failed to initialize Gemini. Ensure GEMINI_API_KEY is set in your .env file.")
        return

    print(f"\n--- System Prompt Used ---")
    print(system_prompt)
    
    user_prompt = f"Context:\n{retrieved_context}\n\nQuestion: {query}"
    
    try:
        # Instantiate the new client
        client = genai.Client(api_key=api_key)
        
        print("\n--- Calling Gemini API ---")
        
        # Generate the response using the updated stable production model
        response = client.models.generate_content(
            model='gemini-3.6-flash',
            contents=user_prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                temperature=0.0
            )
        )
        
        print(f"\n--- Final LLM Response ---\n{response.text}\n")
        
    except Exception as e:
        print(f"\nError calling Gemini API: {e}")

def main():
    data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')
    pdf_path = os.path.join(data_dir, 'TPC Student Handbook.pdf')
    docx_path = os.path.join(data_dir, 'Capstone-Dalandan Mini.docx')
    
    raw_text = cp1.read_pdf(pdf_path) + "\n" + cp1.read_docx(docx_path)
    cleaned_text = cp1.clean_text(raw_text)
    chunks = cp1.chunk_text(cleaned_text)
    
    print("Initializing ChromaDB and loading embeddings...")
    collection, _ = setup_chromadb(chunks)
    
    print("\n=== TPC Checkpoint 2: API Integration & Prompt Engineering Demo ===")
    
    # Prompt 1: General Q&A (Strict Hallucination Prevention)
    prompt_1 = (
        "You are the official TPC Automated Clearance & Academic Policy Assistant. "
        "Answer questions based ONLY on the provided context retrieved from the TPC Student Handbook "
        "and the Web-Based Clearance System manual. If the answer is not contained within the provided context, "
        "you must state exactly: 'I dont have an answer for that'. Do not use outside knowledge."
    )
    query_1 = "What is the capital of France?" # Intentional out-of-scope query
    
    # Prompt 2: Step-by-Step Extractor
    prompt_2 = (
        "You are the TPC Clearance Step-by-Step Guide. Your job is to read the provided context and extract any actionable "
        "requirements or steps. Format your answer as a strict, numbered checklist. Do not include introductory fluff or conversational text. "
        "If the context does not contain actionable steps related to the query, output: 'No actionable steps found in context.'"
    )
    query_2 = "What are the steps to get clearance?"
    
    # Prompt 3: Document/Requirement Extractor
    prompt_3 = (
        "You are the TPC Document Extractor. Analyze the provided context and list ONLY the physical or digital documents "
        "required for the process mentioned in the query. Format as a bulleted list. Do not include process steps, locations, or conversational text. "
        "If no documents are mentioned, output 'No documents required.'"
    )
    query_3 = "What documents do I need for clearance?"

    # Run the demo suite
    perform_rag_query(collection, query_1, prompt_1, "Prompt 1 (Hallucination Prevention)")
    perform_rag_query(collection, query_2, prompt_2, "Prompt 2 (Step-by-Step Extractor)")
    perform_rag_query(collection, query_3, prompt_3, "Prompt 3 (Document Extractor)")

if __name__ == "__main__":
    main()