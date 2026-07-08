# Nodiq — Technical Documentation

## Overview

Nodiq is an AI-powered Software Intelligence Platform that transforms Python 
repositories into structured knowledge systems. It enables developers to 
understand, navigate, document, and reason about complex codebases through 
a knowledge graph and grounded, cited AI chat.

## Architecture

The system is built as a modular pipeline with explicit data contracts 
between each stage:
GitHub repo / ZIP
↓
Repository Ingester
↓
Tree-sitter AST Parser → Python-only (MVP)
↓
OKF Extraction (Open Knowledge Format)
↓
Knowledge Graph Construction (NetworkX)
↓
Graph-Enriched Embedding Pipeline (ChromaDB + Gemini)
↓
LangGraph Reasoning Layer
↓
FastAPI REST API
↓
Next.js Frontend (in progress)

## Key Concepts

### Open Knowledge Format (OKF)
A normalized, language-agnostic intermediate representation of a single 
code entity (file, class, function, or method). Every downstream stage 
consumes OKF records — never raw AST output. This is the data contract 
that keeps the pipeline modular and independently testable.

### Knowledge Graph
Every OKF record becomes a node. Every relationship (calls, imports, 
inherits-from) becomes a directed edge. Built with NetworkX and persisted 
to disk as JSON.

### Graph-Enriched Embeddings
Before embedding, each OKF record is enriched with its graph context — 
what it calls and what calls it. This means the embedding captures not 
just what a function is, but where it sits in the codebase.

### LangGraph Reasoning
A multi-step reasoning graph that:
1. Retrieves relevant OKF records from ChromaDB
2. Checks retrieval confidence
3. Rephrases and retries if confidence is low
4. Synthesizes a grounded, cited answer

## Project Structure
nodiq/
backend/
app/
ingestion/      # GitHub/ZIP importer
parsing/        # Tree-sitter + OKF extraction (per language)
python/       # Python-specific AST mapper
graph/          # NetworkX knowledge graph
embeddings/     # Embedding pipeline + ChromaDB
retrieval/      # Hybrid retrieval (vector + graph)
reasoning/      # LangGraph agents
api/            # FastAPI routes
evaluation/     # Evaluation harness
tests/
frontend/           # Next.js (Milestone 7+)
docs/               # Project documentation
docker/             # Containerization

## Technology Decisions

| Component | Technology | Why |
|---|---|---|
| AST parsing | Tree-sitter | Language-agnostic, production-grade, used by VS Code and GitHub |
| Graph | NetworkX | Lightweight, Pythonic, no infrastructure needed |
| Vector store | ChromaDB | Free, local, purpose-built for embeddings |
| Embeddings | Gemini text-embedding-004 | Free tier, production quality |
| Reasoning | LangGraph | Native support for conditional, multi-step AI workflows |
| API | FastAPI | Modern, fast, automatic validation via Pydantic |
| Frontend | Next.js + React Flow | Industry standard + purpose-built graph visualization |
| Deployment | Render | Free tier compatible |

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/v1/ingest/github` | Ingest a public GitHub repository |
| POST | `/api/v1/chat` | Ask a question about an ingested repo |
| GET | `/api/v1/graph/{repo_id}` | Get the knowledge graph for visualization |
| GET | `/api/v1/health` | Health check |

## Evaluation

The system includes a lightweight evaluation harness that measures:
- **Precision** — of results returned, how many were correct?
- **Recall** — of correct answers that exist, how many were found?
- **Hit Rate** — percentage of questions where at least one correct answer was found

This allows retrieval quality to be tracked as the pipeline evolves.

## Milestones

| # | Milestone | Status |
|---|---|---|
| 0 | Project setup & architecture | ✅ Complete |
| 1 | Repository ingestion + OKF schema + AST extraction | ✅ Complete |
| 2 | Knowledge graph construction | ✅ Complete |
| 3 | Embedding pipeline + ChromaDB | ✅ Complete |
| 4 | Evaluation harness | ✅ Complete |
| 5 | LangGraph reasoning layer | ✅ Complete |
| 6 | FastAPI backend integration | ✅ Complete |
| 7 | Next.js frontend — chat + docs view | 🔄 In progress |
| 8 | Next.js frontend — graph explorer | ⏳ Pending |
| 9 | Documentation generation | ⏳ Pending |
| 10 | Deployment to Render | ⏳ Pending |
