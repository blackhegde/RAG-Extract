from typing import Any, Optional

from pydantic import BaseModel


class DocumentNode(BaseModel):
    """Schema chung sau khi chuan hoa, san sang chunk + embedding."""

    id: str
    source_file: str
    file_type: str
    content: str
    heading_path: list[str] = []
    page: Optional[int] = None
    bbox: Optional[list[float]] = None
    metadata: dict[str, Any] = {}


def normalize_and_chunk(extracted: dict[str, Any], file_type: str, source_file: str) -> list[DocumentNode]:
    """STUB - chuan hoa ket qua extract (khac nhau theo nhanh) ve chung 1
    schema DocumentNode, roi chunk theo semantic boundary (heading/section),
    overlap 10-15%.

    TODO:
    - Nhanh MinerU: doc bbox + heading hierarchy tu middle-json, chunk theo
      section, overlap 10-15%
    - Nhanh Excel: moi sheet/bang la 1 hoac nhieu DocumentNode, khong chunk
      theo cau
    - Nhanh ban ve: title_block + caption la 1 DocumentNode, kem
      original_image_ref trong metadata
    """
    return [
        DocumentNode(
            id="stub-0",
            source_file=source_file,
            file_type=file_type,
            content="STUB: noi dung sau chuan hoa",
            metadata={"raw": extracted},
        )
    ]
