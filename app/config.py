from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="RAG_", env_file=".env", extra="ignore")

    max_concurrent_requests: int = 4
    max_concurrent_gpu_jobs: int = 1
    thread_pool_size: int = 8
    process_pool_size: int = 4

    work_root: str = "/tmp/rag-extract"
    max_upload_mb: int = 200

    # review_root: luu tru RIENG, KHONG bi auto-cleanup nhu work_root - noi
    # giu lai file bi quality-gate flag de mot service nhap lieu ben ngoai
    # doc lai va gui ket qua da dien bo sung ve sau.
    review_root: str = "/tmp/rag-extract-review"
    # Nguong do net (variance cua Laplacian): duoi nguong nay coi la anh qua
    # mo sau enhance, day sang human review thay vi co OCR ra ket qua sai.
    blur_variance_threshold: float = 100.0

    # "pipeline": backend OCR/layout co dien, KHONG dung VLM. Da test that
    # tren may dev (Apple M2, 8GB unified memory) voi file PDF scan that 20
    # trang - chay on dinh, khong crash.
    #
    # "hybrid-engine"/"vlm-engine" (dung VLM) cho dau tieng Viet CHINH XAC
    # HON NHIEU (vd "Hop Dong" -> dung "Hợp Đồng" thay vi "Hp ng" nhu model
    # "ch"/"latin" cua pipeline - xem ghi chu mineru_lang ben duoi), nhung
    # da test that va bi CRASH tien trinh do memory leak that trong
    # mlx-vlm (engine "mlx" ma MinerU tu chon tren macOS): Metal bao loi
    # "Insufficient Memory" sau ~16-82 lan goi predict lien tiep (tuy
    # backend), khong lien quan batch/window size - xay ra tren CA hybrid
    # lan vlm-engine, chi khac o so lan predict truoc khi crash. Tren
    # Linux+CUDA (production du kien), MinerU KHONG dung engine "mlx" ma
    # chon vllm/lmdeploy/transformers (nhanh code khac han) - loi nay CO
    # THE khong xay ra o do, nhung CAN VERIFY THAT tren may GPU that truoc
    # khi bat hybrid/vlm-engine cho production.
    mineru_backend: str = "pipeline"
    mineru_parse_method: str = "auto"
    # "latin" la alias, KHONG phai model rieng: trong models_config.yml
    # thuc te cua MinerU 3.4.x, "latin" (cung "en"/"japan"/"chinese_cht")
    # bi map thang ve dung chung model "ch" (ch_PP-OCRv6_small_rec_infer).
    # Model "latin_PP-OCRv5_rec_infer" xuat hien trong arch_config.yaml
    # CHUA co dict + weight di kem cuc bo, khong dung duoc qua duong nay.
    # Dict cua model "ch" (ppocrv6_dict.txt) THIEU cac ky tu dau ghep tieng
    # Viet (vd "ộ","ờ","ấ","ợ","ạ" deu MISSING dù co "ơ","ư","ă","â","đ")
    # -> da test that: "Độc lập - Tự do - Hạnh phúc" bi OCR ra "Đc lp - T
    # do - Hnh phúc". mineru_lang KHONG co gia tri nao sua duoc van de nay
    # cho backend "pipeline" - chi backend VLM (hybrid-engine/vlm-engine)
    # moi ra dau tieng Viet dung (da test that, xem ghi chu mineru_backend).
    mineru_lang: str = "ch"


settings = Settings()
