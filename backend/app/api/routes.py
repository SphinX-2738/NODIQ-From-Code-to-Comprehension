import tempfile
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.ingestion.importer import (
    ingest_from_github,
    ingest_from_zip,
    collect_python_files,
    IngestionError,
)
from app.parsing.python.extractor import extract_okf_records
from app.graph.builder import build_graph, save_graph, load_graph, get_graph_stats, populate_incoming_refs
from app.embeddings.pipeline import build_embedding_pipeline, query_collection, COLLECTION_NAME
from app.reasoning.graph import build_reasoning_graph, ask
import chromadb

router = APIRouter()

# In-memory store for active repos — replaced with a database in post-MVP
_repo_store: dict[str, dict] = {}


# --- Request / Response models ---

class IngestGithubRequest(BaseModel):
    github_url: str
    repo_id: str  # a name you give this repo e.g. "my-fastapi-app"


class IngestResponse(BaseModel):
    repo_id: str
    total_files: int
    total_records: int
    graph_stats: dict


class ChatRequest(BaseModel):
    repo_id: str
    question: str


class ChatResponse(BaseModel):
    question: str
    answer: str
    cited_ids: list[str]
    confidence: float
    needed_clarification: bool


class GraphResponse(BaseModel):
    repo_id: str
    nodes: list[dict]
    edges: list[dict]


# --- Endpoints ---

@router.post("/ingest/github", response_model=IngestResponse)
async def ingest_github(request: IngestGithubRequest):
    """
    Download a public GitHub repo, extract Python files,
    build OKF records, knowledge graph, and embeddings.
    """
    try:
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo_path = Path(tmp_dir) / "repo"
            chroma_path = Path(f"data/{request.repo_id}/chroma")
            graph_path = Path(f"data/{request.repo_id}/graph.json")

            # Step 1 — Ingest
            ingest_from_github(request.github_url, repo_path)
            python_files = collect_python_files(repo_path)

            if not python_files:
                raise HTTPException(
                    status_code=400,
                    detail="No Python files found in this repository."
                )

            # Step 2 — Extract OKF records
            all_records = []
            for file_path in python_files:
                relative_path = str(file_path.relative_to(repo_path))
                source_code = file_path.read_text(encoding="utf-8", errors="ignore")
                records = extract_okf_records(source_code, relative_path)
                all_records.extend(records)

            # Step 3 — Build graph and populate incoming refs
            graph = build_graph(all_records)
            all_records = populate_incoming_refs(all_records, graph)
            save_graph(graph, graph_path)

            # Step 4 — Build embeddings
            chroma_path.mkdir(parents=True, exist_ok=True)
            build_embedding_pipeline(all_records, chroma_path)

            # Step 5 — Store repo metadata
            stats = get_graph_stats(graph)
            _repo_store[request.repo_id] = {
                "chroma_path": str(chroma_path),
                "graph_path": str(graph_path),
            }

            return IngestResponse(
                repo_id=request.repo_id,
                total_files=len(python_files),
                total_records=len(all_records),
                graph_stats=stats,
            )

    except IngestionError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Ask a question about an ingested repository.
    Returns a grounded, cited answer.
    """
    if request.repo_id not in _repo_store:
        raise HTTPException(
            status_code=404,
            detail=f"Repository '{request.repo_id}' not found. Ingest it first."
        )

    repo_data = _repo_store[request.repo_id]
    chroma_path = Path(repo_data["chroma_path"])

    chroma_client = chromadb.PersistentClient(path=str(chroma_path))
    collection = chroma_client.get_collection(COLLECTION_NAME)

    compiled_graph = build_reasoning_graph(collection)
    result = ask(compiled_graph, request.question)

    return ChatResponse(**result)


@router.get("/graph/{repo_id}", response_model=GraphResponse)
async def get_graph(repo_id: str):
    """
    Return the knowledge graph for a repository.
    Used by the frontend React Flow visualization.
    """
    if repo_id not in _repo_store:
        raise HTTPException(
            status_code=404,
            detail=f"Repository '{repo_id}' not found. Ingest it first."
        )

    graph_path = Path(_repo_store[repo_id]["graph_path"])
    graph = load_graph(graph_path)

    nodes = [
        {"id": node_id, **attrs}
        for node_id, attrs in graph.nodes(data=True)
    ]
    edges = [
        {"source": src, "target": tgt, **attrs}
        for src, tgt, attrs in graph.edges(data=True)
    ]

    return GraphResponse(repo_id=repo_id, nodes=nodes, edges=edges)


@router.get("/health")
async def health():
    """Simple health check endpoint."""
    return {"status": "ok"}