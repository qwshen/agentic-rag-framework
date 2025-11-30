1. User Query Ingestion

- Capture and normalize the query.

- Optional: detect intent, domain, or complexity.

2. Document Retrieval

- Retrieve relevant documents using vector search, BM25, hybrid retrieval, etc.

- Possibly use multiple retrievers or sources.

3. Document Grading / Filtering

- Use grade prompts (e.g. “Is this document relevant to the query?”).

- Filter out irrelevant or low-quality documents.

- This step may trigger Iterative Retrieval if too few good documents are found.

4. Iterative Retrieval (Agentic Loop)

- If documents are low-quality or incomplete:

- Re-write the query to improve retrieval.

- Retry retrieval with refined query.

- Optionally use a fallback retriever.

- (Edge case) Ask the user for clarification.

- Once satisfactory context is found → move to generation.

5. Response Generation

- Use the final query + retrieved context to draft an answer.

6. Answer Grading / Self-Check (⚠️ The missing step)

- Use a grade prompt to verify:

  - Faithfulness to retrieved evidence (no hallucination).

  - Completeness (did it answer all parts?).

  - Relevance and clarity.

- If it fails → trigger:

  - Answer Re-writing, or

  - Iterative retrieval again (if missing context).

7. Answer Re-writing / Polishing

- Apply rewrite prompts to fix tone, grammar, conciseness, etc.

- Ensure the final message is user-ready.

8. Final Delivery

- Output to the user or external system.