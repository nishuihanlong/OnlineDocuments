"""应用配置：全部通过环境变量读取，禁止在代码中硬编码密钥与口令。"""

from __future__ import annotations

import secrets
from functools import lru_cache
from typing import Literal

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

AppEnv = Literal["dev", "test", "prod"]
StorageBackend = Literal["local", "rustfs"]


class Settings(BaseSettings):
    """应用运行时配置，字段与 .env 中的环境变量一一对应。"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "OnlineDocuments"
    app_env: AppEnv = "dev"
    debug: bool = True
    api_prefix: str = "/v1"

    database_url: str = "sqlite+aiosqlite:///./online_documents.db"
    sql_echo: bool = False

    jwt_secret_key: str = ""
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 120

    initial_admin_password: str = ""
    cors_origins: list[str] = ["http://localhost:4000", "http://127.0.0.1:4000"]

    redis_url: str = ""
    rabbitmq_url: str = ""
    event_exchange: str = "online.documents.events"

    storage_backend: StorageBackend = "local"
    storage_local_dir: str = "./storage"
    rustfs_endpoint: str = ""
    rustfs_bucket: str = "documents"
    rustfs_access_key: str = ""
    rustfs_secret_key: str = ""

    @model_validator(mode="after")
    def validate_secrets(self) -> Settings:
        """开发环境自动生成临时密钥；生产环境强制要求显式配置密钥与管理员口令。"""
        if self.app_env == "prod":
            if not self.jwt_secret_key:
                raise ValueError("生产环境必须通过环境变量 JWT_SECRET_KEY 配置签名密钥")
            if not self.initial_admin_password:
                raise ValueError("生产环境必须通过环境变量 INITIAL_ADMIN_PASSWORD 配置初始管理员口令")
        if not self.jwt_secret_key:
            self.jwt_secret_key = secrets.token_urlsafe(48)
        return self

    @property
    def is_production(self) -> bool:
        """是否为生产环境。"""
        return self.app_env == "prod"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """返回进程内单例配置，避免重复解析环境变量。"""
    return Settings()
