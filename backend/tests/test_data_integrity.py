from datetime import UTC, datetime, timedelta, timezone
from enum import Enum
from types import SimpleNamespace
from uuid import UUID

from scripts.check_data_integrity import _canonical, _hash_rows


class ExampleStatus(str, Enum):
    ACTIVE = "ACTIVE"


def test_canonical_serialization_normalizes_supported_domain_values() -> None:
    value = {
        "z": [ExampleStatus.ACTIVE, UUID("00000000-0000-0000-0000-000000000001")],
        "a": datetime(2026, 9, 20, 10, 30, tzinfo=timezone(timedelta(hours=-5))),
    }

    assert _canonical(value) == {
        "a": "2026-09-20T15:30:00.000000Z",
        "z": ["ACTIVE", "00000000-0000-0000-0000-000000000001"],
    }


def test_row_hash_is_reproducible_and_sensitive_to_protected_values() -> None:
    first = SimpleNamespace(
        id=UUID("00000000-0000-0000-0000-000000000001"),
        timestamp=datetime(2026, 9, 20, 15, 30, tzinfo=UTC),
        details={"second": 2, "first": 1},
    )
    equivalent = SimpleNamespace(
        id=first.id,
        timestamp=datetime(2026, 9, 20, 10, 30, tzinfo=timezone(timedelta(hours=-5))),
        details={"first": 1, "second": 2},
    )
    changed = SimpleNamespace(
        id=first.id,
        timestamp=first.timestamp,
        details={"first": 1, "second": 3},
    )
    columns = ("id", "timestamp", "details")

    assert _hash_rows([first], columns) == _hash_rows([equivalent], columns)
    assert _hash_rows([first], columns)[1] != _hash_rows([changed], columns)[1]
