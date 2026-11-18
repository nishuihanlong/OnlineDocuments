"""文档对象存储：开发环境本地磁盘，生产环境 RustFS（S3 兼容协议）。"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Protocol

from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, Field

from src.core.config import Settings, get_settings
from src.core.exceptions import BadRequestError

logger = logging.getLogger(__name__)


class StoredObject(BaseModel):
    """对象写入结果。"""

    key: str
    size: int
    content_type: str


class ObjectStorage(Protocol):
    """对象存储接口，屏蔽本地磁盘与 RustFS 差异。"""

    async def put(self, key: str, content: bytes, content_type: str) -> StoredObject: ...

    async def get(self, key: str) -> bytes: ...

    async def delete(self, key: str) -> None: ...


class LocalObjectStorage:
    """本地文件存储，仅用于开发与单机测试。"""

    def __init__(self, root_dir: str) -> None:
        self.root = Path(root_dir).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def _resolve(self, key: str) -> Path:
        """把对象键解析为本地路径，并阻止目录穿越。"""
        target = (self.root / key).resolve()
        if not target.is_relative_to(self.root):
            raise BadRequestError("非法的对象存储键")
        return target

    async def put(self, key: str, content: bytes, content_type: str) -> StoredObject:
        """写入文件并返回存储结果。"""
        def write() -> None:
            target = self._resolve(key)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)

        await run_in_threadpool(write)
        return StoredObject(key=key, size=len(content), content_type=content_type)

    async def get(self, key: str) -> bytes:
        """读取文件内容。"""
        return await run_in_threadpool(self._resolve(key).read_bytes)

    async def delete(self, key: str) -> None:
        """删除文件（不存在时忽略）。"""
        def remove() -> None:
            target = self._resolve(key)
            target.unlink(missing_ok=True)

        await run_in_threadpool(remove)


class RustfsObjectStorage:
    """RustFS 对象存储，使用 S3 兼容 API（boto3 在线程池中执行）。"""

    def __init__(self, settings: Settings) -> None:
        import boto3

        self._bucket = settings.rustfs_bucket
        self._client: Any = boto3.client(
            "s3",
            endpoint_url=settings.rustfs_endpoint,
            aws_access_key_id=settings.rustfs_access_key,
            aws_secret_access_key=settings.rustfs_secret_key,
        )

    async def put(self, key: str, content: bytes, content_type: str) -> StoredObject:
        """上传对象到 RustFS。"""
        await run_in_threadpool(
            lambda: self._client.put_object(
                Bucket=self._bucket, Key=key, Body=content, ContentType=content_type
            )
        )
        return StoredObject(key=key, size=len(content), content_type=content_type)

    async def get(self, key: str) -> bytes:
        """从 RustFS 下载对象。"""
        def read() -> bytes:
            response = self._client.get_object(Bucket=self._bucket, Key=key)
            return response["Body"].read()

        return await run_in_threadpool(read)

    async def delete(self, key: str) -> None:
        """删除 RustFS 对象。"""
        await run_in_threadpool(
            lambda: self._client.delete_object(Bucket=self._bucket, Key=key)
        )


_storage: ObjectStorage | None = None


def get_object_storage(settings: Settings | None = None) -> ObjectStorage:
    """按配置返回对象存储实现单例。"""
    global _storage
    if _storage is None:
        current = settings or get_settings()
        if current.storage_backend == "rustfs":
            if not all(
                [current.rustfs_endpoint, current.rustfs_access_key, current.rustfs_secret_key]
            ):
                raise RuntimeError("启用 RustFS 时必须配置 endpoint 与访问密钥")
            _storage = RustfsObjectStorage(current)
        else:
            _storage = LocalObjectStorage(current.storage_local_dir)
        logger.info("对象存储后端: %s", current.storage_backend)
    return _storage
