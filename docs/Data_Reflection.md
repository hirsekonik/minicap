# Data Reflection
**Project:** TPC Automated Clearance Assistant (MiniCAP)

## Data Messiness
Working with real-world PDF and DOCX files for the TPC Student Handbook and Clearance Manual presented several immediate challenges during the ingestion phase:
1. **Recurring Headers/Footers:** The PDF format meant that "TPC STUDENT HANDBOOK v.04" and page numbers appeared repeatedly throughout the text, interrupting the natural flow of sentences and creating artificial noise for the embedding model.
2. **Formatting Artifacts:** Extracting raw text from documents often resulted in large blocks of empty whitespace, irregular line breaks, and mashed-together words where tables or columns were present.
3. **Information Density vs. Noise:** The documents contain a lot of "fluff"—such as the TPC Hymn, long lists of personnel, or historical background—which, while important, dilutes the relevance of actual actionable policy steps.

## Handling the Messiness
To handle these issues, I implemented a dedicated `clean_text()` function in `checkpoint1_pipeline.py`. 
- **Regex Cleaning:** I used Python's `re` module to automatically strip out the recurring header text ("TPC STUDENT HANDBOOK v.04") and standalone page numbers.
- **Whitespace Normalization:** I collapsed consecutive newlines and extra spaces into a single space (`re.sub(r'\s+', ' ', text)`) to ensure the tokenization process was evaluating actual words, not blank space.
- **Overlapping Chunks:** To deal with the density of the text, I used the `tiktoken` library to split the text into chunks of 500 tokens with a 50-token overlap. This sliding window approach ensures that if a clearance policy spans across a chunk boundary, the context isn't lost, making the resulting embeddings much more semantically accurate.
