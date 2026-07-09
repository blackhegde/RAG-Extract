import json
from pathlib import Path
from typing import Any

from app.config import settings


def run_mineru(file_path: Path, workdir: Path) -> dict[str, Any]:
    """Extract PDF/DOCX/Slide qua MinerU. GPU-bound, phai chay duoi
    GPU_SEMAPHORE (xem app/main.py).

    Backend mac dinh "hybrid-engine" (mac dinh chinh thuc cua MinerU 3.4.x):
    layout + OCR co dien ket hop VLM cho cong thuc/bang phuc tap. Tren macOS
    tu dong chon inference engine "mlx" neu co mlx-vlm, tan dung GPU tich
    hop (Apple Silicon) khong can CUDA.

    Goi thang mineru.cli.common.do_parse - entrypoint noi bo ma chinh CLI
    `mineru` dung - roi doc lai file `<ten>_middle.json` do no ghi ra (vi
    tri phu thuoc backend, dung lai build_parse_dir cua chinh MinerU thay vi
    hardcode) de giu nguyen bbox + heading hierarchy cho buoc normalize.

    Ngon ngu OCR mac dinh (mineru_lang) dang de "latin" - ban PP-OCRv5 moi
    nhat cua MinerU 3.4.x co model rec rieng cho Latin
    ("latin_PP-OCRv5_rec_infer") da mo rong ho tro tieng Viet co dau; van
    nen kiem tra do chinh xac thuc te.
    """
    try:
        from mineru.cli.common import do_parse
        from mineru.cli.output_paths import build_parse_dir
    except ImportError as exc:
        raise RuntimeError(
            f"Thieu dependency mineru (hoac extra can thiet cho backend "
            f"'{settings.mineru_backend}') - xem requirements.txt"
        ) from exc

    output_dir = workdir / "mineru_output"
    output_dir.mkdir(parents=True, exist_ok=True)
    pdf_stem = file_path.stem

    do_parse(
        output_dir=str(output_dir),
        pdf_file_names=[pdf_stem],
        pdf_bytes_list=[file_path.read_bytes()],
        p_lang_list=[settings.mineru_lang],
        backend=settings.mineru_backend,
        parse_method=settings.mineru_parse_method,
    )

    parse_dir = build_parse_dir(output_dir, pdf_stem, settings.mineru_backend, settings.mineru_parse_method)
    middle_json_path = parse_dir / f"{pdf_stem}_middle.json"
    if not middle_json_path.exists():
        raise RuntimeError(f"MinerU khong tao ra middle json cho {file_path.name}")

    return json.loads(middle_json_path.read_text(encoding="utf-8"))
