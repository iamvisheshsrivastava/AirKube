"""
Lightweight geospatial image analysis pipeline.

Uses OpenCV + NumPy only (no heavy deep learning) so beginners can
follow each step: preprocess -> detect -> visualize -> metrics.
"""
from __future__ import annotations

import csv
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import cv2
import numpy as np
from skimage import morphology
from skimage.measure import label, regionprops


@dataclass
class DetectedRegion:
    """One connected area flagged as vegetation loss or strong change."""

    region_id: int
    x: int
    y: int
    width: int
    height: int
    area_pixels: int
    area_percent: float


@dataclass
class AnalysisResult:
    job_id: str
    image_id: str
    mode: str  # "single" | "compare"
    forest_percent: float
    change_percent: float
    risk_score: float
    regions: list[DetectedRegion]
    overlay_path: str
    heatmap_path: str | None
    csv_path: str
    metrics_path: str
    created_at: str


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def preprocess(image_bgr: np.ndarray, max_side: int = 1024) -> np.ndarray:
    """
    Standardize input: resize if huge, denoise slightly, work in BGR uint8.
    Satellite tiles can be large; we cap size for fast demo runs.
    """
    h, w = image_bgr.shape[:2]
    scale = min(1.0, max_side / max(h, w))
    if scale < 1.0:
        image_bgr = cv2.resize(
            image_bgr, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA
        )
    # Mild blur reduces sensor noise before thresholding
    return cv2.GaussianBlur(image_bgr, (5, 5), 0)


