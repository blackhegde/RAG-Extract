import re
import subprocess
from pathlib import Path

_LEGACY_OFFICE_TARGETS = {
    ".doc": "docx",
    ".ppt": "pptx",
    ".xls": "xlsx",
}

_LIBREOFFICE_TIMEOUT_SEC = 120
_MAX_FILENAME_LEN = 255

# Ky tu dieu khien hoac path separator khong duoc phep trong ten file
_INVALID_FILENAME_CHARS = re.compile(r"[\\/\x00-\x1f]")
# Cung 1 ky tu dac biet (khong phai chu/so/khoang trang) lap lai >=4 lan lien tiep
# -> dau hieu ten file rac (vd "!@$%%%%%%!@!!!@#$")
_REPEATED_SYMBOL_RUN = re.compile(r"([^\w\s])\1{3,}")
_WORD_CHAR = re.compile(r"\w", re.UNICODE)


def preprocess_common(file_path: Path, workdir: Path) -> Path:
    """Preprocess tang 1, chung cho moi loai file, chay TRUOC router.

    - Validate ten file: rong/qua dai/chua ky tu dieu khien, hoac phan ten
      (khong tinh duoi) toan ky tu dac biet lap lai -> day thuong la file
      rac/upload loi chu khong phai tai lieu that, reject som truoc khi
      ton tai gio xu ly.
    - Validate file rong hoac khong doc duoc.
    - Convert dinh dang Office cu (.doc/.ppt/.xls) sang OOXML bang
      LibreOffice headless, de router va cac buoc sau chi can xu ly 1
      dinh dang moi cho moi ho.
    """
    _validate_filename(file_path.name)
    _validate_not_empty(file_path)

    suffix = file_path.suffix.lower()
    if suffix in _LEGACY_OFFICE_TARGETS:
        file_path = _convert_legacy_office(file_path, workdir)

    return file_path


def _validate_filename(name: str) -> None:
    if not name or not name.strip():
        raise ValueError("Ten file rong")
    if len(name) > _MAX_FILENAME_LEN:
        raise ValueError(f"Ten file qua dai ({len(name)} ky tu)")
    if _INVALID_FILENAME_CHARS.search(name):
        raise ValueError(f"Ten file chua ky tu khong hop le: {name!r}")

    stem = Path(name).stem
    if _REPEATED_SYMBOL_RUN.search(name) or not _WORD_CHAR.search(stem):
        raise ValueError(
            f"Ten file khong hop le, nghi la file rac (toan ky tu dac biet lap lai): {name!r}"
        )


def _validate_not_empty(file_path: Path) -> None:
    if not file_path.exists():
        raise ValueError(f"File khong ton tai: {file_path.name}")
    if file_path.stat().st_size == 0:
        raise ValueError(f"File rong (0 byte): {file_path.name}")


def _convert_legacy_office(file_path: Path, workdir: Path) -> Path:
    target_ext = _LEGACY_OFFICE_TARGETS[file_path.suffix.lower()]
    try:
        subprocess.run(
            [
                "soffice",
                "--headless",
                "--convert-to",
                target_ext,
                "--outdir",
                str(workdir),
                str(file_path),
            ],
            check=True,
            capture_output=True,
            timeout=_LIBREOFFICE_TIMEOUT_SEC,
        )
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        raise RuntimeError(f"LibreOffice convert that bai cho {file_path.name}: {exc}") from exc

    converted_path = workdir / f"{file_path.stem}.{target_ext}"
    if not converted_path.exists():
        raise RuntimeError(f"LibreOffice convert khong tao ra file dau ra cho {file_path.name}")
    return converted_path