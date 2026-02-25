"""结构化日志配置"""

import logging

from rich.logging import RichHandler


def setup_logging(verbose: bool = False) -> None:
    """配置基于 Rich 的结构化日志"""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(rich_tracebacks=True, show_path=verbose)],
    )


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
