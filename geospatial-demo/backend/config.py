"""Paths and constants for the geospatial demo app."""
from pathlib import Path

# Project root is geospatial-demo/
ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data" / "uploads"
OUTPUT_DIR = ROOT / "outputs"
FRONTEND_DIR = ROOT / "frontend"

DATA_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Max upload size (10 MB)
MAX_UPLOAD_BYTES = 10 * 1024 * 1024
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".webp"}
