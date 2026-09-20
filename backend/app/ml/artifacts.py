import hashlib
import json
from pathlib import Path
from typing import Any

import joblib


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def save_artifact(
    model_dir: Path,
    model_version: str,
    pipeline: Any,
    metadata: dict[str, Any],
) -> tuple[Path, str]:
    model_dir.mkdir(parents=True, exist_ok=True)
    artifact_path = (model_dir / f"{model_version}.joblib").resolve()
    temporary_path = artifact_path.with_suffix(".joblib.tmp")
    joblib.dump({"pipeline": pipeline, "metadata": metadata}, temporary_path)
    temporary_path.replace(artifact_path)
    digest = file_sha256(artifact_path)
    sidecar = artifact_path.with_suffix(".metadata.json")
    sidecar.write_text(
        json.dumps({**metadata, "artifact_sha256": digest}, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return artifact_path, digest


def load_artifact(path: str | Path, expected_sha256: str | None = None) -> dict[str, Any]:
    artifact_path = Path(path)
    if expected_sha256 and file_sha256(artifact_path) != expected_sha256:
        raise ValueError("Model artifact SHA-256 does not match metadata")
    value = joblib.load(artifact_path)
    if not isinstance(value, dict) or "pipeline" not in value or "metadata" not in value:
        raise ValueError("Invalid model artifact")
    return value
