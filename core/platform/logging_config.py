
import json
import logging
import os
from datetime import UTC, datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path

# ---------------------------------------------------------
# Configuration
# ---------------------------------------------------------

LOG_DIR = Path(__file__).resolve().parents[2] / "logs"

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

LOGGER_NAMES = [
    "platform",
    "agent_router",
    "github_agent",
    "linear_agent",
]


# ---------------------------------------------------------
# JSON Formatter
# ---------------------------------------------------------

class JSONFormatter(logging.Formatter):

    ALLOWED_CONTEXT_FIELDS = {  # noqa: RUF012
        "user_id",
        "target_user_id",
        "target_user",
        "platform",
        "provider",
        "operation",
        "status",
        "thread_id",
        "clarification_type",
        "is_supported",
    }

    def format(self, record: logging.LogRecord) -> str:

        log_data = {
            "timestamp": datetime.fromtimestamp(
                record.created, UTC
            ).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        context = {
            key: value
            for key, value in record.__dict__.items()
            if key in self.ALLOWED_CONTEXT_FIELDS
        }

        if context:
            log_data["context"] = context

        if record.exc_info:
            log_data["exception"] = self.formatException(
                record.exc_info
            )

        return json.dumps(log_data, default=str)


# ---------------------------------------------------------
# Logger Configuration
# ---------------------------------------------------------

def configure_logging() -> None:

    LOG_DIR.mkdir(parents=True, exist_ok=True)

    formatter = JSONFormatter()

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    for logger_name in LOGGER_NAMES:

        logger = logging.getLogger(logger_name)

        # Avoid duplicate handlers during reloads.
        if logger.handlers:
            logger.handlers.clear()

        logger.setLevel(LOG_LEVEL)
        logger.propagate = False

        file_handler = RotatingFileHandler(
            filename=LOG_DIR / f"{logger_name}.log",
            maxBytes=5 * 1024 * 1024,
            backupCount=3,
            encoding="utf-8",
        )

        file_handler.setFormatter(formatter)

        logger.addHandler(file_handler)
        logger.addHandler(console_handler)

    logging.getLogger("platform").info(
        "LOGGING_INITIALIZED",
        extra={"status": "success"},
    )
