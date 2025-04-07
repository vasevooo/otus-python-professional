import logging
from typing import Optional
from pathlib import Path
import structlog


def setup_pre_logging() -> None:
    """Базовая настройка логгера — логируем в консоль красиво (plain text)"""
    logging.basicConfig(
        format="%(asctime)s [%(levelname)-8s] %(message)s",
        handlers=[logging.StreamHandler()],
        level=logging.INFO,
        force=True,
    )

    structlog.configure(
        processors=[
            structlog.processors.add_log_level,
            structlog.dev.ConsoleRenderer(),
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        cache_logger_on_first_use=True,
    )


def setup_logging(
    log_file_path: Optional[str] = None, log_handlers: list[logging.Handler] = []
) -> None:
    """Перенастраиваем логгер, если указан путь до файла — логируем в JSON"""
    log_handlers = []

    if log_file_path:
        log_path = Path(log_file_path).resolve()
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_handlers.append(logging.FileHandler(log_path, encoding="utf-8"))
    else:
        log_handlers.append(logging.StreamHandler())

    logging.basicConfig(
        format="%(message)s",
        handlers=log_handlers,
        level=logging.INFO,
        force=True,
    )

    structlog.configure(
        processors=[
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.add_log_level,
            structlog.processors.JSONRenderer(),
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        cache_logger_on_first_use=True,
    )
