from enum import Enum
from pydantic import BaseModel, Field


class EntityType(str, Enum):
    """The kinds of code entities Nodiq understands."""
    FILE = "file"
    CLASS = "class"
    FUNCTION = "function"
    METHOD = "method"


class OKFRecord(BaseModel):
    """
    Open Knowledge Format — one 'recipe card' describing a single code entity.
    This is the contract between the parsing layer and everything downstream.
    Downstream stages (graph, embeddings, retrieval) only ever consume OKFRecords
    — they never touch raw AST output directly.
    """

    id: str = Field(
        description="Unique identifier. Format: module.path.EntityName e.g. myapp.utils.calculate_discount"
    )
    entity_type: EntityType = Field(
        description="What kind of thing this is: file, class, function, or method."
    )
    name: str = Field(
        description="The simple name of this entity e.g. calculate_discount"
    )
    file_path: str = Field(
        description="Path to the source file, relative to repo root e.g. myapp/utils.py"
    )
    start_line: int = Field(
        description="Line number where this entity starts (1-indexed)."
    )
    end_line: int = Field(
        description="Line number where this entity ends (1-indexed)."
    )
    docstring: str | None = Field(
        default=None,
        description="The docstring/comment written by the original developer, if any."
    )
    signature: str | None = Field(
        default=None,
        description="Function/method signature e.g. (price: float, percent: int) -> float. None for files/classes."
    )
    outgoing_refs: list[str] = Field(
        default_factory=list,
        description="IDs of entities this one calls, imports, or inherits from. Populated during parsing."
    )
    incoming_refs: list[str] = Field(
        default_factory=list,
        description="IDs of entities that call or import this one. Populated during graph construction."
    )