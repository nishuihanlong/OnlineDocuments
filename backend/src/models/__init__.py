"""ORM 模型集合；导入本模块可确保 Alembic 与建表逻辑收集全部表。"""

from src.models.document import Document, DocumentVersion
from src.models.log import LoginLog, OperationLog
from src.models.share import DocumentShare
from src.models.system import SysConfig, SysJob, SysNotice
from src.models.user import Dept, Menu, Org, Post, Role, User, role_menu, user_role

__all__ = [
    "Dept",
    "Menu",
    "Org",
    "Post",
    "Role",
    "User",
    "role_menu",
    "user_role",
    "Document",
    "DocumentVersion",
    "DocumentShare",
    "LoginLog",
    "OperationLog",
    "SysConfig",
    "SysNotice",
    "SysJob",
]
