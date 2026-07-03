from pathlib import Path


def preprocess_common(file_path: Path, workdir: Path) -> Path:
    """STUB - preprocess tang 1, chung cho moi loai file, chay TRUOC router.

    TODO:
    - Convert .doc/.ppt/.xls cu sang .docx/.pptx/.xlsx bang LibreOffice headless
    - Validate file loi/rong (vd PDF corrupt, file 0 byte)
    - Dedup neu can (hash noi dung)
    """
    return file_path
