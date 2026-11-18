"""文档分享 DTO。"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from .common import Iso8601DateTime

SharePermission = Literal["read", "write"]


class DocumentShareCreateIn(BaseModel):
    """创建分享请求。granted_user_id 为空即公开链接。"""

    document_id: int
    permission: SharePermission = "read"
    granted_user_id: int | None = None
    expires_in_hours: int | None = Field(
        default=None, ge=1, le=24 * 30, description="过期时长（小时），为空表示永久有效"
    )


class DocumentShareOut(BaseModel):
    """分享记录输出；share_path 供前端拼接免登录页面地址。"""

    id: int
    document_id: int
    permission: SharePermission
    granted_user_id: int | None = None
    granted_username: str | None = None
    is_public: bool
    token: str
    share_path: str
    expires_at: Iso8601DateTime | None = None
    revoked_at: Iso8601DateTime | None = None
    created_by: int
    created_at: Iso8601DateTime


class PublicShareOut(BaseModel):
    """公开分享访问输出：文档元信息 + 当前版本内容。"""

    token: str
    permission: SharePermission
    document_id: int
    document_title: str
    file_name: str | None = None
    mime_type: str | None = None
    size: int = 0
    content_base64: str | None = None


class PublicShareSaveIn(BaseModel):
    """公开分享编辑保存请求（JSON 内容，Base64 编码）。"""

    file_name: str = Field(min_length=1, max_length=256)
    content_base64: str = Field(min_length=1)
    mime_type: str | None = Field(default=None, max_length=128)
    change_log: str | None = Field(default=None, max_length=512)
