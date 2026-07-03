import tree_sitter_python as tspython
from tree_sitter import Language, Parser

from app.parsing.models import EntityType, OKFRecord

# Build the Python language parser once — this is the engine + grammar combined
PY_LANGUAGE = Language(tspython.language())
parser = Parser(PY_LANGUAGE)


def _get_docstring(node, source: bytes) -> str | None:
    """
    Extract the docstring from a function or class body, if one exists.
    A docstring is just the first statement in the body, if it's a plain string.
    """
    body = next((c for c in node.children if c.type == "block"), None)
    if not body:
        return None

    first_statement = next((c for c in body.children if c.is_named), None)
    if first_statement and first_statement.type == "expression_statement":
        expr = first_statement.children[0]
        if expr.type == "string":
            raw = source[expr.start_byte:expr.end_byte].decode("utf-8")
            return raw.strip('"""').strip("'''").strip('"').strip("'").strip()
    return None


def _get_signature(node, source: bytes) -> str:
    """
    Extract the signature (parameters + return type) from a function definition.
    Example output: (price: float, percent: int) -> float
    """
    params = next((c for c in node.children if c.type == "parameters"), None)
    return_type = next((c for c in node.children if c.type == "type"), None)

    sig = source[params.start_byte:params.end_byte].decode("utf-8") if params else "()"
    if return_type:
        sig += " -> " + source[return_type.start_byte:return_type.end_byte].decode("utf-8")
    return sig


def _make_id(file_path: str, *names: str) -> str:
    """
    Build a unique ID for an entity.
    Example: myapp/utils.py + calculate_discount → myapp.utils.calculate_discount
    """
    base = file_path.replace("/", ".").replace("\\", ".").removesuffix(".py")
    parts = [p for p in names if p]
    return ".".join([base] + parts)


def extract_okf_records(source_code: str, file_path: str) -> list[OKFRecord]:
    """
    Given raw Python source code and its file path, return a list of OKF records
    — one for the file itself, one per class, one per function/method.

    This is the only function the rest of the system calls.
    Everything else in this file is a private helper.
    """
    source_bytes = source_code.encode("utf-8")
    tree = parser.parse(source_bytes)
    root = tree.root_node

    records: list[OKFRecord] = []

    # --- File-level record ---
    records.append(OKFRecord(
        id=_make_id(file_path),
        entity_type=EntityType.FILE,
        name=file_path.split("/")[-1].split("\\")[-1],
        file_path=file_path,
        start_line=1,
        end_line=root.end_point[0] + 1,
    ))

    # --- Walk the top-level nodes ---
    for node in root.children:

        # Top-level functions
        if node.type == "function_definition":
            name_node = node.child_by_field_name("name")
            if not name_node:
                continue
            name = source_bytes[name_node.start_byte:name_node.end_byte].decode("utf-8")
            records.append(OKFRecord(
                id=_make_id(file_path, name),
                entity_type=EntityType.FUNCTION,
                name=name,
                file_path=file_path,
                start_line=node.start_point[0] + 1,
                end_line=node.end_point[0] + 1,
                docstring=_get_docstring(node, source_bytes),
                signature=_get_signature(node, source_bytes),
            ))

        # Classes — and their methods
        elif node.type == "class_definition":
            class_name_node = node.child_by_field_name("name")
            if not class_name_node:
                continue
            class_name = source_bytes[class_name_node.start_byte:class_name_node.end_byte].decode("utf-8")

            records.append(OKFRecord(
                id=_make_id(file_path, class_name),
                entity_type=EntityType.CLASS,
                name=class_name,
                file_path=file_path,
                start_line=node.start_point[0] + 1,
                end_line=node.end_point[0] + 1,
                docstring=_get_docstring(node, source_bytes),
            ))

            # Methods inside the class
            body = next((c for c in node.children if c.type == "block"), None)
            if not body:
                continue
            for child in body.children:
                if child.type == "function_definition":
                    method_name_node = child.child_by_field_name("name")
                    if not method_name_node:
                        continue
                    method_name = source_bytes[method_name_node.start_byte:method_name_node.end_byte].decode("utf-8")
                    records.append(OKFRecord(
                        id=_make_id(file_path, class_name, method_name),
                        entity_type=EntityType.METHOD,
                        name=method_name,
                        file_path=file_path,
                        start_line=child.start_point[0] + 1,
                        end_line=child.end_point[0] + 1,
                        docstring=_get_docstring(child, source_bytes),
                        signature=_get_signature(child, source_bytes),
                    ))

    return records