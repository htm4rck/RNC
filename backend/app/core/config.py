from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Remote Career Navigator API"
    app_version: str = "0.1.0"
    cors_origins: list[str] = ["http://localhost:4200"]
    database_url: str = "postgresql+psycopg://rcn_user:rcn_password@localhost:5432/rcn"
    static_files_dir: str = "public"
    ui_prefix: str = "/"

    model_config = SettingsConfigDict(env_file=".env", env_prefix="RCN_")


settings = Settings()