def estimate_forest_mask(image_bgr: np.ndarray) -> np.ndarray:
    """
    Approximate forest/vegetation with an Excess Green index (ExG).

    ExG = 2*G - R - B  (higher = greener). This is a classic, explainable
    vegetation index when you only have RGB (no NIR band).
    """
    b, g, r = cv2.split(image_bgr.astype(np.float32))
    exg = 2.0 * g - r - b
    # Normalize to 0-255 for thresholding
    exg_norm = cv2.normalize(exg, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
    _, mask = cv2.threshold(exg_norm, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    # Clean small speckles
    mask = morphology.remove_small_objects(mask.astype(bool), min_size=64)
    return (mask.astype(np.uint8)) * 255


def detect_change_mask(before_bgr: np.ndarray, after_bgr: np.ndarray) -> np.ndarray:
    """
    Pixel-wise difference between two aligned scenes.

    Large differences often mean land-cover change (roads, clearing, burn).
    """
    before = preprocess(before_bgr)
    after = preprocess(after_bgr)
    if before.shape != after.shape:
        after = cv2.resize(after, (before.shape[1], before.shape[0]))

    diff = cv2.absdiff(before, after)
    gray = cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (5, 5), 0)
    _, change = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    change = morphology.remove_small_objects(change.astype(bool), min_size=48)
    return (change.astype(np.uint8)) * 255


def build_heatmap(change_mask: np.ndarray) -> np.ndarray:
    """Color-map change intensity for the UI overlay."""
    heat = cv2.applyColorMap(change_mask, cv2.COLORMAP_JET)
    return heat


def find_regions(mask: np.ndarray, min_area: int = 100) -> list[DetectedRegion]:
    """Label connected components and return bounding boxes + area stats."""
    labeled = label(mask > 0)
    total_pixels = mask.shape[0] * mask.shape[1]
    regions: list[DetectedRegion] = []
    rid = 1
    for prop in regionprops(labeled):
        if prop.area < min_area:
            continue
        minr, minc, maxr, maxc = prop.bbox
        regions.append(
            DetectedRegion(
                region_id=rid,
                x=int(minc),
                y=int(minr),
                width=int(maxc - minc),
                height=int(maxr - minr),
                area_pixels=int(prop.area),
                area_percent=round(100.0 * prop.area / total_pixels, 3),
            )
        )
        rid += 1
    return regions


def draw_overlay(
    image_bgr: np.ndarray,
    forest_mask: np.ndarray | None,
    change_mask: np.ndarray | None,
    regions: list[DetectedRegion],
) -> np.ndarray:
    """Draw green forest tint, red change boxes, and numeric labels."""
    out = image_bgr.copy()
    if forest_mask is not None:
        green = np.zeros_like(out)
        green[:, :, 1] = forest_mask // 3
        out = cv2.addWeighted(out, 0.75, green, 0.25, 0)

    if change_mask is not None:
        heat = build_heatmap(change_mask)
        mask_bool = change_mask > 0
        out[mask_bool] = cv2.addWeighted(out, 0.5, heat, 0.5, 0)[mask_bool]

    for r in regions:
        cv2.rectangle(
            out,
            (r.x, r.y),
            (r.x + r.width, r.y + r.height),
            (0, 0, 255),
            2,
        )
        cv2.putText(
            out,
            f"#{r.region_id}",
            (r.x, max(15, r.y - 5)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.45,
            (0, 0, 255),
            1,
            cv2.LINE_AA,
        )
    return out


def compute_risk_score(change_percent: float, forest_percent: float, n_regions: int) -> float:
    """
    Simple heuristic risk score 0-100 for learning purposes.

    More change + fewer remaining forest + more patches => higher score.
    """
    loss_factor = min(100.0, change_percent * 2.5)
    forest_factor = max(0.0, 40.0 - forest_percent * 0.4)
    patch_factor = min(30.0, n_regions * 2.0)
    return round(min(100.0, loss_factor + forest_factor + patch_factor), 1)


def save_csv(path: Path, regions: list[DetectedRegion]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "region_id",
                "x",
                "y",
                "width",
                "height",
                "area_pixels",
                "area_percent",
            ],
        )
        writer.writeheader()
        for r in regions:
            writer.writerow(asdict(r))


def analyze_single(image_bgr: np.ndarray, job_id: str, image_id: str, out_dir: Path) -> dict[str, Any]:
    """Run vegetation segmentation on one satellite image."""
    processed = preprocess(image_bgr)
    forest_mask = estimate_forest_mask(processed)
    total = forest_mask.size
    forest_pixels = int(np.count_nonzero(forest_mask))
    forest_percent = round(100.0 * forest_pixels / total, 2)

    # Treat low-vegetation patches inside the scene as "possible loss" for demo
    inv = cv2.bitwise_not(forest_mask)
    regions = find_regions(inv, min_area=200)
    change_percent = round(sum(r.area_percent for r in regions), 2)
    risk = compute_risk_score(change_percent, forest_percent, len(regions))

    overlay = draw_overlay(processed, forest_mask, None, regions[:12])
    overlay_path = out_dir / f"{job_id}_overlay.png"
    cv2.imwrite(str(overlay_path), overlay)

    csv_path = out_dir / f"{job_id}_regions.csv"
    save_csv(csv_path, regions)

    result = AnalysisResult(
        job_id=job_id,
        image_id=image_id,
        mode="single",
        forest_percent=forest_percent,
        change_percent=change_percent,
        risk_score=risk,
        regions=regions[:50],
        overlay_path=str(overlay_path.name),
        heatmap_path=None,
        csv_path=str(csv_path.name),
        metrics_path=f"{job_id}_metrics.json",
        created_at=_utc_now(),
    )
    metrics = {
        **{k: v for k, v in asdict(result).items() if k != "regions"},
        "regions_count": len(regions),
        "regions": [asdict(r) for r in result.regions],
    }
    metrics_file = out_dir / result.metrics_path
    metrics_file.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    return metrics


def analyze_compare(
    before_bgr: np.ndarray,
    after_bgr: np.ndarray,
    job_id: str,
    before_id: str,
    after_id: str,
    out_dir: Path,
) -> dict[str, Any]:
    """Compare two dates and highlight likely deforestation / land-cover change."""
    before_p = preprocess(before_bgr)
    after_p = preprocess(after_bgr)

    forest_before = estimate_forest_mask(before_p)
    forest_after = estimate_forest_mask(after_p)
    total = forest_before.size
    fb = 100.0 * np.count_nonzero(forest_before) / total
    fa = 100.0 * np.count_nonzero(forest_after) / total
    forest_percent = round((fb + fa) / 2, 2)

    change_mask = detect_change_mask(before_p, after_p)
    change_pixels = int(np.count_nonzero(change_mask))
    change_percent = round(100.0 * change_pixels / total, 2)
    regions = find_regions(change_mask, min_area=80)
    risk = compute_risk_score(change_percent, forest_percent, len(regions))

    overlay = draw_overlay(after_p, forest_after, change_mask, regions[:15])
    overlay_path = out_dir / f"{job_id}_overlay.png"
    heatmap_path = out_dir / f"{job_id}_heatmap.png"
    cv2.imwrite(str(overlay_path), overlay)
    cv2.imwrite(str(heatmap_path), build_heatmap(change_mask))

    csv_path = out_dir / f"{job_id}_regions.csv"
    save_csv(csv_path, regions)

    result = AnalysisResult(
        job_id=job_id,
        image_id=f"{before_id}+{after_id}",
        mode="compare",
        forest_percent=forest_percent,
        change_percent=change_percent,
        risk_score=risk,
        regions=regions[:50],
        overlay_path=str(overlay_path.name),
        heatmap_path=str(heatmap_path.name),
        csv_path=str(csv_path.name),
        metrics_path=f"{job_id}_metrics.json",
        created_at=_utc_now(),
    )
    metrics = {
        **{k: v for k, v in asdict(result).items() if k != "regions"},
        "forest_before_percent": round(fb, 2),
        "forest_after_percent": round(fa, 2),
        "regions_count": len(regions),
        "regions": [asdict(r) for r in result.regions],
    }
    metrics_file = out_dir / result.metrics_path
    metrics_file.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    return metrics
