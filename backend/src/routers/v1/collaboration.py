"""实时协作接口：Yjs WebSocket 房间连接与房间状态诊断。"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from src.core.config import get_settings
from src.core.exceptions import BizError
from src.core.response import ApiResponse
from src.db.session import get_db_session
from src.routers.deps import DbSession, SettingsDep
from src.schemas.collaboration import CollaborationRoomIn, CollaborationRoomOut
from src.services.collaboration import CollaborationService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/collaboration", tags=["实时协作"])

WSClosePolicyViolation = 1008


@router.websocket("/ws/{room_id}")
async def collaboration_socket(
    websocket: WebSocket,
    room_id: str,
    token: str = Query(default="", description="JWT 访问令牌"),
) -> None:
    """处理一个 Yjs 协作连接：鉴权、回放历史、广播消息。

    鉴权只在连接建立时用短会话完成；长连接生命周期内不持有数据库会话，
    避免同步驱动门面在连接关闭时出现事务清理竞态。
    """
    settings = get_settings()
    async with get_db_session() as session:
        service = CollaborationService(session, settings)
        try:
            principal = await service.authenticate(
                CollaborationRoomIn(room_id=room_id, token=token)
            )
        except BizError as exc:
            logger.warning("协作连接鉴权失败 room=%s: %s", room_id, exc.message)
            await websocket.close(code=WSClosePolicyViolation, reason=exc.message)
            return
        except Exception:
            logger.exception("协作连接鉴权异常 room=%s", room_id)
            await websocket.close(code=WSClosePolicyViolation, reason="鉴权失败")
            return

    await websocket.accept()
    logger.info("协作连接建立 room=%s user=%s", room_id, principal.username)

    for message in service.register(room_id, websocket):
        await websocket.send_bytes(message)

    try:
        while True:
            message = await websocket.receive_bytes()
            for target in service.relay(room_id, websocket, message):
                await target.send_bytes(message)
    except WebSocketDisconnect:
        pass
    except Exception:
        logger.exception("协作连接异常 room=%s", room_id)
    finally:
        service.unregister(room_id, websocket)
        logger.info("协作连接关闭 room=%s user=%s", room_id, principal.username)


@router.get(
    "/rooms/{room_id}",
    response_model=ApiResponse[CollaborationRoomOut],
    summary="协作房间状态",
)
async def get_room_status(
    room_id: str, session: DbSession, settings: SettingsDep
) -> ApiResponse[CollaborationRoomOut]:
    """查询房间在线人数；无需鉴权，仅暴露非敏感计数。"""
    return ApiResponse[CollaborationRoomOut](
        data=CollaborationService(session, settings).room_info(room_id)
    )
