from dataclasses import dataclass
from pathlib import Path

import cv2
import fitz  # PyMuPDF
import numpy as np

from app.config import settings

_RENDER_DPI = 200
# Nguong bien thien (coefficient of variation) ty le fill va chieu cao giua
# cac connected component, dung lam proxy nghi ngo chu viet tay. Da hieu
# chinh thu cong bang cach test voi Helvetica (in thuong) vs 4 font kieu
# viet tay tren macOS (Bradley Hand, Brush Script, Snell Roundhand, Marker
# Felt) - KET QUA: heuristic nay recall thap (bo sot ~1/2 kieu chu viet tay
# da test, vd Bradley Hand/Marker Felt co net kha deu nen giong chu in ve
# mat thong ke), nhung khong co false positive tren mau in thuong da test.
# => Chi nen dung nhu 1 tin hieu phu, KHONG thay the model that truoc khi
# dua vao production.
_HANDWRITING_FILL_RATIO_CV_THRESHOLD = 0.45
_HANDWRITING_HEIGHT_CV_THRESHOLD = 0.35
_MIN_STROKE_COMPONENTS = 20


@dataclass
class EnhanceResult:
    path: Path
    needs_review: bool
    review_reason: str | None
    has_handwriting: bool
    quality_score: float


def enhance_image(file_path: Path, workdir: Path) -> EnhanceResult:
    """Preprocess tang 2 cho nhanh anh (PDF scan, ban ve): render tung trang
    ra anh xam, deskew + denoise, heuristic phat hien chu viet tay, va
    quality gate dua tren do net (variance cua Laplacian).

    Neu bat ky trang nao qua mo sau enhance -> needs_review=True; main.py
    se day file sang human review (luu qua app.utils.review_store) thay vi
    tiep tuc OCR, tranh sai so lieu tren ban ve ky thuat.
    """
    doc = fitz.open(file_path)
    try:
        out_doc = fitz.open()
        min_quality_score = float("inf")
        any_handwriting = False

        for page_index in range(len(doc)):
            gray = _render_page_grayscale(doc[page_index])
            deskewed = _deskew(gray)
            denoised = cv2.fastNlMeansDenoising(deskewed, h=10)

            min_quality_score = min(min_quality_score, _sharpness_score(denoised))
            if _looks_like_handwriting(denoised):
                any_handwriting = True

            _append_page_image(out_doc, denoised)

        enhanced_path = workdir / f"{file_path.stem}_enhanced.pdf"
        out_doc.save(enhanced_path)
        out_doc.close()
    finally:
        doc.close()

    needs_review = min_quality_score < settings.blur_variance_threshold
    review_reason = (
        f"Do net anh (Laplacian variance={min_quality_score:.1f}) duoi nguong "
        f"{settings.blur_variance_threshold} sau khi enhance"
        if needs_review
        else None
    )

    return EnhanceResult(
        path=enhanced_path,
        needs_review=needs_review,
        review_reason=review_reason,
        has_handwriting=any_handwriting,
        quality_score=min_quality_score,
    )


def _render_page_grayscale(page: fitz.Page) -> np.ndarray:
    pix = page.get_pixmap(dpi=_RENDER_DPI, colorspace=fitz.csGRAY)
    img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
    return img[:, :, 0] if pix.n > 1 else img.squeeze(-1)


def _deskew(gray: np.ndarray) -> np.ndarray:
    """Uoc luong goc nghieng qua minAreaRect tren vung co noi dung (threshold
    nguoc kieu Otsu), roi xoay lai anh cho thang."""
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    coords = cv2.findNonZero(binary)
    if coords is None:
        return gray

    angle = cv2.minAreaRect(coords)[-1]
    # minAreaRect tra goc trong khoang (-90, 0]; chuan hoa ve do lech thuc te
    if angle < -45:
        angle = 90 + angle
    if abs(angle) < 0.1:
        return gray

    h, w = gray.shape
    matrix = cv2.getRotationMatrix2D((w // 2, h // 2), angle, 1.0)
    return cv2.warpAffine(gray, matrix, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)


def _sharpness_score(gray: np.ndarray) -> float:
    return float(cv2.Laplacian(gray, cv2.CV_64F).var())


def _looks_like_handwriting(gray: np.ndarray) -> bool:
    """Heuristic tam thoi (KHONG phai model ML that): dung do bien thien
    (coefficient of variation) cua ty le fill (dien tich/bbox) VA chieu cao
    giua cac connected component lam proxy cho do dong deu cua net/ky tu -
    chu in thuong deu hon, chu viet tay bien thien nhieu hon.

    Da test thu cong voi Helvetica (in) vs 4 font kieu viet tay tren macOS:
    khong co false positive tren mau in, nhung bo sot mot so kieu chu viet
    tay co net kha deu (recall thap). TODO: thay bang model classification
    that truoc khi dua vao production.
    """
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    num_labels, _, stats, _ = cv2.connectedComponentsWithStats(binary, connectivity=8)
    if num_labels - 1 < _MIN_STROKE_COMPONENTS:
        return False

    widths = stats[1:, cv2.CC_STAT_WIDTH].astype(np.float64)
    heights = stats[1:, cv2.CC_STAT_HEIGHT].astype(np.float64)
    areas = stats[1:, cv2.CC_STAT_AREA].astype(np.float64)
    bbox_areas = widths * heights
    valid = bbox_areas > 0
    if not np.any(valid):
        return False

    fill_ratio = areas[valid] / bbox_areas[valid]
    mean_fill = float(np.mean(fill_ratio))
    fill_cv = float(np.std(fill_ratio) / mean_fill) if mean_fill > 0 else 0.0

    valid_heights = heights[valid]
    mean_height = float(np.mean(valid_heights))
    height_cv = float(np.std(valid_heights) / mean_height) if mean_height > 0 else 0.0

    return (
        fill_cv > _HANDWRITING_FILL_RATIO_CV_THRESHOLD
        or height_cv > _HANDWRITING_HEIGHT_CV_THRESHOLD
    )


def _append_page_image(out_doc: fitz.Document, gray: np.ndarray) -> None:
    ok, buf = cv2.imencode(".png", gray)
    if not ok:
        raise RuntimeError("Khong encode duoc anh sau enhance")

    rect = fitz.Rect(0, 0, gray.shape[1], gray.shape[0])
    new_page = out_doc.new_page(width=rect.width, height=rect.height)
    new_page.insert_image(rect, stream=buf.tobytes())
