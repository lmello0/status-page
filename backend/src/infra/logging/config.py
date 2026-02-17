import logging
import sys
from typing import Callable, Literal

import structlog
from structlog.types import EventDict

OFF_LOG_LEVEL = logging.CRITICAL + 1


def add_service_context(service_name: str, environment: str) -> Callable:
    def processor(logger: structlog.BoundLogger, method_name: str, event_dict: dict):
        event_dict["service"] = service_name
        event_dict["environment"] = environment

        return event_dict

    return processor


def drop_color_message_key(_, __, event_dict: EventDict) -> EventDict:
    event_dict.pop("color_message", None)
    return event_dict


def _normalize_log_level(level: str | int) -> int:
    if isinstance(level, int):
        return level

    normalized_level = level.strip().upper()

    if normalized_level == "OFF":
        return OFF_LOG_LEVEL

    level_map = logging.getLevelNamesMapping()

    if normalized_level in level_map:
        return level_map[normalized_level]

    raise ValueError(
        "Invalid log level '%s'. Supported values are DEBUG, INFO, WARNING, ERROR, CRITICAL, OFF, or an integer."
        % level
    )


def _apply_library_log_levels(library_log_levels: dict[str, str | int]) -> None:
    for logger_name, configured_level in library_log_levels.items():
        if not logger_name or not logger_name.strip():
            raise ValueError("Logger name in library_log_levels cannot be empty.")

        logger = logging.getLogger(logger_name)
        normalized_level = _normalize_log_level(configured_level)

        logger.setLevel(normalized_level)

        if normalized_level == OFF_LOG_LEVEL:
            logger.disabled = True
            logger.propagate = False
            logger.handlers.clear()
            continue

        logger.disabled = False
        logger.propagate = True


def configure_logging(
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
    service_name: str,
    environment: Literal["loc", "dev", "pre", "pro"],
    json_logs: bool,
    library_log_levels: dict[str, str | int] | None = None,
) -> None:
    shared_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.stdlib.ExtraAdder(),
        drop_color_message_key,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        add_service_context(service_name, environment),
    ]

    if json_logs:
        shared_processors.append(structlog.processors.format_exc_info)

    structlog.configure(
        processors=shared_processors + [structlog.stdlib.ProcessorFormatter.wrap_for_formatter],
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    log_renderer = structlog.dev.ConsoleRenderer()
    if json_logs:
        log_renderer = structlog.processors.JSONRenderer()

    formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=shared_processors,
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            log_renderer,
        ],
    )

    handler = logging.StreamHandler()
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(log_level.upper())

    for _log in ["uvicorn", "uvicorn.error"]:
        logging.getLogger(_log).handlers.clear()
        logging.getLogger(_log).propagate = True

    logging.getLogger("uvicorn.access").handlers.clear()
    logging.getLogger("uvicorn.access").propagate = False

    if library_log_levels:
        _apply_library_log_levels(library_log_levels)

    def handle_exception(exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return

        root_logger.error("Uncaught exception", exc_info=(exc_type, exc_value, exc_traceback))

    sys.excepthook = handle_exception
