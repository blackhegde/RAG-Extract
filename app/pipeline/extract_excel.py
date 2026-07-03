from pathlib import Path
from typing import Any


def extract_excel(file_path: Path, workdir: Path) -> dict[str, Any]:
    """STUB - extract Excel. CPU-bound (chay trong ProcessPoolExecutor).

    TODO:
    - Doc bang openpyxl/pandas, giu cau truc bang (sheet, row, col)
    - KHONG chunk nhu van ban thuong
    - Lay gia tri da tinh (cached value) thay vi cong thuc tho
    """
    return {
        "source": str(file_path),
        "sheets": [
            {
                "name": "Sheet1",
                "rows": [["STUB", "du lieu", "gia"]],
            }
        ],
    }
