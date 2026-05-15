"""Simple local file storage for uploads and job metadata."""
from __future__ import annotations

import json
import shutil
import uuid
from pathlib import Path

from backend.config import ALLOWED_EXTENSIONS, DATA_DIR, MAX_UPLOAD_BYTES, OUTPUT_DIR


def new_id() -> str:
    return uuid.uuid4().hex[:12]


def validate_extension(filename: str) -> str:
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError(f"Unsupported file type '{ext}'. Allowed: {sorted(ALLOWED_EXTENSIONS)}")
    return ext


def save_upload(content: bytes, filename: str) -> dict:
    if len(content) > MAX_UPLOAD_BYTES:
        raise ValueError(f"File too large (max {MAX_UPLOAD_BYTES // (1024*1024)} MB)")
    ext = validate_extension(filename)
    image_id = new_id()
    path = DATA_DIR / f"{image_id}{ext}"
    path.write_bytes(content)
    meta = {"image_id": image_id, "filename": path.name, "original_name": filename}
    _write_meta(DATA_DIR / f"{image_id}.json", meta)
    return meta


def load_image_path(image_id: str) -> Path:
    for p in DATA_DIR.glob(f"{image_id}.*"):
        if p.suffix.lower() in ALLOWED_EXTENSIONS:
            return p
    raise FileNotFoundError(f"Image not found: {image_id}")


def save_job_status(job_id: str, status: str, message: str = "") -> None:
    path = OUTPUT_DIR / f"{job_id}_status.json"
    path.write_text(
        json.dumps({"job_id": job_id, "status": status, "message": message}),
        encoding="utf-8",
    )


def get_job_status(job_id: str) -> dict | None:
    path = OUTPUT_DIR / f"{job_id}_status.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _write_meta(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def list_uploads() -> list[dict]:
    items = []
    for meta_file in DATA_DIR.glob("*.json"):
        items.append(json.loads(meta_file.read_text(encoding="utf-8")))
    return items


def clear_outputs() -> None:
    """Optional helper for dev resets."""
    for p in OUTPUT_DIR.iterdir():
        if p.is_file():
            p.unlink()
        elif p.is_dir():
            shutil.rmtree(p)
