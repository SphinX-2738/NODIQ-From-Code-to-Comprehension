import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path
from app.parsing.models import OKFRecord, EntityType
from app.embeddings.pipeline import _build_text_chunk, query_collection


def make_record(id, entity_type, name, file_path, **kwargs):
    return OKFRecord(
        id=id,
        entity_type=entity_type,
        name=name,
        file_path=file_path,
        start_line=1,
        end_line=10,
        **kwargs,
    )


RECORDS = [
    make_record(
        "myapp.auth.login",
        EntityType.FUNCTION,
        "login",
        "myapp/auth.py",
        docstring="Authenticate a user and return a session token.",
        signature="(username: str, password: str) -> str",
        outgoing_refs=["myapp.auth.validate_password"],
        incoming_refs=["myapp.api.handle_login"],
    ),
    make_record(
        "myapp.auth.validate_password",
        EntityType.FUNCTION,
        "validate_password",
        "myapp/auth.py",
        docstring="Check if a password matches the stored hash.",
    ),
]


def test_text_chunk_includes_name():
    """The text chunk should always include the entity name."""
    from app.graph.builder import build_graph
    graph = build_graph(RECORDS)
    chunk = _build_text_chunk(RECORDS[0], graph)
    assert "login" in chunk


def test_text_chunk_includes_docstring():
    """Docstrings are the most semantically rich part — must be included."""
    from app.graph.builder import build_graph
    graph = build_graph(RECORDS)
    chunk = _build_text_chunk(RECORDS[0], graph)
    assert "Authenticate a user" in chunk


def test_text_chunk_includes_graph_context():
    """Outgoing refs should appear in the chunk for graph enrichment."""
    from app.graph.builder import build_graph
    graph = build_graph(RECORDS)
    chunk = _build_text_chunk(RECORDS[0], graph)
    assert "myapp.auth.validate_password" in chunk


def test_text_chunk_no_signature_for_file():
    """FILE records have no signature — chunk should not include it."""
    from app.graph.builder import build_graph
    file_record = make_record(
        "myapp.auth",
        EntityType.FILE,
        "auth.py",
        "myapp/auth.py",
    )
    graph = build_graph([file_record])
    chunk = _build_text_chunk(file_record, graph)
    assert "signature" not in chunk