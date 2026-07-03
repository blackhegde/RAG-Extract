import shutil
import uuid
from contextlib import contextmanager
from pathlib import Path

from app.config import settings


@contextmanager
def request_workdir():
    """Tao thu muc lam viec rieng cho 1 request, tu dong xoa sach khi xong."""
    path = Path(settings.work_root) / uuid.uuid4().hex
    path.mkdir(parents=True, exist_ok=True)
    try:
        yield path
    finally:
        shutil.rmtree(path, ignore_errors=True)
