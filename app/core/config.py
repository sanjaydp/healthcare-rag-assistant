from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    openai_api_key: str
    model_name: str = "gpt-4o-mini"
    embedding_model: str = "text-embedding-3-small"
    chroma_persist_dir: str = "data/vectordb"
    raw_data_dir: str = "data/raw"
    processed_data_dir: str = "data/processed"
    memory_db_path: str = "data/memory/langgraph_memory.db"
    app_env: str = "development"
    log_level: str = "INFO"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        protected_namespaces=("settings_",)
    )


settings = Settings()