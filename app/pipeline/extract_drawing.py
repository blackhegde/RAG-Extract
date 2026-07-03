from pathlib import Path
from typing import Any


def extract_drawing(file_path: Path, workdir: Path) -> dict[str, Any]:
    """STUB - extract ban ve thiet ke (CAD/PDF ky thuat).

    TODO:
    - Neu co file CAD goc (.dwg/.dxf): doc bang ezdxf (chinh xac hon OCR)
    - Neu chi co anh/PDF: OCR theo vung (title block, ghi chu) + VLM sinh
      caption mo ta tong quan
    - Luu kem anh goc de hien thi lai cho user
    """
    return {
        "source": str(file_path),
        "title_block": {"title": "STUB", "drawing_no": "STUB-000"},
        "caption": "STUB: mo ta tong quan ban ve (VLM)",
        "original_image_ref": str(file_path),
    }
