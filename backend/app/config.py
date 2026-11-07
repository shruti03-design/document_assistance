from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "mysql+pymysql://docassist:docassist@localhost:3306/docassist"
    qdrant_url: str = "http://localhost:6333"
    openai_api_key: str = ""
    cors_origins: str = "http://localhost:5173"
    upload_dir: str = "uploads"
    max_upload_mb: int = 20
    chunk_size: int = 1000      # characters
    chunk_overlap: int = 200    # characters

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
