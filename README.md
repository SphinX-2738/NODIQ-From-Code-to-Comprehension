\# Nodiq — From Code to Comprehension



An AI-powered Software Intelligence Platform that transforms Python repositories 

into structured knowledge systems.



Unlike RAG chatbots that chunk files into embeddings, Nodiq extracts a structured 

representation of a codebase — files, classes, functions, call graph, imports — 

and reasons over that structure to give grounded, cited answers.



\## What it does



\- Ingests any public Python repository from GitHub

\- Builds a knowledge graph of every function, class, and file

\- Enables semantic search over code using graph-enriched embeddings

\- Answers questions about the codebase with cited evidence



\## Tech Stack



\*\*Backend:\*\* FastAPI, LangGraph, Tree-sitter, NetworkX, ChromaDB, Gemini  

\*\*Frontend:\*\* Next.js, React Flow, TypeScript, Tailwind CSS (coming soon)  

\*\*Deployment:\*\* Render (free tier)



\## Status



Active development — Milestone 6 of 10 complete.  

See \[docs/NODIQ\_PROJECT\_GUIDE.md](docs/NODIQ\_PROJECT\_GUIDE.md) for the full 

governing specification and milestone roadmap.



\## Running locally



```bash

cd backend

uv sync

uv run pytest        # run all tests

uv run ruff check .  # lint

```

