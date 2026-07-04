import json
from pathlib import Path
import networkx as nx
from app.parsing.models import OKFRecord, EntityType


def build_graph(records: list[OKFRecord]) -> nx.DiGraph:
    """
    Build a directed knowledge graph from a list of OKF records.

    Each record becomes a node.
    Each outgoing_ref becomes a directed edge: this record → referenced record.

    We use a DiGraph (directed graph) because relationships have direction:
    "A calls B" is not the same as "B calls A".
    """
    graph = nx.DiGraph()

    # Step 1 — Add every record as a node
    for record in records:
        graph.add_node(
            record.id,
            name=record.name,
            entity_type=record.entity_type.value,
            file_path=record.file_path,
            start_line=record.start_line,
            end_line=record.end_line,
            docstring=record.docstring or "",
            signature=record.signature or "",
        )

    # Step 2 — Add edges for every outgoing reference
    for record in records:
        for ref_id in record.outgoing_refs:
            if graph.has_node(ref_id):
                graph.add_edge(record.id, ref_id, relationship="calls")

    return graph


def populate_incoming_refs(records: list[OKFRecord], graph: nx.DiGraph) -> list[OKFRecord]:
    """
    Fill in the incoming_refs field on each OKFRecord using the graph.

    During extraction (Milestone 1), we only knew what each function calls
    (outgoing). Now that the full graph exists, we can look backwards and
    find everything that calls each function (incoming).

    This is why incoming_refs was left empty during parsing — you can only
    know who calls you once you've seen the whole codebase.
    """
    updated = []
    for record in records:
        predecessors = list(graph.predecessors(record.id))
        updated.append(record.model_copy(update={"incoming_refs": predecessors}))
    return updated


def save_graph(graph: nx.DiGraph, path: Path) -> None:
    """
    Persist the graph to disk as a JSON file.
    We use node-link format — a standard, readable JSON representation
    of a graph that NetworkX can reload perfectly.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    data = nx.node_link_data(graph, edges="edges")
    path.write_text(json.dumps(data, indent=2))


def load_graph(path: Path) -> nx.DiGraph:
    """
    Load a previously saved graph from disk.
    Raises FileNotFoundError if the file doesn't exist.
    """
    if not path.exists():
        raise FileNotFoundError(f"No graph file found at: {path}")
    data = json.loads(path.read_text())
    return nx.node_link_graph(data, directed=True, edges="edges")


def get_graph_stats(graph: nx.DiGraph) -> dict:
    """
    Return a simple summary of the graph.
    Useful for debugging and for showing users how big their repo is.
    """
    entity_counts = {}
    for _, attrs in graph.nodes(data=True):
        etype = attrs.get("entity_type", "unknown")
        entity_counts[etype] = entity_counts.get(etype, 0) + 1

    return {
        "total_nodes": graph.number_of_nodes(),
        "total_edges": graph.number_of_edges(),
        "entity_counts": entity_counts,
    }