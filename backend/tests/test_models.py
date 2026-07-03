import pytest
from app.parsing.models import OKFRecord, EntityType


def test_valid_function_record():
    """A complete, valid OKF record should be created without errors."""
    record = OKFRecord(
        id="myapp.utils.calculate_discount",
        entity_type=EntityType.FUNCTION,
        name="calculate_discount",
        file_path="myapp/utils.py",
        start_line=12,
        end_line=14,
        docstring="Apply a percentage discount to a price.",
        signature="(price: float, percent: int) -> float",
    )
    assert record.name == "calculate_discount"
    assert record.entity_type == EntityType.FUNCTION
    assert record.outgoing_refs == []
    assert record.incoming_refs == []


def test_docstring_is_optional():
    """Not every function has a docstring — this should still work."""
    record = OKFRecord(
        id="myapp.utils.helper",
        entity_type=EntityType.FUNCTION,
        name="helper",
        file_path="myapp/utils.py",
        start_line=1,
        end_line=3,
    )
    assert record.docstring is None
    assert record.signature is None


def test_invalid_entity_type_rejected():
    """Entity type must be one of our four allowed values — nothing else."""
    with pytest.raises(Exception):
        OKFRecord(
            id="myapp.utils.something",
            entity_type="banana",  # not a valid EntityType
            name="something",
            file_path="myapp/utils.py",
            start_line=1,
            end_line=1,
        )