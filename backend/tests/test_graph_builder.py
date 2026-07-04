import json
from pathlib import Path
from app.parsing.models import OKFRecord, EntityType
from app.graph.builder import (
    build_graph,
    populate_incoming_refs,
    save_graph,
    load_graph,
    get_graph_stats,
)


def make_record(id, entity_type, name, file_path, outgoing_refs=None):
    """Helper to create OKFRecords quickly in tests."""
    return OKFRecord(
        id=id,
        entity_type=entity_type,
        name=name,
        file_path=file_path,
        start_line=1,
        end_line=10,
        outgoing_refs=outgoing_refs or [],
    )


RECORDS = [
    make_record("myapp.auth", EntityType.FILE, "auth.py", "myapp/auth.py"),
    make_record("myapp.auth.UserAuth", EntityType.CLASS, "UserAuth", "myapp/auth.py"),
    make_record(
        "myapp.auth.UserAuth.login",
        EntityType.METHOD,
        "login",
        "myapp/auth.py",
        outgoing_refs=["myapp.auth.validate_password"],
    ),
    make_record("myapp.auth.validate_password", EntityType.FUNCTION, "validate_password", "myapp/auth.py"),
]


def test_graph_has_correct_node_count():
    """Graph should have one node per OKF record."""
    graph = build_graph(RECORDS)
    assert graph.number_of_nodes() == 4


def test_graph_has_call_edge():
    """login() calls validate_password() — that edge must exist."""
    graph = build_graph(RECORDS)
    assert graph.has_edge(
        "myapp.auth.UserAuth.login",
        "myapp.auth.validate_password"
    )


def test_node_stores_attributes():
    """Each node should store the name and entity_type from its OKF record."""
    graph = build_graph(RECORDS)
    node = graph.nodes["myapp.auth.UserAuth.login"]
    assert node["name"] == "login"
    assert node["entity_type"] == "method"


def test_incoming_refs_populated():
    """After populate_incoming_refs, validate_password should know login calls it."""
    graph = build_graph(RECORDS)
    updated = populate_incoming_refs(RECORDS, graph)
    validate_pw = next(r for r in updated if r.name == "validate_password")
    assert "myapp.auth.UserAuth.login" in validate_pw.incoming_refs


def test_save_and_load_graph(tmp_path):
    """Saving and reloading a graph should produce an identical graph."""
    graph = build_graph(RECORDS)
    path = tmp_path / "graph.json"
    save_graph(graph, path)

    loaded = load_graph(path)
    assert loaded.number_of_nodes() == graph.number_of_nodes()
    assert loaded.number_of_edges() == graph.number_of_edges()
    assert loaded.has_edge(
        "myapp.auth.UserAuth.login",
        "myapp.auth.validate_password"
    )


def test_graph_stats():
    """Stats should correctly count nodes and entity types."""
    graph = build_graph(RECORDS)
    stats = get_graph_stats(graph)
    assert stats["total_nodes"] == 4
    assert stats["total_edges"] == 1
    assert stats["entity_counts"]["method"] == 1
    assert stats["entity_counts"]["function"] == 1