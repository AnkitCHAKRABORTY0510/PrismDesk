from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "Prism Desk"
    APP_ENV: str = "development"

    DATABASE_HOST: str = "127.0.0.1"
    DATABASE_PORT: int = 5432
    DATABASE_NAME: str = "prism_desk"
    DATABASE_USER: str = "prism_user"
    DATABASE_PASSWORD: str

    # SQL echo logs statement parameters (hashes, tokens), so it is
    # opt-in and never tied to APP_ENV.
    SQL_ECHO: bool = False

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    SESSION_EXPIRE_HOURS: int = 8
    SESSION_INACTIVITY_MINUTES: int = 30
    SESSION_COOKIE_NAME: str = "prism_session"
    CSRF_HEADER_NAME: str = "X-CSRF-Token"
    COOKIE_SECURE: bool = False

    # Comma-separated list of browser origins allowed to call the API.
    CORS_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173"

    # Rate limiting for sensitive endpoints (requests per window per IP).
    RATE_LIMIT_ENABLED: bool = True
    LOGIN_RATE_LIMIT: int = 10
    REGISTER_RATE_LIMIT: int = 5
    RATE_LIMIT_WINDOW_SECONDS: int = 300

    # Project retention before permanent deletion is allowed.
    PROJECT_DELETE_RETENTION_DAYS: int = 90

    # Public base URL of the frontend (used for OAuth redirects).
    FRONTEND_BASE_URL: str = "http://localhost:5173"

    # Discord integration. All optional: the app works without them.
    DISCORD_CLIENT_ID: str = ""
    DISCORD_CLIENT_SECRET: str = ""
    DISCORD_REDIRECT_URI: str = ""
    DISCORD_BOT_TOKEN: str = ""
    DISCORD_ANNOUNCEMENT_CHANNEL_ID: str = ""
    # Channel where new papers are posted; each post gets a discussion thread.
    DISCORD_RESEARCH_CHANNEL_ID: str = ""
    # Server (guild) ID, used to build "Discuss on Discord" links.
    DISCORD_GUILD_ID: str = ""

    # Used to fetch paper metadata for a DOI (doi.org content negotiation).
    DOI_LOOKUP_URL: str = "https://doi.org"
    DISCORD_API_BASE_URL: str = "https://discord.com/api/v10"

    # Notification worker.
    NOTIFICATION_MAX_ATTEMPTS: int = 5
    NOTIFICATION_RETRY_BASE_SECONDS: int = 60
    NOTIFICATION_RETRY_MAX_SECONDS: int = 3600
    NOTIFICATION_POLL_SECONDS: int = 15
    TASK_REMINDER_HOURS: int = 24
    CONFERENCE_REMINDER_DAYS: int = 7

    LOG_LEVEL: str = "INFO"
    API_DOCS_ENABLED: bool = True

    @field_validator("APP_ENV")
    @classmethod
    def normalize_env(cls, value: str) -> str:
        return value.strip().lower()

    @property
    def is_production(self) -> bool:
        return self.APP_ENV == "production"

    @property
    def cookie_secure(self) -> bool:
        # Production always uses Secure cookies regardless of COOKIE_SECURE.
        return self.COOKIE_SECURE or self.is_production

    @property
    def cors_origin_list(self) -> list[str]:
        return [
            origin.strip()
            for origin in self.CORS_ORIGINS.split(",")
            if origin.strip()
        ]

    @property
    def discord_oauth_configured(self) -> bool:
        return bool(
            self.DISCORD_CLIENT_ID
            and self.DISCORD_CLIENT_SECRET
            and self.DISCORD_REDIRECT_URI
        )

    @property
    def discord_bot_configured(self) -> bool:
        return bool(self.DISCORD_BOT_TOKEN)


settings = Settings()
