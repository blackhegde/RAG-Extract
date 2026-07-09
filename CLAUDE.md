# Bối cảnh project: rag-extract

Đây là service xử lý tài liệu đa định dạng cho pipeline RAG (Retrieval
Augmented Generation), tham khảo MinerU cho phần extract PDF.

## Bài toán

Input: nhiều loại file khác nhau — PDF (scan hoặc text-native), DOCX,
PPTX (slide), Excel, bản vẽ thiết kế (CAD/PDF kỹ thuật).

Output: dữ liệu đã chuẩn hoá về 1 schema chung (Document Node), sẵn
sàng để chunk + embedding cho hệ thống RAG.

## Kiến trúc pipeline đã chốt

```
Raw file
  -> Preprocess tầng 1 (CHUNG mọi loại: convert format cũ, dedup, validate)
  -> Router (phân loại theo loại file)
  -> Preprocess tầng 2 (RIÊNG theo loại — chỉ nhánh ảnh mới cần):
       - PDF/DOCX/Slide: detect scan vs native, nếu scan -> deskew, khử nhiễu
       - Excel: chuẩn hoá encoding
       - Bản vẽ: enhance ảnh, phát hiện vùng chữ viết tay
  -> Extract (khác nhau theo nhánh):
       - PDF/DOCX/Slide -> MinerU (layout, bảng, công thức, OCR; giữ
         output dạng middle-json để có bbox + heading hierarchy)
       - Excel -> đọc trực tiếp (openpyxl/pandas), giữ cấu trúc bảng,
         KHÔNG chunk như văn bản thường; lấy giá trị đã tính thay vì
         công thức thô
       - Bản vẽ -> nếu có file CAD gốc (.dwg/.dxf) đọc bằng ezdxf
         (chính xác hơn OCR); nếu chỉ có ảnh/PDF -> OCR theo vùng
         (title block, ghi chú) + VLM sinh caption mô tả tổng quan,
         lưu kèm ảnh gốc để hiển thị lại cho user
  -> Chuẩn hoá (Document Node schema chung) + chunk theo semantic
     boundary (heading/section), overlap 10-15%
  -> Data chuẩn, sẵn sàng embedding
```

### Quyết định quan trọng cần nhớ

- **PDF, DOCX, Slide dùng chung 1 nhánh extract (MinerU)** vì cùng
  logic layout/OCR. Excel và bản vẽ tách riêng vì bản chất dữ liệu
  khác hẳn (Excel = structured data, bản vẽ = cần OCR vùng/CAD gốc).
- **Preprocess tách 2 tầng**: tầng 1 (trước router) chỉ làm việc
  không cần biết loại file; tầng 2 (sau router) mới xử lý ảnh/OCR
  đặc thù từng loại — tránh nhồi logic if/else theo loại vào 1 module.
- Với bản vẽ: cần bước **detect chữ viết tay riêng** để route sang
  handwriting-OCR (model khác hẳn OCR in thường), và **quality gate**
  — nếu ảnh quá mờ sau enhance, đẩy sang human review thay vì cố OCR
  ra kết quả sai (hậu quả sai số liệu trên bản vẽ kỹ thuật nghiêm
  trọng hơn văn bản thường).

## Kiến trúc service (đã chốt)

- **1 API endpoint duy nhất**: upload file -> xử lý đồng bộ trong
  request -> trả kết quả cuối cùng. KHÔNG lưu kết quả trung gian,
  chỉ giữ file input trong lúc xử lý rồi xoá sạch working dir.
- Stack: Python + FastAPI.
- Concurrency:
  - `REQUEST_SEMAPHORE`: giới hạn tổng số request xử lý đồng thời
  - `GPU_SEMAPHORE`: giới hạn riêng job MinerU (GPU-bound), PHẢI
    khớp đúng số GPU vật lý, tách biệt khỏi thread/process pool
  - `ThreadPoolExecutor`: tác vụ I/O-bound (convert file, đọc/ghi
    disk, gọi MinerU)
  - `ProcessPoolExecutor`: tác vụ CPU-bound thuần Python (deskew,
    denoise, parse Excel) — bắt buộc dùng process pool vì GIL chặn
    thread trong trường hợp này

### Ngoại lệ có chủ đích: human review cho quality gate

Nhánh ảnh (`preprocess_image`) có quality gate — nếu ảnh quá mờ sau
enhance, KHÔNG cố OCR ra kết quả sai mà cần đẩy sang human review. Vì
kiến trúc chính không lưu kết quả trung gian, đây là **ngoại lệ có chủ
đích** cho riêng nhánh này:

- File gốc bị flag được lưu vào `RAG_REVIEW_ROOT` (thư mục riêng, KHÔNG
  bị auto-cleanup như working dir mỗi request) kèm `metadata.json`
  (lý do, quality_score, has_handwriting).
- Response trả về `needs_review=true`, `review_id`, `review_path` —
  KHÔNG trả node đã extract cho nhánh này.
- Service hiện tại chỉ có trách nhiệm lưu + trả đường dẫn. Một service
  nhập liệu/review RIÊNG (ngoài repo này) sẽ đọc file qua review_path
  và gửi lại kết quả đã điền bổ sung — chưa cần thêm endpoint GET/POST
  review trong service này.

## Trạng thái hiện tại

