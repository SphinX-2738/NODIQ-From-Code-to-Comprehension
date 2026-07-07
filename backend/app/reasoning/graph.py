import os
from typing import TypedDict, Annotated
from dotenv import load_dotenv

import chromadb
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import StateGraph, START, END

from app.embeddings.pipeline import query_collection, COLLECTION_NAME

load_dotenv()

# Initialize the Gemini model for answer synthesis
llm = ChatGoogleGenerativeAI(
    model="gemini-2.0-flash",
    google_api_key=os.environ["GEMINI_API_KEY"],
    temperature=0.2,  # low temperature = more focused, less creative answers
)

# Confidence threshold — below this score we consider retrieval uncertain
CONFIDENCE_THRESHOLD = 0.5


class ReasoningState(TypedDict):
    """
    The shared state that flows through every node in the graph.
    Every node reads from this and writes back to it.
    Think of it as the shared notebook for the whole reasoning process.
    """
    question: str                    # the original user question
    retrieved_context: list[dict]    # OKF records retrieved from ChromaDB
    confidence: float                # how confident we are in the retrieval
    answer: str                      # the final synthesized answer
    cited_ids: list[str]             # OKF IDs cited in the answer
    needs_clarification: bool        # whether we need to retry with a better query
    retry_count: int                 # how many times we've retried retrieval


def retrieve_context(state: ReasoningState, collection: chromadb.Collection) -> ReasoningState:
    """
    Node 1: Search ChromaDB for OKF records relevant to the question.
    Calculates a confidence score based on the top result's similarity.
    """
    results = query_collection(collection, state["question"], n_results=5)

    confidence = results[0]["score"] if results else 0.0

    return {
        **state,
        "retrieved_context": results,
        "confidence": confidence,
    }


def check_confidence(state: ReasoningState) -> str:
    """
    Conditional edge: decides where to go next based on confidence score.
    This is where LangGraph earns its place — a plain pipeline can't branch.

    Returns the name of the next node to execute.
    """
    if state["confidence"] >= CONFIDENCE_THRESHOLD:
        return "synthesize_answer"
    if state["retry_count"] >= 1:
        # We've already retried once — synthesize with what we have
        return "synthesize_answer"
    return "clarify_query"


def clarify_query(state: ReasoningState) -> ReasoningState:
    """
    Node 2 (optional): If retrieval wasn't confident enough, use the LLM
    to rephrase the question before retrying.

    This is the disambiguation step — asking "what might this question
    really be about?" before searching again.
    """
    prompt = f"""A user asked: "{state['question']}"

A search over a Python codebase returned low-confidence results.
Rephrase this question to be more specific and technical,
focusing on Python code concepts like functions, classes, or methods.
Return only the rephrased question, nothing else."""

    response = llm.invoke(prompt)
    rephrased = response.content.strip()

    return {
        **state,
        "question": rephrased,
        "retry_count": state["retry_count"] + 1,
        "needs_clarification": True,
    }


def synthesize_answer(state: ReasoningState) -> ReasoningState:
    """
    Node 3: Use the LLM to synthesize a grounded answer from retrieved context.
    The answer must cite specific OKF IDs — no hallucinating code that wasn't retrieved.
    """
    if not state["retrieved_context"]:
        return {
            **state,
            "answer": "I could not find relevant code to answer this question.",
            "cited_ids": [],
        }

    # Build context string from retrieved OKF records
    context_parts = []
    for r in state["retrieved_context"]:
        context_parts.append(
            f"[{r['id']}]\n{r['document']}\n(similarity: {r['score']:.2f})"
        )
    context_str = "\n\n---\n\n".join(context_parts)

    prompt = f"""You are an expert software engineer analyzing a Python codebase.

A developer asked: "{state['question']}"

Here are the most relevant code entities found:

{context_str}

Instructions:
- Answer the question clearly and technically
- Reference specific entity IDs using [id] notation
- Only cite entities that are actually relevant to the answer
- If the context doesn't fully answer the question, say so honestly
- Keep the answer concise but complete"""

    response = llm.invoke(prompt)
    answer = response.content.strip()

    # Extract cited IDs from the answer
    cited_ids = [
        r["id"] for r in state["retrieved_context"]
        if r["id"] in answer
    ]

    return {
        **state,
        "answer": answer,
        "cited_ids": cited_ids,
    }


def build_reasoning_graph(collection: chromadb.Collection) -> StateGraph:
    """
    Assemble the LangGraph reasoning graph.

    Nodes: retrieve_context → check_confidence → synthesize_answer
                                               ↘ clarify_query → retrieve_context (retry)

    This is the function that connects all the pieces together.
    """
    graph = StateGraph(ReasoningState)

    # Add nodes — each one is a function that takes state and returns updated state
    graph.add_node(
        "retrieve_context",
        lambda state: retrieve_context(state, collection)
    )
    graph.add_node("clarify_query", clarify_query)
    graph.add_node("synthesize_answer", synthesize_answer)

    # Fixed edges
    graph.add_edge(START, "retrieve_context")
    graph.add_edge("clarify_query", "retrieve_context")
    graph.add_edge("synthesize_answer", END)

    # Conditional edge — this is where LangGraph's branching happens
    graph.add_conditional_edges(
        "retrieve_context",
        check_confidence,
        {
            "synthesize_answer": "synthesize_answer",
            "clarify_query": "clarify_query",
        }
    )

    return graph.compile()


def ask(compiled_graph, question: str) -> dict:
    """
    Ask a question and get a grounded answer back.
    This is the single entry point the rest of the system uses.
    """
    initial_state: ReasoningState = {
        "question": question,
        "retrieved_context": [],
        "confidence": 0.0,
        "answer": "",
        "cited_ids": [],
        "needs_clarification": False,
        "retry_count": 0,
    }

    final_state = compiled_graph.invoke(initial_state)

    return {
        "question": final_state["question"],
        "answer": final_state["answer"],
        "cited_ids": final_state["cited_ids"],
        "confidence": final_state["confidence"],
        "needed_clarification": final_state["needs_clarification"],
    }