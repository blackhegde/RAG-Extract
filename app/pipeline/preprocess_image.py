from pathlib import Path


def enhance_image(file_path: Path, workdir: Path) -> Path:
    """STUB - preprocess tang 2 cho nhanh anh (PDF scan, ban ve), chay SAU router.

    TODO:
    - Deskew, denoise anh scan
    - Phat hien vung chu viet tay (route sang handwriting-OCR)
    - Quality gate: neu anh qua mo sau enhance -> flag human review,
      KHONG day tiep sang OCR de tranh sai so lieu tren ban ve ky thuat
    """
    return file_path
