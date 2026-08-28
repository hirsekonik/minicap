# Project Proposal: Mini Generative AI Capstone
**Project Title:** TPC Automated Clearance & Academic Policy Assistant (MiniCAP)

## 1. Problem Statement
Navigating the clearance process and understanding academic policies at Talibon Polytechnic College (TPC) can be time-consuming and confusing for students. Students often have to manually search through the TPC Student Handbook or the Web-Based Clearance System manual, leading to misinterpretations, frustration, and repeated questions directed at the Office of Student Affairs and Services (OSAS). There is a need for an automated, intelligent system that can instantly retrieve accurate, context-grounded answers to these specific institutional queries.

## 2. Target Users
- **Current TPC Students:** Specifically graduating students or those undergoing semester clearance who need quick, reliable answers regarding requirements, steps, and academic policies.
- **TPC Administration (OSAS):** Indirectly benefits by having routine, repetitive questions offloaded to the AI assistant, allowing staff to focus on more complex student issues.

## 3. Chosen Theme
**Document/Knowledge-Base Q&A Assistant.**
This project implements a Retrieval-Augmented Generation (RAG) assistant grounded strictly in TPC's official documentation. It acts as an interactive policy and clearance guide that refuses to hallucinate information outside of its provided context.

## 4. Dataset Source(s)
The dataset consists of authentic institutional documents:
1. **TPC Student Handbook (PDF):** Contains comprehensive academic policies, rules, and student guidelines.
2. **Web-Based Clearance System Manual (DOCX):** Contains specific steps, required documents, and procedural guidelines for securing student clearance.
*Combined, these documents provide well over the required 20-30 pages of text necessary to form a robust retrieval knowledge base.*

## 5. Success Criteria
To consider this project a success, the system must achieve the following:
- **Accurate Ingestion:** Successfully extract, clean, and chunk text from both PDF and DOCX formats without losing semantic meaning.
- **High-Quality Retrieval:** Return highly relevant context chunks for a given user query using dense vector embeddings (`all-MiniLM-L6-v2`) and a vector database (ChromaDB).
- **Zero Hallucination:** The Large Language Model (Gemini) must strictly synthesize answers *only* from the retrieved context. If the answer is not present, it must safely refuse to answer rather than guessing.
- **Actionable Formatting:** The system must be capable of extracting policies and formatting them into readable, step-by-step checklists or required document lists when prompted.
