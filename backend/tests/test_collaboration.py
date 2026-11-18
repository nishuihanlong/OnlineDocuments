"""实时协作服务测试：房间广播、历史回放与房间隔离。"""

from __future__ import annotations

from src.core.config import get_settings
from src.services.collaboration import CollaborationService

ROOM_A = "doc-1-docx"
ROOM_B = "doc-1-xlsx"
ROOM_VSDX = "doc-1-vsdx"


def _service() -> CollaborationService:
    """构造协作服务；房间状态为进程内共享，测试间自行清理。"""
    return CollaborationService(None, get_settings())


def test_relay_broadcasts_only_to_other_participants() -> None:
    """sync 消息只广播给房间内其他人，不回传发送者。"""
    service = _service()
    sender = object()
    peer = object()

    assert service.register(ROOM_A, sender) == []
    assert service.register(ROOM_A, peer) == []

    message = b"\x00\x01\x02sync-update"
    assert service.relay(ROOM_A, sender, message) == [peer]
    assert service.relay(ROOM_A, peer, message) == [sender]

    service.unregister(ROOM_A, sender)
    service.unregister(ROOM_A, peer)


def test_history_replayed_to_late_joiner() -> None:
    """后加入者应拿到此前缓存的 sync 消息。"""
    service = _service()
    first = object()
    message = b"\x00\x01\x04data"

    service.register(ROOM_A, first)
    service.relay(ROOM_A, first, message)
    late = object()
    assert service.register(ROOM_A, late) == [message]

    service.unregister(ROOM_A, first)
    service.unregister(ROOM_A, late)


def test_rooms_are_isolated_by_format() -> None:
    """同一文档不同格式的房间互不影响。"""
    service = _service()
    docx_client = object()
    xlsx_client = object()
    message = b"\x00\x01\x00x"

    service.register(ROOM_A, docx_client)
    service.register(ROOM_B, xlsx_client)
    assert service.relay(ROOM_A, docx_client, message) == []
    assert service.relay(ROOM_B, xlsx_client, message) == []

    assert service.room_info(ROOM_A).document_id == 1
    assert service.room_info(ROOM_A).doc_format == "docx"
    assert service.room_info(ROOM_B).doc_format == "xlsx"

    service.unregister(ROOM_A, docx_client)
    service.unregister(ROOM_B, xlsx_client)


def test_vsdx_room_is_supported_and_isolated() -> None:
    """Visio 房间号应通过正则校验，并与其他格式隔离。"""
    service = _service()
    vsdx_client = object()
    message = b"\x00\x01\x05v"

    assert service.register(ROOM_VSDX, vsdx_client) == []
    assert service.relay(ROOM_VSDX, vsdx_client, message) == []

    info = service.room_info(ROOM_VSDX)
    assert info.document_id == 1
    assert info.doc_format == "vsdx"

    service.unregister(ROOM_VSDX, vsdx_client)
