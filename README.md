# RAG Document Processing Service

Service xử lý tài liệu đa định dạng (PDF, DOCX, PPTX, Excel, bản vẽ
thiết kế) cho pipeline RAG: preprocess -> extract -> chuẩn hoá.

Thiết kế: **1 endpoint duy nhất**, xử lý đồng bộ trong lúc request,
không lưu kết quả trung gian — chỉ trả về kết quả cuối cùng.

## Trạng thái hiện tại

Đây là **walking skeleton** (bước 1-2 trong roadmap): toàn bộ luồng
request -> preprocess -> router -> extract -> normalize -> response
đã chạy được end-to-end, nhưng các hàm xử lý thật (`preprocess_common`,
`enhance_image`, `run_mineru`, `extract_excel`, `extract_drawing`)
hiện là **STUB** — trả kết quả giả để test hạ tầng trước khi cắm
logic thật vào.

Mỗi file stub đều có docstring TODO ghi rõ việc cần làm khi implement
thật (bước 3 trở đi).

## Chạy thử

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```

Test:
```bash
curl -X POST http://localhost:8000/v1/process \
  -F "file=@/duong/dan/den/file.pdf"
```

## Cấu trúc

```
app/
  main.py                  # FastAPI app, 1 endpoint duy nhất, wiring pool/semaphore
  config.py                # cấu hình qua biến môi trường (pool size, giới hạn)
  pipeline/
    router.py              # phân loại file
    preprocess_common.py   # preprocess tầng 1 (chung) — implement thật ĐẦU TIÊN
    preprocess_image.py    # preprocess tầng 2 (ảnh: deskew, denoise) — CPU-bound
    extract_mineru.py      # extract PDF/DOCX/Slide qua MinerU — GPU-bound
    extract_excel.py       # extract Excel — CPU-bound
    extract_drawing.py     # extract bản vẽ (CAD gốc hoặc VLM)
    normalize.py           # chuẩn hoá về Document Node schema + chunk
  utils/
    workdir.py             # quản lý + auto-cleanup thư mục tạm mỗi request
```

## Roadmap tiếp theo

1. ~~API contract tối thiểu~~ ✅
2. ~~Khung stub end-to-end~~ ✅ (repo này)
3. ~~Implement thật `preprocess_common`: convert .doc/.ppt cũ bằng
   LibreOffice headless, validate file lỗi/rỗng, validate tên file rác~~ ✅
   (nhánh convert LibreOffice chưa test được trên máy dev vì thiếu `soffice`)
4. ~~Implement `router.detect_type` phân biệt PDF scan vs text-native,
   PDF bản vẽ kỹ thuật vs văn bản thường~~ ✅
5. ~~Implement `preprocess_image.enhance_image`: deskew, denoise, phát
   hiện chữ viết tay, quality gate cho bản vẽ~~ ✅ (phát hiện chữ viết
   tay dùng heuristic tạm thời, chưa phải model thật — xem CLAUDE.md)
6. ~~Tích hợp MinerU thật vào `extract_mineru.run_mineru`~~ ✅ (code đã
   gọi đúng API `mineru.cli.common.do_parse`, nhưng package `mineru`
   chưa cài/chạy thử được trên máy dev)
7. Implement `extract_excel` (openpyxl/pandas) và `extract_drawing`
   (ezdxf cho CAD gốc, OCR theo vùng + VLM cho ảnh)
8. Hoàn thiện `normalize_and_chunk` theo schema Document Node đầy đủ

## Lưu ý vận hành

- `RAG_MAX_CONCURRENT_GPU_JOBS` phải khớp đúng số GPU vật lý khả dụng
  — không phải con số tuỳ chọn để tăng throughput.
- Timeout ở reverse proxy (nginx/traefik) cần dài hơn thời gian xử lý
  tối đa của MinerU cho file lớn nhất dự kiến.
- Vì không lưu kết quả trung gian, nếu cần debug lỗi extract, cân
  nhắc thêm structured logging tại mỗi stage (không lưu file, chỉ
  log ra stdout/log system) thay vì tắt hẳn khả năng quan sát.
