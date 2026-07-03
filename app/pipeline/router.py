import zipfile
from enum import Enum
from pathlib import Path

import fitz  # PyMuPDF


class FileType(str, Enum):
    PDF_NATIVE = "pdf_native"
    PDF_SCAN = "pdf_scan"
    DOCX = "docx"
    PPTX = "pptx"
    EXCEL = "excel"
    DRAWING = "drawing"


_PDF_MAGIC = b"%PDF-"
_OLE_MAGIC = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"
_ZIP_MAGIC = b"PK\x03\x04"
_DWG_MAGIC = b"AC10"  # DWG nhi phan luon mo dau bang "AC" + ma phien ban

_OOXML_MARKERS = {
    "word/document.xml": FileType.DOCX,
    "ppt/presentation.xml": FileType.PPTX,
    "xl/workbook.xml": FileType.EXCEL,
}

_PAGES_TO_SAMPLE = 5
# Nguong xac dinh PDF la ban ve ky thuat: nhieu net ve (line/curve) hoac
# kho giay lon hon A4 thong thuong (A4 ~ 595x842pt) kem it text
_DRAWING_VECTOR_THRESHOLD = 80
_DRAWING_MAX_CHARS_PER_PAGE = 400
_LARGE_SHEET_POINTS = 1000
# Nguong phan biet scan vs native: trung binh so ky tu text/trang
_SCAN_MIN_CHARS_PER_PAGE = 20


def detect_type(file_path: Path) -> FileType:
    """Phan loai file dua tren magic bytes + phan tich noi dung, khong chi
    dua vao duoi file.

    - PDF: phan biet PDF_SCAN (khong co text layer, can OCR) vs PDF_NATIVE
      (co text layer san sang). PDF nhan dien la ban ve ky thuat (nhieu net
      ve, kho giay lon, it text) duoc xep vao DRAWING.
    - Office moi (OOXML .docx/.pptx/.xlsx): la file zip, phan biet qua cac
      thu muc noi bo (word/, ppt/, xl/) thay vi tin vao duoi file.
    - Office cu (.doc/.ppt/.xls, dinh dang OLE): phai duoc preprocess_common
      convert sang OOXML truoc; o day bao loi ro rang de de debug thay vi
      doan sai loai file.
    - CAD goc: DWG nhan qua magic bytes "AC1x"; DXF la file text nen sniff
      theo tu khoa cau truc "SECTION" trong phan dau file.
    """
    header = file_path.read_bytes()[:8]

    if header.startswith(_PDF_MAGIC):
        return _detect_pdf_subtype(file_path)

    if header.startswith(_OLE_MAGIC):
        raise ValueError(
            f"{file_path.name}: dinh dang Office cu (.doc/.ppt/.xls) chua "
            "duoc convert sang OOXML — can chay qua preprocess_common truoc"
        )

    if header.startswith(_ZIP_MAGIC):
        return _detect_ooxml_subtype(file_path)

    if header[:4] == _DWG_MAGIC:
        return FileType.DRAWING

    if _looks_like_dxf(file_path):
        return FileType.DRAWING

    raise ValueError(f"Khong nhan dien duoc loai file: {file_path.name}")


def _detect_pdf_subtype(file_path: Path) -> FileType:
    doc = fitz.open(file_path)
    try:
        page_count = min(len(doc), _PAGES_TO_SAMPLE)
        pages = [doc[i] for i in range(page_count)]

        total_chars = 0
        max_vector_count = 0
        max_sheet_dim = 0.0
        for page in pages:
            total_chars += len(page.get_text("text").strip())
            max_vector_count = max(max_vector_count, len(page.get_drawings()))
            rect = page.rect
            max_sheet_dim = max(max_sheet_dim, rect.width, rect.height)

        avg_chars_per_page = total_chars / max(page_count, 1)

        is_drawing_like = max_vector_count >= _DRAWING_VECTOR_THRESHOLD or (
            max_sheet_dim >= _LARGE_SHEET_POINTS and avg_chars_per_page <= _DRAWING_MAX_CHARS_PER_PAGE
        )
        if is_drawing_like:
            return FileType.DRAWING

        if avg_chars_per_page < _SCAN_MIN_CHARS_PER_PAGE:
            return FileType.PDF_SCAN

        return FileType.PDF_NATIVE
    finally:
        doc.close()


def _detect_ooxml_subtype(file_path: Path) -> FileType:
    with zipfile.ZipFile(file_path) as zf:
        names = set(zf.namelist())
    for marker, file_type in _OOXML_MARKERS.items():
        if marker in names:
            return file_type
    raise ValueError(f"{file_path.name}: file zip nhung khong phai OOXML da biet (docx/pptx/xlsx)")


def _looks_like_dxf(file_path: Path) -> bool:
    if file_path.suffix.lower() != ".dxf":
        return False
    with file_path.open("r", errors="ignore") as f:
        head = f.read(4000)
    return "SECTION" in head
