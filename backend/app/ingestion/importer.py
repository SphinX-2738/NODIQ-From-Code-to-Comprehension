import io
import os
import shutil
import tempfile
import zipfile
from pathlib import Path

import requests


class IngestionError(Exception):
    """Raised when a repository cannot be imported."""
    pass


def _extract_zip(zip_bytes: bytes, destination: Path) -> None:
    """
    Extract a ZIP archive (as raw bytes) into a destination folder.
    Skips any files that are not .py files — we only care about Python source.
    """
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        for member in zf.infolist():
            # Skip directories and non-Python files
            if member.filename.endswith("/"):
                continue
            if not member.filename.endswith(".py"):
                continue

            # Flatten the top-level folder GitHub adds (e.g. "myrepo-main/")
            parts = Path(member.filename).parts
            if len(parts) < 2:
                continue
            relative_path = Path(*parts[1:])  # strip the top-level folder

            target = destination / relative_path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(zf.read(member.filename))


def ingest_from_github(github_url: str, destination: Path) -> Path:
    """
    Download a public GitHub repository and extract its Python files.

    Accepts URLs in these formats:
      - https://github.com/owner/repo
      - https://github.com/owner/repo/tree/main

    Returns the destination path containing the extracted .py files.
    Raises IngestionError if the download fails.
    """
    # Normalize the URL to get the ZIP download link
    # GitHub serves any repo as a ZIP at: /owner/repo/archive/refs/heads/main.zip
    parts = github_url.rstrip("/").split("/")
    try:
        owner = parts[3]
        repo = parts[4]
    except IndexError:
        raise IngestionError(
            f"Could not parse GitHub URL: {github_url}. "
            "Expected format: https://github.com/owner/repo"
        )

    zip_url = f"https://github.com/{owner}/{repo}/archive/refs/heads/main.zip"

    try:
        response = requests.get(zip_url, timeout=30)
        response.raise_for_status()
    except requests.exceptions.HTTPError:
        # Try 'master' branch if 'main' doesn't exist
        zip_url = f"https://github.com/{owner}/{repo}/archive/refs/heads/master.zip"
        try:
            response = requests.get(zip_url, timeout=30)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            raise IngestionError(f"Failed to download repository: {e}")
    except requests.exceptions.RequestException as e:
        raise IngestionError(f"Failed to download repository: {e}")

    destination.mkdir(parents=True, exist_ok=True)
    _extract_zip(response.content, destination)
    return destination


def ingest_from_zip(zip_path: Path, destination: Path) -> Path:
    """
    Extract Python files from a local ZIP file.

    Returns the destination path containing the extracted .py files.
    Raises IngestionError if the ZIP cannot be read.
    """
    if not zip_path.exists():
        raise IngestionError(f"ZIP file not found: {zip_path}")
    if not zipfile.is_zipfile(zip_path):
        raise IngestionError(f"Not a valid ZIP file: {zip_path}")

    try:
        zip_bytes = zip_path.read_bytes()
    except OSError as e:
        raise IngestionError(f"Could not read ZIP file: {e}")

    destination.mkdir(parents=True, exist_ok=True)
    _extract_zip(zip_bytes, destination)
    return destination


def collect_python_files(directory: Path) -> list[Path]:
    """
    Walk a directory and return all .py files found, sorted by path.
    Skips common non-source folders like tests, migrations, and __pycache__.
    """
    SKIP_DIRS = {"__pycache__", ".git", ".venv", "venv", "migrations", ".tox"}

    python_files = []
    for root, dirs, files in os.walk(directory):
        # Modify dirs in-place to skip unwanted folders
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for file in files:
            if file.endswith(".py"):
                python_files.append(Path(root) / file)

    return sorted(python_files)