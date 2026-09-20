from __future__ import annotations

import logging
import sys
from collections.abc import Iterable

from app.config import get_settings

LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


class SecretRedactingFilter(logging.Filter):
    """Replaces known secrets (bot token, database password) in log records."""

    def __init__(self, secrets: Iterable[str]) -> None:
        super().__init__()
        self._secrets = sorted(
            {secret for secret in secrets if secret and len(secret) >= 4},
            key=len,
            reverse=True,
        )

    def filter(self, record: logging.LogRecord) -> bool:
        try:
            message = record.getMessage()
        except Exception:  # noqa: BLE001 - logging must never raise
            return True
        redacted = message
        for secret in self._secrets:
            if secret in redacted:
                redacted = redacted.replace(secret, "***")
        if redacted != message:
            record.msg = redacted
            record.args = ()
        return True


def _collect_secrets() -> list[str]:
    settings = get_settings()
    secrets = [settings.bot_token]
    for raw_url in (settings.database_url, settings.direct_url):
        if "://" not in raw_url:
            continue
        without_scheme = raw_url.split("://", 1)[1]
        credentials = without_scheme.rsplit("@", 1)[0]
        if ":" in credentials:
            password = credentials.rsplit(":", 1)[1].split("?", 1)[0]
            secrets.append(password)
    return secrets


def setup_logging(level: str = "INFO") -> None:
    root = logging.getLogger()
    root.setLevel(level)

    for handler in list(root.handlers):
        root.removeHandler(handler)

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT))
    handler.addFilter(SecretRedactingFilter(_collect_secrets()))
    root.addHandler(handler)

    logging.getLogger("aiogram.event").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
