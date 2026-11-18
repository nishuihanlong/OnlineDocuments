"""实时协作 DTO：鉴权主体与房间状态。"""

from __future__ import annotations

from pydantic import BaseModel, Field


class CollaborationRoomIn(BaseModel):
    """协作连接入参：房间号与 query token。"""

    room_id: str = Field(min_length=1, max_length=128)
    token: str = Field(min_length=1)


class CollaborationPrincipal(BaseModel):
    """协作连接的已认证用户上下文。"""

    user_id: int = Field(description="用户 ID")
    username: str = Field(description="用户名")
    display_name: str = Field(description="显示名")


class CollaborationRoomOut(BaseModel):
    """协作房间状态，供诊断与在线人数展示。"""

    room_id: str = Field(description="房间号")
    document_id: int = Field(description="文档 ID")
    doc_format: str = Field(description="文档格式")
    participant_count: int = Field(description="当前在线人数")
