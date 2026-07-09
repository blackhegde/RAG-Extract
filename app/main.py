import asyncio
import shutil
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile

from app.config import settings
from app.pipeline.extract_drawing import extract_drawing
from app.pipeline.extract_excel import extract_excel
from app.pipeline.extract_mineru import run_mineru
from app.pipeline.normalize import normalize_and_chunk
from app.pipeline.preprocess_common import preprocess_common
from app.pipeline.preprocess_image import enhance_image
from app.pipeline.router import FileType, detect_type
from app.utils.review_store import save_for_review
from app.utils.workdir import request_workdir

STATE: dict = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    STATE["request_semaphore"] = asyncio.Semaphore(settings.max_concurrent_requests)
    STATE["gpu_semaphore"] = asyncio.Semaphore(settings.max_concurrent_gpu_jobs)
    STATE["thread_pool"] = ThreadPoolExecutor(max_workers=settings.thread_pool_size)
    STATE["process_pool"] = ProcessPoolExecutor(max_workers=settings.process_pool_size)
    Path(settings.work_root).mkdir(parents=True, exist_ok=True)
    yield
    STATE["thread_pool"].shutdown(wait=True)
    STATE["process_pool"].shutdown(wait=True)


app = FastAPI(title="RAG Document Processing Service", lifespan=lifespan)


@app.post("/v1/process")
async def process_document(file: UploadFile = File(...)):
    async with STATE["request_semaphore"]:
        with request_workdir() as workdir:
            # Chi lay ten file (bo qua moi thanh phan thu muc) de tranh path
            # traversal / ghi de file ngoai workdir qua filename do client gui
            safe_name = Path(file.filename or "").name
            raw_path = workdir / safe_name
            with raw_path.open("wb") as f:
                shutil.copyfileobj(file.file, f)

            loop = asyncio.get_running_loop()
            thread_pool = STATE["thread_pool"]
            process_pool = STATE["process_pool"]

            # Preprocess tang 1 (chung, I/O-bound)
            try:
                common_path = await loop.run_in_executor(
                    thread_pool, preprocess_common, raw_path, workdir
                )
            except ValueError as exc:
                raise HTTPException(status_code=422, detail=str(exc)) from exc
            except RuntimeError as exc:
                raise HTTPException(status_code=500, detail=str(exc)) from exc

            try:
                file_type = detect_type(common_path)
            except ValueError as exc:
                raise HTTPException(status_code=422, detail=str(exc)) from exc

            # Preprocess tang 2 (rieng theo loai, chi nhanh anh moi can, CPU-bound)
            has_handwriting = False
            if file_type in (FileType.PDF_SCAN, FileType.DRAWING):
                pre_enhance_path = common_path
                enhance_result = await loop.run_in_executor(
                    process_pool, enhance_image, common_path, workdir
                )

                if enhance_result.needs_review:
                    # Anh qua mo sau enhance: KHONG co OCR tiep vi de ra sai
                    # so lieu tren ban ve ky thuat. Luu file goc vao
                    # REVIEW_ROOT (persistent, khac workdir se bi xoa) de
                    # mot service nhap lieu ben ngoai xu ly tiep.
                    record = save_for_review(
                        pre_enhance_path,
                        reason=enhance_result.review_reason,
                        extra={
                            "file_type": file_type.value,
                            "quality_score": enhance_result.quality_score,
                            "has_handwriting": enhance_result.has_handwriting,
                        },
                    )
                    return {
                        "file_type": file_type.value,
                        "needs_review": True,
                        "review_id": record.review_id,
                        "review_path": record.path,
                        "reason": enhance_result.review_reason,
                        "nodes": [],
                    }

                common_path = enhance_result.path
                has_handwriting = enhance_result.has_handwriting

            # Extract (khac nhau theo nhanh)
            try:
                if file_type in (FileType.PDF_NATIVE, FileType.PDF_SCAN, FileType.DOCX, FileType.PPTX):
                    async with STATE["gpu_semaphore"]:
                        extracted = await loop.run_in_executor(
                            thread_pool, run_mineru, common_path, workdir
                        )
                elif file_type == FileType.EXCEL:
                    extracted = await loop.run_in_executor(
                        process_pool, extract_excel, common_path, workdir
                    )
                elif file_type == FileType.DRAWING:
                    extracted = await loop.run_in_executor(
                        process_pool, extract_drawing, common_path, workdir
                    )
                else:
                    raise HTTPException(status_code=422, detail=f"Loai file chua ho tro: {file_type}")
            except ValueError as exc:
                raise HTTPException(status_code=422, detail=str(exc)) from exc
            except RuntimeError as exc:
                raise HTTPException(status_code=500, detail=str(exc)) from exc

            nodes = normalize_and_chunk(extracted, file_type.value, file.filename)

            return {
                "file_type": file_type.value,
                "needs_review": False,
                "has_handwriting": has_handwriting,
                "nodes": [n.model_dump() for n in nodes],
            }
