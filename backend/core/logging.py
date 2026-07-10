"""Structured JSON logging configuration with structlog."""

import structlog
from structlog.processors import JSONRenderer, TimeStamper, add_log_level
from structlog.stdlib import LoggerFactory, ProcessorFormatter


def configure_logging() -> None:
    """Configure structlog for structured JSON logging."""
    structlog.configure_once(
        processors=[
            structlog.stdlib.filter_by_level,
            add_log_level,
            TimeStamper(fmt="iso"),
            structlog.dev.ConsoleRenderer()
            if __import__("sys").stdout.isatty()
            else JSONRenderer(),
        ],
        context_class=dict,
        logger_factory=LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """Get a structlog logger instance."""
    return structlog.get_logger(name or __name__)
