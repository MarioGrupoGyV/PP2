import csv
import io

from scripts.generate_demo_event_log import CSV_COLUMNS


def build_csv(
    rows: list[dict[str, str]],
    *,
    fieldnames: list[str] | None = None,
) -> bytes:
    output = io.StringIO(newline="")
    writer = csv.DictWriter(
        output,
        fieldnames=fieldnames or CSV_COLUMNS,
        lineterminator="\n",
    )
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue().encode("utf-8")


def event_row(
    *,
    case_code: str = "IMPORT-001",
    stage_code: str = "LEAD",
    activity: str = "Lead creado",
    timestamp: str = "2026-09-01T09:00:00-05:00",
    resource: str = "Asesor 01",
    event_type: str = "STAGE_CHANGE",
    source: str = "META_ADS",
    metadata: str = "{}",
) -> dict[str, str]:
    return {
        "case_code": case_code,
        "stage_code": stage_code,
        "activity": activity,
        "timestamp": timestamp,
        "resource": resource,
        "event_type": event_type,
        "source": source,
        "metadata": metadata,
    }
