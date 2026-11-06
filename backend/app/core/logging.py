import logging
import re

from app.core.config import settings

_SENSITIVE = re.compile(
    r"(password|token|secret|authorization|cookie)(\"?\s*[:=]\s*)(\S+)",
    re.IGNORECASE,
)


class RedactingFilter(logging.Filter):
    """Masks obvious credential values that slip into log messages."""

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = _SENSITIVE.sub(r"\1\2[REDACTED]", record.msg)
        return True


def configure_logging() -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(
        logging.Formatter(
            "%(asctime)s %(levelname)s [%(name)s] %(message)s"
        )
    )
    handler.addFilter(RedactingFilter())

    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(settings.LOG_LEVEL.upper())

    # Never let SQLAlchemy print bound parameters unless explicitly asked.
    if not settings.SQL_ECHO:
        logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
