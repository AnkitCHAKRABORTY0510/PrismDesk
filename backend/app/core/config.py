from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "Prism Desk"
    APP_ENV: str = "development"

    DATABASE_HOST: str = "127.0.0.1"
    DATABASE_PORT: int = 5432
    DATABASE_NAME: str = "prism_desk"
    DATABASE_USER: str = "prism_user"
    DATABASE_PASSWORD: str

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    SESSION_EXPIRE_HOURS: int = 8
    SESSION_INACTIVITY_MINUTES: int = 30
    SESSION_COOKIE_NAME: str = "prism_session"
    COOKIE_SECURE: bool = False


settings = Settings()