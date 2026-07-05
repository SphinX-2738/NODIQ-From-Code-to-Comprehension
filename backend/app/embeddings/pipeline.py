import os
from pathlib import Path

import chromadb
from google import genai
from google.genai import types
from dotenv import load_dotenv

from app.graph.builder import build_graph, get_graph_stats
from app.parsing.models import OKFRecord

# Load the GEMINI_API_KEY from .env file
load_dotenv()
client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

# The ChromaDB collection name
COLLECTION_NAME = "nodiq_embeddings"


def _build_text_chunk(record: OKFRecord, graph) -> str:
    """
    Build a rich text description of an OKF record, enriched with
    graph context (who calls it, what it calls).
    """
    lines = []

    lines.append(f"{record.entity_type.value}: {record.name}")
    lines.append(f"file: {record.file_path}")
    lines.append(f"lines: {record.start_line}-{record.end_line}")

    if record.signature:
        lines.append(f"signature: {record.signature}")

    if record.docstring:
        lines.append(f"description: {record.docstring}")

    if record.outgoing_refs:
        lines.append(f"calls: {', '.join(record.outgoing_refs)}")

    if record.incoming_refs:
        lines.append(f"called by: {', '.join(record.incoming_refs)}")

    return "\n".join(lines)


def _embed_texts(texts: list[str]) -> list[list[float]]:
    """
    Convert a list of text strings into vectors using Gemini's
    embedding model via the new google-genai SDK.
    """
    result = client.models.embed_content(
        model="text-embedding-004",
        contents=texts,
        config=types.EmbedContentConfig(task_type="RETRIEVAL_DOCUMENT"),
    )
    return [e.values for e in result.embeddings]


def build_embedding_pipeline(
    records: list[OKFRecord],
    chroma_path: Path,
) -> chromadb.Collection:
    """
    Main function: takes OKF records, builds the graph, enriches each
    record with graph context, embeds them, and stores in ChromaDB.
    """
    graph = build_graph(records)
    stats = get_graph_stats(graph)
    print(f"Graph built: {stats}")

    chroma_client = chromadb.PersistentClient(path=str(chroma_path))

    try:
        chroma_client.delete_collection(COLLECTION_NAME)
    except Exception:
        pass

    collection = chroma_client.create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )

    BATCH_SIZE = 50
    all_ids = []
    all_texts = []
    all_metadatas = []

    for record in records:
        chunk = _build_text_chunk(record, graph)
        all_ids.append(record.id)
        all_texts.append(chunk)
        all_metadatas.append({
            "name": record.name,
            "entity_type": record.entity_type.value,
            "file_path": record.file_path,
            "start_line": record.start_line,
            "end_line": record.end_line,
        })

    for i in range(0, len(all_texts), BATCH_SIZE):
        batch_texts = all_texts[i:i + BATCH_SIZE]
        batch_ids = all_ids[i:i + BATCH_SIZE]
        batch_metadatas = all_metadatas[i:i + BATCH_SIZE]

        print(f"Embedding batch {i // BATCH_SIZE + 1} ({len(batch_texts)} items)...")
        embeddings = _embed_texts(batch_texts)

        collection.add(
            ids=batch_ids,
            embeddings=embeddings,
            documents=batch_texts,
            metadatas=batch_metadatas,
        )

    print(f"Embedding complete. {len(all_texts)} records stored in ChromaDB.")
    return collection


def query_collection(
    collection: chromadb.Collection,
    question: str,
    n_results: int = 5,
) -> list[dict]:
    """
    Search ChromaDB for records most relevant to a question.
    """
    result = client.models.embed_content(
        model="text-embedding-004",
        contents=question,
        config=types.EmbedContentConfig(task_type="RETRIEVAL_QUERY"),
    )
    query_embedding = result.embeddings[0].values

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=n_results,
        include=["documents", "metadatas", "distances"],
    )

    matches = []
    for i in range(len(results["ids"][0])):
        matches.append({
            "id": results["ids"][0][i],
            "document": results["documents"][0][i],
            "metadata": results["metadatas"][0][i],
            "score": 1 - results["distances"][0][i],
        })

    return matches