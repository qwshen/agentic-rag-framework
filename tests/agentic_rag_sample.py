"""
Agentic RAG example with:
- separate LLMs for generation and grading
- query rewriting loop
- document grading and answer self-check
- conversation context (ConversationBufferMemory)
"""

from typing import List, Tuple
from langchain.chat_models import ChatOpenAI
from langchain.embeddings import OpenAIEmbeddings
from langchain.vectorstores import FAISS
from langchain.schema import Document
from langchain.prompts import PromptTemplate
from langchain.memory import ConversationBufferMemory
from langchain.schema import HumanMessage
import time

# -----------------------------
# Config: choose models + params
# -----------------------------
GENERATION_MODEL = "gpt-4o"        # used to generate answers
GRADING_MODEL = "gpt-4o-mini"      # used for grading / rewriting (lower temp)
REWRITE_MODEL = "gpt-4o-mini"      # used for query rewrite (could be same as grading)
TEMPERATURE_GEN = 0.7
TEMPERATURE_GRADER = 0.0
MAX_ITER = 3                       # max agentic iterations

# -----------------------------
# Instantiate LLMs and embeddings
# -----------------------------
generation_llm = ChatOpenAI(model=GENERATION_MODEL, temperature=TEMPERATURE_GEN)
grading_llm = ChatOpenAI(model=GRADING_MODEL, temperature=TEMPERATURE_GRADER)
rewrite_llm = ChatOpenAI(model=REWRITE_MODEL, temperature=TEMPERATURE_GRADER)

emb = OpenAIEmbeddings()

# -----------------------------
# Example: load or build vectorstore
# -----------------------------
# For demo: assume an existing FAISS index saved at "faiss_index"
# If you don't have one, create/ingest docs and build FAISS first.
# vectorstore = FAISS.load_local("faiss_index", embeddings=emb)

# For demonstration only: create a tiny in-memory index from scratch.
docs = [
    Document(page_content="Paris is the capital of France. Population ~2.1M."),
    Document(page_content="The capital city of Germany is Berlin."),
    Document(page_content="Lenovo Legion 5 specs: battery life 6-8 hours typical usage."),
]
vectorstore = FAISS.from_documents(docs, emb)

retriever = vectorstore.as_retriever(search_type="similarity", search_kwargs={"k": 4})

# -----------------------------
# Prompt templates
# -----------------------------
REWRITE_PROMPT = PromptTemplate(
    input_variables=["query", "chat_history"],
    template=(
        "You are a query rewriter. Given the conversation history and the new user query, "
        "produce a concise, self-contained search query that maximizes retrieval relevance.\n\n"
        "Chat history:\n{chat_history}\n\nUser query:\n{query}\n\nRewritten standalone query:"
    )
)

DOC_RELEVANCE_PROMPT = PromptTemplate(
    input_variables=["query", "document_text"],
    template=(
        "You are a strict grader. Determine whether the document below is relevant to the query.\n\n"
        "Query:\n{query}\n\nDocument:\n{document_text}\n\n"
        "If the document can help answer the query, respond ONLY with: yes\n"
        "Otherwise respond ONLY with: no"
    )
)

ANSWER_GROUNDED_PROMPT = PromptTemplate(
    input_variables=["query", "answer", "documents_text"],
    template=(
        "You are a factuality checker. Given the query, the model's answer, and the retrieved documents, "
        "determine whether the answer is grounded in the documents and does not introduce unsupported facts.\n\n"
        "Query:\n{query}\n\nAnswer:\n{answer}\n\nRetrieved documents:\n{documents_text}\n\n"
        "If the answer is fully grounded and supported by the documents, respond ONLY with: yes\n"
        "If the answer includes hallucinated or unsupported facts, respond ONLY with: no"
    )
)

# -----------------------------
# Helper functions
# -----------------------------
def rewrite_query(query: str, chat_history: str) -> str:
    prompt = REWRITE_PROMPT.format(query=query, chat_history=chat_history)
    resp = rewrite_llm.generate([{"role": "user", "content": prompt}])
    # ChatOpenAI.generate returns Generation objects; extract content safely:
    return resp.generations[0][0].text.strip()

def grade_document_relevance(query: str, document_text: str) -> bool:
    prompt = DOC_RELEVANCE_PROMPT.format(query=query, document_text=document_text)
    resp = grading_llm.generate([{"role": "user", "content": prompt}])
    ans = resp.generations[0][0].text.strip().lower()
    return ans.startswith("yes")

def grade_answer_grounded(query: str, answer: str, docs: List[Document]) -> bool:
    docs_text = "\n\n".join(d.page_content for d in docs)
    prompt = ANSWER_GROUNDED_PROMPT.format(query=query, answer=answer, documents_text=docs_text)
    resp = grading_llm.generate([{"role": "user", "content": prompt}])
    ans = resp.generations[0][0].text.strip().lower()
    return ans.startswith("yes")

