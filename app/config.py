from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="RAG_", env_file=".env", extra="ignore")

    max_concurrent_requests: int = 4
    max_concurrent_gpu_jobs: int = 1
    thread_pool_size: int = 8
    process_pool_size: int = 4

    work_root: str = "/tmp/rag-extract"
    max_upload_mb: int = 200


settings = Settings()
