import zipfile
import io
from pathlib import Path
import pytest
from app.ingestion.importer import collect_python_files, ingest_from_zip, IngestionError


def make_zip(files: dict[str, str]) -> bytes:
    """
    Helper: create an in-memory ZIP containing the given files.
    files is a dict of {filename: content}.
    Mimics GitHub's ZIP structure by adding a top-level folder.
    """
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name, content in files.items():
            zf.writestr(f"myrepo-main/{name}", content)
    return buf.getvalue()


def test_ingest_from_zip_extracts_python_files(tmp_path):
    """Should extract .py files from a ZIP into the destination folder."""
    zip_bytes = make_zip({
        "main.py": "print('hello')",
        "utils.py": "def helper(): pass",
        "README.md": "# Not Python",
    })
    zip_file = tmp_path / "repo.zip"
    zip_file.write_bytes(zip_bytes)

    dest = tmp_path / "output"
    ingest_from_zip(zip_file, dest)

    extracted = list(dest.rglob("*.py"))
    names = [f.name for f in extracted]
    assert "main.py" in names
    assert "utils.py" in names
    assert "README.md" not in str(extracted)


def test_ingest_from_zip_skips_non_python(tmp_path):
    """Non-.py files should never appear in the output folder."""
    zip_bytes = make_zip({
        "app.py": "x = 1",
        "config.json": '{"key": "value"}',
        "styles.css": "body { color: red; }",
    })
    zip_file = tmp_path / "repo.zip"
    zip_file.write_bytes(zip_bytes)

    dest = tmp_path / "output"
    ingest_from_zip(zip_file, dest)

    all_files = list(dest.rglob("*.*"))
    for f in all_files:
        assert f.suffix == ".py", f"Non-Python file found: {f}"


def test_ingest_from_zip_missing_file_raises(tmp_path):
    """Should raise IngestionError if the ZIP file doesn't exist."""
    with pytest.raises(IngestionError):
        ingest_from_zip(tmp_path / "nonexistent.zip", tmp_path / "out")


def test_collect_python_files_finds_all(tmp_path):
    """Should recursively find all .py files in a directory."""
    (tmp_path / "a.py").write_text("x = 1")
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "b.py").write_text("y = 2")

    files = collect_python_files(tmp_path)
    names = [f.name for f in files]
    assert "a.py" in names
    assert "b.py" in names


def test_collect_python_files_skips_pycache(tmp_path):
    """Should not include files inside __pycache__ folders."""
    cache = tmp_path / "__pycache__"
    cache.mkdir()
    (cache / "cached.py").write_text("# cached")
    (tmp_path / "real.py").write_text("# real")

    files = collect_python_files(tmp_path)
    names = [f.name for f in files]
    assert "real.py" in names
    assert "cached.py" not in names