Đã dựng xong **walking skeleton**: toàn bộ luồng request -> preprocess
-> router -> extract -> normalize -> response chạy end-to-end, nhưng
các hàm xử lý thật đang là STUB (trả kết quả giả). Mỗi file stub có
docstring TODO mô tả việc cần làm.

Cấu trúc:
```
app/main.py                    # endpoint, wiring pool/semaphore
app/config.py                  # config qua biến môi trường
app/pipeline/router.py         # detect_type — STUB
app/pipeline/preprocess_common.py  # STUB, ưu tiên implement ĐẦU TIÊN
app/pipeline/preprocess_image.py   # STUB
app/pipeline/extract_mineru.py     # STUB
app/pipeline/extract_excel.py      # STUB
app/pipeline/extract_drawing.py    # STUB
app/pipeline/normalize.py          # STUB, đã có Document Node schema mẫu
app/utils/workdir.py           # auto-cleanup working dir mỗi request
```

## Roadmap tiếp theo (theo đúng thứ tự ưu tiên)

1. ✅ API contract tối thiểu
2. ✅ Khung stub end-to-end
3. ✅ Implement thật `preprocess_common`: convert .doc/.ppt cũ bằng
   LibreOffice headless, validate file lỗi/rỗng, validate tên file rác
   (ký tự đặc biệt lặp lại). Lưu ý: nhánh convert LibreOffice mới chỉ
   review code, chưa test được trên máy dev vì thiếu `soffice` cài đặt
4. ✅ Implement `router.detect_type`: phân biệt PDF scan vs
   text-native, PDF bản vẽ kỹ thuật vs văn bản thường (không chỉ
   dựa vào đuôi file — dùng magic bytes)
5. ✅ Implement `preprocess_image.enhance_image`: deskew (minAreaRect +
   warpAffine), denoise (fastNlMeansDenoising), quality gate (variance
   Laplacian). Phát hiện chữ viết tay dùng **heuristic tạm thời** (CV của
   fill-ratio/chiều cao connected component) — đã test với Helvetica vs 4
   font kiểu viết tay trên macOS: không false positive trên mẫu in, nhưng
   bỏ sót ~2/4 kiểu chữ viết tay có nét đều (recall thấp). Cần thay bằng
   model classification thật trước khi dùng production.
6. ✅ Tích hợp `extract_mineru.run_mineru` với `mineru.cli.common.do_parse`,
   ĐÃ TEST THẬT với file PDF scan thật 20 trang trên máy dev (Apple M2,
   8GB unified memory, cài `mineru[core,mlx]`). Kết quả quan trọng cần nhớ:
   - **Backend mặc định: `pipeline`** (OCR/layout cổ điển, không VLM) —
     chạy ổn định, không crash, đã verify full 20 trang.
   - **`hybrid-engine`/`vlm-engine` (VLM) cho dấu tiếng Việt ĐÚNG HƠN
     NHIỀU** (vd ra đúng "Hợp Đồng", "Độc lập - Tự do - Hạnh phúc" thay vì
     bị rụng dấu) vì không bị giới hạn bởi dict ký tự cố định như pipeline.
     NHƯNG đã test thật và bị **crash tiến trình** (native crash, không
     bắt được bằng try/except Python) do memory leak thật trong `mlx-vlm`
     — Metal báo "Insufficient Memory" sau ~16-82 lần gọi predict liên
     tiếp (không liên quan batch/window size, xảy ra ở cả hybrid lẫn
     vlm-engine, chỉ khác số lần predict trước khi crash). Trên
     Linux+CUDA (production dự kiến), MinerU KHÔNG dùng engine "mlx" mà
     chọn vllm/lmdeploy/transformers (nhánh code khác hẳn) — lỗi này CÓ
     THỂ không xảy ra ở đó, nhưng **CẦN VERIFY THẬT trên máy GPU thật**
     trước khi bật hybrid/vlm-engine cho production.
   - **`mineru_lang="latin"` KHÔNG có tác dụng sửa dấu tiếng Việt** cho
     backend `pipeline` như ghi chú cũ ở đây từng kỳ vọng — đã kiểm tra
     trực tiếp `models_config.yml` của MinerU 3.4.x: "latin" chỉ là alias
     trỏ thẳng về model "ch" (`ch_PP-OCRv6_small_rec_infer`), và dict của
     model "ch" (`ppocrv6_dict.txt`) THIẾU các ký tự dấu ghép tiếng Việt
     (vd "ộ","ờ","ấ","ợ","ạ" đều MISSING dù có "ơ","ư","ă","â","đ"). Model
     `latin_PP-OCRv5_rec_infer` xuất hiện trong `arch_config.yaml` nhưng
     CHƯA có dict + weight cục bộ đi kèm — không dùng được ngay. Đã đổi
     `mineru_lang` về `"ch"` cho khớp thực tế (giá trị "latin" gây hiểu
     nhầm sai vì không có model latin thật đứng sau nó).
7. ⬜ Implement `extract_excel` và `extract_drawing`
8. ⬜ Hoàn thiện `normalize_and_chunk` theo schema Document Node đầy đủ

## Lưu ý vận hành

- `RAG_MAX_CONCURRENT_GPU_JOBS` phải khớp số GPU vật lý thật.
- Timeout reverse proxy (nginx/traefik) cần dài hơn thời gian xử lý
  tối đa của MinerU cho file lớn nhất dự kiến.
- Vì không lưu kết quả trung gian, cần structured logging tại mỗi
  stage (log ra stdout, không lưu file) để debug khi có lỗi extract.
