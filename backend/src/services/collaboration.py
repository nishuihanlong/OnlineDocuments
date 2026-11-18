"""实时协作服务：Yjs 房间状态、鉴权与二进制消息转发。

服务端不理解 Yjs 文档语义，只做两件事：
1. 把收到的 sync/awareness 消息广播给房间内其他参与者；
2. 缓存 sync 消息，供后加入者在没有老客户端在线时回放历史内容。

房间按“文档 ID + 格式”隔离，避免 docx/xlsx/pptx/vsdx 的 Y.Doc 顶层键混用。
房间状态为进程内单例，单机部署可用；多 worker 需外接共享发布订阅后改造。
"""

from __future__ import annotations

import logging
import re
from collections import deque
from dataclasses import dataclass, field

from fastapi import WebSocket
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from src.core.config import Settings
from src.core.deps import CurrentUser
from src.core.exceptions import BadRequestError, ForbiddenError, NotFoundError, UnauthorizedError
from src.core.permissions import expand_permissions
from src.core.security import decode_access_token
from src.db.session import DatabaseSession
from src.models.user import Role, User
from src.repositories.document import DocumentRepository
from src.schemas.collaboration import CollaborationPrincipal, CollaborationRoomIn, CollaborationRoomOut

logger = logging.getLogger(__name__)

# y-websocket 线协议：type 0 为 sync（文档更新），1 为 awareness，3 为 queryAwareness。
MESSAGE_SYNC = 0
ROOM_PATTERN = re.compile(r"^doc-(\d+)-(docx|xlsx|pptx|vsdx)$")
MAX_HISTORY = 512

# 房间状态进程内共享；service 实例随请求创建，不能把状态挂在实例上。
_rooms: dict[str, _RoomState] = {}


@dataclass
class _RoomState:
    """单个协作房间的参与者与近期消息历史。"""

    participants: set[WebSocket] = field(default_factory=set)
    history: deque[bytes] = field(default_factory=lambda: deque(maxlen=MAX_HISTORY))


def _read_var_uint(data: bytes) -> tuple[int, int]:
    """读取 lib0 varUint，返回（数值，消耗的字节数）。"""
    number = 0
    multiplier = 1
    offset = 0
    while offset < len(data):
        byte = data[offset]
        offset += 1
        number += (byte & 0x7F) * multiplier
        if byte < 0x80:
            return number, offset
        multiplier *= 128
    raise BadRequestError("Yjs 消息格式错误")


class CollaborationService:
    """协作会话的鉴权与消息转发，路由层只负责 WebSocket 收发。"""

    def __init__(self, session: DatabaseSession, settings: Settings) -> None:
        self._session = session
        self._settings = settings

    async def authenticate(self, connection: CollaborationRoomIn) -> CollaborationPrincipal:
        """校验房间号、JWT 与文档访问权限，返回已认证主体。"""
        match = ROOM_PATTERN.match(connection.room_id)
        if match is None:
            raise BadRequestError("房间号格式错误")
        document_id = int(match.group(1))

        payload = decode_access_token(connection.token, self._settings)
        statement = (
            select(User)
            .options(selectinload(User.roles).selectinload(Role.menus))
            .where(User.id == int(payload.sub))
        )
        user = (await self._session.execute(statement)).scalar_one_or_none()
        if user is None:
            raise UnauthorizedError("用户不存在")
        if user.status != 1:
            raise ForbiddenError("账号已停用")

        enabled_menus = [
            menu for role in user.roles for menu in role.menus if menu.enabled
        ]
        configured = {
            menu.permission_code for menu in enabled_menus if menu.permission_code
        }
        # 与 HTTP 鉴权一致：粗码展开为细码集合。
        permissions = expand_permissions(configured)
        principal = CurrentUser(
            id=user.id,
            username=user.username,
            real_name=user.real_name,
            is_superuser=user.is_superuser,
            dept_id=user.dept_id,
            data_scope=user.data_scope,
            roles=[role.code for role in user.roles],
            permissions=sorted(permissions),
            menu_ids=sorted(menu.id for menu in enabled_menus),
        )
        document = await DocumentRepository(self._session).get_detail(document_id, principal)
        if document is None:
            raise NotFoundError("文档不存在或已删除")
        if (
            not principal.is_superuser
            and "*" not in permissions
            and "document:update" not in permissions
        ):
            raise ForbiddenError("没有文档编辑权限")

        return CollaborationPrincipal(
            user_id=user.id,
            username=user.username,
            display_name=user.real_name or user.username,
        )

    def register(self, room_id: str, websocket: WebSocket) -> list[bytes]:
        """登记参与者并返回需要回放的 sync 历史。"""
        room = _rooms.setdefault(room_id, _RoomState())
        room.participants.add(websocket)
        return list(room.history)

    def unregister(self, room_id: str, websocket: WebSocket) -> None:
        """移除参与者；房间空时释放状态，保留空房间便于诊断。"""
        room = _rooms.get(room_id)
        if room is None:
            return
        room.participants.discard(websocket)
        if not room.participants:
            room.history.clear()

    def relay(self, room_id: str, sender: WebSocket, message: bytes) -> list[WebSocket]:
        """缓存 sync 消息并返回应广播的其他参与者。"""
        room = _rooms.get(room_id)
        if room is None:
            return []
        try:
            message_type, _ = _read_var_uint(message)
        except BadRequestError:
            return []
        if message_type == MESSAGE_SYNC:
            room.history.append(message)
        return [participant for participant in room.participants if participant is not sender]

    def room_info(self, room_id: str) -> CollaborationRoomOut:
        """返回房间状态，供诊断接口使用。"""
        match = ROOM_PATTERN.match(room_id)
        room = _rooms.get(room_id)
        return CollaborationRoomOut(
            room_id=room_id,
            document_id=int(match.group(1)) if match else 0,
            doc_format=match.group(2) if match else "",
            participant_count=len(room.participants) if room else 0,
        )
