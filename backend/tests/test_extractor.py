from app.parsing.python.extractor import extract_okf_records
from app.parsing.models import EntityType


# This is the sample Python code we'll extract from.
# Think of this as a mini Python file we made up just for testing.
SAMPLE_CODE = '''
def greet(name: str) -> str:
    """Say hello to someone."""
    return "Hello " + name


def add(a: int, b: int) -> int:
    return a + b


class Calculator:
    """A simple calculator class."""

    def multiply(self, x: int, y: int) -> int:
        """Multiply two numbers."""
        return x * y

    def divide(self, x: float, y: float) -> float:
        return x / y
'''


def test_extracts_file_record():
    """Should always produce one FILE record for the file itself."""
    records = extract_okf_records(SAMPLE_CODE, "myapp/calc.py")
    file_records = [r for r in records if r.entity_type == EntityType.FILE]
    assert len(file_records) == 1
    assert file_records[0].name == "calc.py"


def test_extracts_functions():
    """Should find both top-level functions: greet and add."""
    records = extract_okf_records(SAMPLE_CODE, "myapp/calc.py")
    function_names = [r.name for r in records if r.entity_type == EntityType.FUNCTION]
    assert "greet" in function_names
    assert "add" in function_names


def test_extracts_class():
    """Should find the Calculator class."""
    records = extract_okf_records(SAMPLE_CODE, "myapp/calc.py")
    class_records = [r for r in records if r.entity_type == EntityType.CLASS]
    assert len(class_records) == 1
    assert class_records[0].name == "Calculator"


def test_extracts_methods():
    """Should find multiply and divide as methods inside Calculator."""
    records = extract_okf_records(SAMPLE_CODE, "myapp/calc.py")
    method_names = [r.name for r in records if r.entity_type == EntityType.METHOD]
    assert "multiply" in method_names
    assert "divide" in method_names


def test_docstring_extracted():
    """greet() has a docstring — it should be captured on the card."""
    records = extract_okf_records(SAMPLE_CODE, "myapp/calc.py")
    greet = next(r for r in records if r.name == "greet")
    assert greet.docstring == "Say hello to someone."


def test_no_docstring_is_none():
    """add() has no docstring — the field should be None, not empty string."""
    records = extract_okf_records(SAMPLE_CODE, "myapp/calc.py")
    add = next(r for r in records if r.name == "add")
    assert add.docstring is None


def test_signature_extracted():
    """greet() has a signature — it should be captured correctly."""
    records = extract_okf_records(SAMPLE_CODE, "myapp/calc.py")
    greet = next(r for r in records if r.name == "greet")
    assert "name" in greet.signature
    assert "str" in greet.signature


def test_unique_ids():
    """Every record must have a unique ID — no duplicates allowed."""
    records = extract_okf_records(SAMPLE_CODE, "myapp/calc.py")
    ids = [r.id for r in records]
    assert len(ids) == len(set(ids))