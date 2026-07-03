from pathlib import Path
from typing import Any


def run_mineru(file_path: Path, workdir: Path) -> dict[str, Any]:
    """STUB - extract PDF/DOCX/Slide qua MinerU. GPU-bound, phai chay duoi
    GPU_SEMAPHORE.

    Tra ve dang middle-json (fake) de giu bbox + heading hierarchy cho
    buoc normalize sau nay.

    TODO: goi MinerU that, giu nguyen cau truc middle-json (bbox, heading
    hierarchy, bang, cong thuc, OCR text) thay vi fake du lieu.
    """
    return {
        "source": str(file_path),
        "pdf_info": [
            {
                "page_idx": 0,
                "blocks": [
                    {
                        "type": "text",
                        "bbox": [0, 0, 100, 20],
                        "text": "STUB: noi dung trich xuat gia tu MinerU",
                        "heading_level": None,
                    }
                ],
            }
        ],
    }