def generate_answer(query: str, docs: List[Document], chat_history: str) -> str:
    context_text = "\n\n".join([f"Document {i+1}:\n{d.page_content}" for i, d in enumerate(docs)])
    # Build a system+user style conversational call; include chat history for continuity
    system_msg = (
        "You are an assistant that answers user questions using only the provided documents. "
        "Cite evidence from documents when possible."
    )
    user_msg = (
        f"Chat history:\n{chat_history}\n\n"
        f"User question: {query}\n\n"
        f"Context / Documents:\n{context_text}\n\n"
        "Provide a concise, grounded answer and, if appropriate, cite which Document(s) support the facts."
    )
    # Use the generation LLM
    resp = generation_llm.generate([
        {"role": "system", "content": system_msg},
        {"role": "user", "content": user_msg}
    ])
    return resp.generations[0][0].text.strip()

# -----------------------------
# Agentic RAG main loop (single turn)
# -----------------------------
def agentic_rag_turn(user_query: str, memory: ConversationBufferMemory) -> Tuple[str, dict]:
    """
    Runs one agentic RAG cycle for the given user_query, using/ updating `memory`
    Returns (final_answer, diagnostics)
    """
    # Keep conversation history text for rewrites
    chat_history_text = memory.load_memory_variables({}).get("history", "")

    current_query = user_query
    diagnostics = {"retrieval_attempts": []}
    final_answer = None

    for attempt in range(1, MAX_ITER + 1):
        # 1) Retrieval
        retrieved_docs = retriever.get_relevant_documents(current_query)
        docs_texts = [d.page_content for d in retrieved_docs]

        # 2) Grade documents individually, filter out irrelevant ones
        relevant_docs = []
        for d in retrieved_docs:
            rel = grade_document_relevance(current_query, d.page_content)
            diagnostics["retrieval_attempts"].append({"attempt": attempt, "doc": d.page_content[:120], "relevant": rel})
            if rel:
                relevant_docs.append(d)

        avg_relevant = (len(relevant_docs) / max(1, len(retrieved_docs)))

        # If not enough relevant docs, try query rewrite and retry
        if avg_relevant < 0.5 and attempt < MAX_ITER:
            # rewrite the query (use chat_history + current query)
            rewritten = rewrite_query(current_query, chat_history_text)
            diagnostics.setdefault("rewrites", []).append({"attempt": attempt, "from": current_query, "to": rewritten})
            current_query = rewritten
            continue  # loop to next attempt

        # If no docs remain, try rewrite once (or break if last attempt)
        if not relevant_docs and attempt >= MAX_ITER:
            final_answer = "Sorry — I could not find relevant documents to answer that. Could you rephrase or provide more detail?"
            diagnostics["final_state"] = "no_relevant_docs"
            break

        # 3) Generate answer using relevant docs
        answer = generate_answer(current_query, relevant_docs, chat_history_text)

        # 4) Grade the answer (groundedness)
        grounded = grade_answer_grounded(current_query, answer, relevant_docs)
        diagnostics.setdefault("answer_checks", []).append({"attempt": attempt, "grounded": grounded, "answer_preview": answer[:150]})

        if grounded:
            final_answer = answer
            diagnostics["final_state"] = "grounded"
            break
        else:
            # Not grounded — try one more retrieval rewrite loop if attempts left
            diagnostics.setdefault("retry_reasons", []).append({"attempt": attempt, "reason": "answer_not_grounded"})
            if attempt < MAX_ITER:
                current_query = rewrite_query(current_query, chat_history_text)
                diagnostics.setdefault("rewrites", []).append({"attempt": attempt, "from": current_query, "to": current_query})
                continue
            else:
                final_answer = (
                    "I attempted to answer but couldn't produce a fully grounded response. "
                    "I can try again if you provide more detail or allow me to fetch external sources."
                )
                diagnostics["final_state"] = "ungrounded_after_retries"
                break

    # 5) Polishing step (simple rewrite/polish using generation model, optional)
    if final_answer and diagnostics.get("final_state") == "grounded":
        polish_prompt = (
            "Please rewrite the following assistant answer to be concise, professional, and easy to read. "
            "Keep facts unchanged:\n\n" + final_answer
        )
        polished_resp = generation_llm.generate([{"role": "user", "content": polish_prompt}])
        polished = polished_resp.generations[0][0].text.strip()
        final_answer = polished
        diagnostics["polished"] = True

    # 6) Update memory with the turn (preserve context)
    memory.save_context({"input": user_query}, {"output": final_answer})

    return final_answer, diagnostics

# -----------------------------
# Example usage with conversation context preserved
# -----------------------------
if __name__ == "__main__":
    memory = ConversationBufferMemory(memory_key="history", return_messages=False)

    print("Agentic RAG demo — enter 'exit' to quit\n")
    while True:
        q = input("User: ").strip()
        if not q or q.lower() in ("exit", "quit"):
            break
        answer, diag = agentic_rag_turn(q, memory)
        print("\nAssistant:", answer)
        # small diagnostic print (optional)
        print("\n[diagnostics]:", diag)
        print("\n---\n")
        time.sleep(0.1)
