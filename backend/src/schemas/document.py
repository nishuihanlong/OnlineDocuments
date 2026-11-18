"""文档与版本 DTO。"""

from __future__ import annotations

from pydantic import BaseModel, Field

from .common import Iso8601DateTime, PageQuery


class DocumentQuery(PageQuery):
    """文档分页查询条件。"""

    keyword: str | None = Field(default=None, description="标题或描述模糊匹配")
    include_deleted: bool = Field(default=False, description="是否包含已删除文档")


class DocumentCreateIn(BaseModel):
    """新建文档元数据请求。"""

    title: str = Field(min_length=1, max_length=256)
    description: str | None = Field(default=None, max_length=2000)


class DocumentUpdateIn(BaseModel):
    """更新文档请求。"""

    title: str | None = Field(default=None, min_length=1, max_length=256)
    description: str | None = None


class DocumentOut(BaseModel):
    """文档详情输出。"""

    id: int
    title: str
    description: str | None = None
    owner_id: int
    current_version: int
    file_name: str | None = None
    file_size: int
    mime_type: str | None = None
    download_count: int
    created_at: Iso8601DateTime
    updated_at: Iso8601DateTime
    deleted_at: Iso8601DateTime | None = None


class DocumentVersionOut(BaseModel):
    """文档版本输出。"""

    id: int
    document_id: int
    version_no: int
    file_size: int
    change_log: str | None = None
    created_by: int
    created_at: Iso8601DateTime


class DocumentUploadOut(BaseModel):
    """文件上传结果。"""

    document_id: int
    version_no: int
    storage_key: str
    file_name: str
    file_size: int


class DocumentDownloadOut(BaseModel):
    """文件下载结果，内容为 Base64 以保证统一 JSON 响应契约。

    生产环境大文件建议改为带鉴权的 RustFS 预签名 URL。
    """

    file_name: str
    mime_type: str
    size: int
    content_base64: str
