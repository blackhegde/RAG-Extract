import json
import shutil
import uuid
from dataclasses import dataclass
from pathlib import Path

from app.config import settings


@dataclass
class ReviewRecord:
    review_id: str
    path: str


def save_for_review(file_path: Path, reason: str, extra: dict | None = None) -> ReviewRecord:
    """Luu file bi quality-gate flag vao REVIEW_ROOT (KHONG bi auto-cleanup
    nhu workdir cua request), kem metadata.json mo ta ly do. Mot service
    nhap lieu ben ngoai se doc file nay va gui lai ket qua da dien bo sung -
    service hien tai chi co trach nhiem luu va tra duong dan, khong tu lam
    UI/form review.
    """
    review_id = uuid.uuid4().hex
    dest_dir = Path(settings.review_root) / review_id
    dest_dir.mkdir(parents=True, exist_ok=True)

    dest_path = dest_dir / file_path.name
    shutil.copy2(file_path, dest_path)

    metadata = {
        "review_id": review_id,
        "original_filename": file_path.name,
        "reason": reason,
        **(extra or {}),
    }
    (dest_dir / "metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    return ReviewRecord(review_id=review_id, path=str(dest_path))
