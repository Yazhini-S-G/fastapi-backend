import os
import tempfile
from pathlib import Path

from loguru import logger


def setup_logger(with_debug: bool = False) -> None:
    app_env = os.getenv("APP_ENV", "development").strip().lower()
    default_log_path = (
        Path("data/logs")
        if app_env == "production"
        else Path(tempfile.gettempdir()) / "fastapi_started_v2_logs"
    )
    log_path = Path(os.getenv("APP_LOG_DIR", str(default_log_path)))
    log_path.mkdir(parents=True, exist_ok=True)
    logger.add(
        log_path / "app.log", rotation="1 hour", compression="zip", level="DEBUG" if with_debug else "INFO"
    )
