"""统一日志配置。"""

from __future__ import annotations

import logging

from src.core.config import Settings


def configure_logging(settings: Settings) -> None:
    """根据环境配置日志级别与输出格式。"""
    level = logging.DEBUG if settings.debug else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    )
    logging.getLogger("sqlalchemy.engine").setLevel(
        logging.INFO if settings.sql_echo else logging.WARNING
    )
