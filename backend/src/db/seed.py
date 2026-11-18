"""首次启动初始化数据：菜单、管理员角色、示例文档。

已有数据库再次启动时，会增量补齐缺失的内置菜单并同步到管理员角色，
避免新增页面因种子只执行一次而永久不可见。
"""

from __future__ import annotations

import logging
import secrets
from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from src.core.config import Settings
from src.core.security import hash_password
from src.db.session import DatabaseSession
from src.models.document import Document, DocumentVersion
from src.models.system import SysConfig
from src.models.user import Menu, Role, User

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class MenuSpec:
    """内置菜单声明，parent 以菜单 name 引用，避免依赖数据库自增值。"""

    name: str
    title: str
    path: str
    component: str
    icon: str = ""
    sort: int = 0
    parent: str | None = None
    redirect: str | None = None
    permission_code: str | None = None
    hidden: bool = False


BUILTIN_MENUS: tuple[MenuSpec, ...] = (
    MenuSpec("Dashboard", "仪表盘", "/dashboard", "#", "mdi:view-dashboard", 1, redirect="/dashboard/analysis"),
    MenuSpec("Analysis", "仪表盘", "analysis", "views/Dashboard/Analysis", "mdi:view-dashboard", 1, "Dashboard"),
    MenuSpec(
        "Document", "文档管理", "/document", "#", "mdi:file-document-multiple", 2,
        redirect="/document/list", permission_code="document:view",
    ),
    MenuSpec(
        "DocumentList", "文档列表", "list", "views/Document/DocumentList",
        "mdi:format-list-bulleted", 1, "Document", permission_code="document:view",
    ),
    # 系统管理：用户、角色、权限
    MenuSpec("System", "系统管理", "/system", "#", "mdi:cog", 3, redirect="/system/user", permission_code="system:view"),
    MenuSpec("SystemUser", "用户管理", "user", "views/System/User", "mdi:account", 1, "System", permission_code="user:view"),
    MenuSpec("SystemRole", "角色管理", "role", "views/System/Role", "mdi:account-circle-outline", 2, "System"),
    MenuSpec("SystemPermission", "权限管理", "permission", "views/System/Permission", "mdi:key", 3, "System"),
    # 审计日志
    MenuSpec("Audit", "审计日志", "/audit", "#", "mdi:file-document-outline", 4, redirect="/audit/operation-log"),
    MenuSpec("AuditOperationLog", "操作日志", "operation-log", "views/Audit/OperationLog", "mdi:history", 1, "Audit"),
    MenuSpec("AuditLoginLog", "登录日志", "login-log", "views/Audit/LoginLog", "mdi:login", 2, "Audit"),
    # 配置管理
    MenuSpec("Config", "配置管理", "/config", "#", "mdi:tune", 5, redirect="/config/param"),
    MenuSpec("ConfigParam", "参数管理", "param", "views/Config/Param", "mdi:tune", 1, "Config"),
    MenuSpec("ConfigJob", "定时任务", "job", "views/Config/Job", "mdi:clock-outline", 2, "Config"),
    MenuSpec("ConfigApi", "系统接口", "api", "views/Config/Api", "mdi:api", 3, "Config"),
    # 监控管理
    MenuSpec("Monitor", "监控管理", "/monitor", "#", "mdi:monitor", 6, redirect="/monitor/service"),
    MenuSpec("MonitorService", "服务监控", "service", "views/Monitor/Service", "mdi:monitor", 1, "Monitor"),
    MenuSpec("MonitorOnline", "在线用户", "online", "views/Monitor/Online", "mdi:account-group", 2, "Monitor"),
    MenuSpec("MonitorFile", "文件管理", "file", "views/Monitor/File", "mdi:folder", 3, "Monitor"),
    MenuSpec("MonitorRedis", "Redis 监控", "redis", "views/Monitor/Redis", "mdi:database", 4, "Monitor"),
    MenuSpec("MonitorRabbitMQ", "RabbitMQ 监控", "rabbitmq", "views/Monitor/RabbitMQ", "mdi:message-text", 5, "Monitor"),
    # 通知公告（独立顶级菜单，子项承载页面以保证套用 Layout 框架）
    MenuSpec("Notice", "通知公告", "/notice", "#", "mdi:bullhorn", 7, redirect="/notice/list"),
    MenuSpec("NoticeList", "通知公告", "list", "views/Notice/List", "mdi:bullhorn", 1, "Notice"),
    # 组织管理
    MenuSpec("Organization", "组织管理", "/organization", "#", "mdi:office-building", 8, redirect="/organization/org"),
    MenuSpec("OrgManage", "机构管理", "org", "views/Organization/Org", "mdi:domain", 1, "Organization"),
    MenuSpec("DeptManage", "部门管理", "dept", "views/Organization/Dept", "mdi:account-group", 2, "Organization"),
)

# 操作权限项：以隐藏菜单承载，挂在对应导航菜单下，仅用于角色授权，不生成前端路由。
# 权限模型分两层：
#   - 导航菜单（上表 BUILTIN_MENUS）：控制用户"看得到"哪些页面，permission_code 用 *:view（当前仅供前端标识）；
#   - 粗粒度模块权限（*:write）：兼容旧角色授权，拥有即蕴含该模块全部细粒度按钮权限（见 core.permissions）；
#   - 细粒度按钮权限（resource:action）：对应页面上一个具体写按钮，是后端接口实际校验的单元。
# 全部作为父菜单子节点，在角色授权树中按父子层级自然展示。
ACTION_PERMISSIONS: tuple[MenuSpec, ...] = (
    # 文档管理：粗码 + 逐个按钮
    MenuSpec(
        "DocumentWritePermission", "文档全部权限", "document-write-permission", "##",
        "mdi:pencil", 90, "Document", permission_code="document:write", hidden=True,
    ),
    MenuSpec(
        "DocumentCreate", "新建文档", "document-create", "##",
        "mdi:file-plus", 91, "Document", permission_code="document:create", hidden=True,
    ),
    MenuSpec(
        "DocumentUpload", "上传文件", "document-upload", "##",
        "mdi:upload", 92, "Document", permission_code="document:upload", hidden=True,
    ),
    MenuSpec(
        "DocumentUpdate", "编辑文档", "document-update", "##",
        "mdi:pencil", 93, "Document", permission_code="document:update", hidden=True,
    ),
    MenuSpec(
        "DocumentDelete", "删除文档", "document-delete", "##",
        "mdi:delete", 94, "Document", permission_code="document:delete", hidden=True,
    ),
    MenuSpec(
        "DocumentRestore", "恢复文档", "document-restore", "##",
        "mdi:restore", 95, "Document", permission_code="document:restore", hidden=True,
    ),
    MenuSpec(
        "DocumentShare", "分享文档", "document-share", "##",
        "mdi:link", 96, "Document", permission_code="document:share", hidden=True,
    ),
    # 用户管理
    MenuSpec(
        "UserWritePermission", "用户全部权限", "user-write-permission", "##",
        "mdi:account-key", 90, "SystemUser", permission_code="user:write", hidden=True,
    ),
    MenuSpec(
        "UserCreate", "新增用户", "user-create", "##",
        "mdi:account-plus", 91, "SystemUser", permission_code="user:create", hidden=True,
    ),
    MenuSpec(
        "UserUpdate", "编辑用户", "user-update", "##",
        "mdi:account-cog", 92, "SystemUser", permission_code="user:update", hidden=True,
    ),
    MenuSpec(
        "UserActivate", "激活停用用户", "user-activate", "##",
        "mdi:check-circle", 93, "SystemUser", permission_code="user:activate", hidden=True,
    ),
    MenuSpec(
        "UserDelete", "删除用户", "user-delete", "##",
        "mdi:delete-outline", 94, "SystemUser", permission_code="user:delete", hidden=True,
    ),
    # 角色管理
    MenuSpec(
        "RoleCreate", "新增角色", "role-create", "##",
        "mdi:plus", 91, "SystemRole", permission_code="role:create", hidden=True,
    ),
    MenuSpec(
        "RoleUpdate", "编辑角色", "role-update", "##",
        "mdi:pencil", 92, "SystemRole", permission_code="role:update", hidden=True,
    ),
    MenuSpec(
        "RoleDelete", "删除角色", "role-delete", "##",
        "mdi:delete", 93, "SystemRole", permission_code="role:delete", hidden=True,
    ),
    # 权限管理
    MenuSpec(
        "PermissionCreate", "新增权限", "permission-create", "##",
        "mdi:plus", 91, "SystemPermission", permission_code="permission:create", hidden=True,
    ),
    MenuSpec(
        "PermissionUpdate", "编辑权限", "permission-update", "##",
        "mdi:pencil", 92, "SystemPermission", permission_code="permission:update", hidden=True,
    ),
    MenuSpec(
        "PermissionDelete", "删除权限", "permission-delete", "##",
        "mdi:delete", 93, "SystemPermission", permission_code="permission:delete", hidden=True,
    ),
    # 系统管理（参数/公告/定时任务/组织/部门）
    MenuSpec(
        "SystemWritePermission", "系统全部权限", "system-write-permission", "##",
        "mdi:shield-check", 90, "System", permission_code="system:write", hidden=True,
    ),
    MenuSpec(
        "ConfigCreate", "新增参数", "config-create", "##",
        "mdi:plus", 91, "ConfigParam", permission_code="config:create", hidden=True,
    ),
    MenuSpec(
        "ConfigUpdate", "编辑参数", "config-update", "##",
        "mdi:pencil", 92, "ConfigParam", permission_code="config:update", hidden=True,
    ),
    MenuSpec(
        "ConfigDelete", "删除参数", "config-delete", "##",
        "mdi:delete", 93, "ConfigParam", permission_code="config:delete", hidden=True,
    ),
    MenuSpec(
        "NoticeCreate", "新增公告", "notice-create", "##",
        "mdi:plus", 91, "NoticeList", permission_code="notice:create", hidden=True,
    ),
    MenuSpec(
        "NoticeUpdate", "编辑公告", "notice-update", "##",
        "mdi:pencil", 92, "NoticeList", permission_code="notice:update", hidden=True,
    ),
    MenuSpec(
        "NoticeDelete", "删除公告", "notice-delete", "##",
        "mdi:delete", 93, "NoticeList", permission_code="notice:delete", hidden=True,
    ),
    MenuSpec(
        "JobCreate", "新增任务", "job-create", "##",
        "mdi:plus", 91, "ConfigJob", permission_code="job:create", hidden=True,
    ),
    MenuSpec(
        "JobUpdate", "编辑任务", "job-update", "##",
        "mdi:pencil", 92, "ConfigJob", permission_code="job:update", hidden=True,
    ),
    MenuSpec(
        "JobRun", "执行任务", "job-run", "##",
        "mdi:play", 93, "ConfigJob", permission_code="job:run", hidden=True,
    ),
    MenuSpec(
        "JobDelete", "删除任务", "job-delete", "##",
        "mdi:delete", 94, "ConfigJob", permission_code="job:delete", hidden=True,
    ),
    MenuSpec(
        "OrgCreate", "新增机构", "org-create", "##",
        "mdi:plus", 91, "OrgManage", permission_code="org:create", hidden=True,
    ),
    MenuSpec(
        "OrgUpdate", "编辑机构", "org-update", "##",
        "mdi:pencil", 92, "OrgManage", permission_code="org:update", hidden=True,
    ),
    MenuSpec(
        "OrgDelete", "删除机构", "org-delete", "##",
        "mdi:delete", 93, "OrgManage", permission_code="org:delete", hidden=True,
    ),
    MenuSpec(
        "DeptCreate", "新增部门", "dept-create", "##",
        "mdi:plus", 91, "DeptManage", permission_code="dept:create", hidden=True,
    ),
    MenuSpec(
        "DeptUpdate", "编辑部门", "dept-update", "##",
        "mdi:pencil", 92, "DeptManage", permission_code="dept:update", hidden=True,
    ),
    MenuSpec(
        "DeptDelete", "删除部门", "dept-delete", "##",
        "mdi:delete", 93, "DeptManage", permission_code="dept:delete", hidden=True,
    ),
)

# 全部内置权限节点（导航菜单 + 操作权限），用于种子同步与 admin 全量授权。
BUILTIN_PERMISSION_NODES: tuple[MenuSpec, ...] = BUILTIN_MENUS + ACTION_PERMISSIONS

# 旧版系统管理下平铺的菜单，重划结构后需要从已有库中清除。
LEGACY_MENU_NAMES = frozenset(
    {
        "SystemConfig", "SystemNotice", "SystemOperationLog", "SystemLoginLog",
        "SystemOnline", "SystemMonitor", "SystemFile", "SystemApi", "SystemJob",
    }
)


async def ensure_builtin_menus(session: DatabaseSession) -> dict[str, Menu]:
    """增量同步内置菜单：补齐缺失、更新已有定义、清除废弃菜单。"""
    existing = {
        menu.name: menu
        for menu in (await session.execute(select(Menu))).scalars().all()
    }
    result = dict(existing)

    for name in LEGACY_MENU_NAMES:
        legacy = result.pop(name, None)
        if legacy is not None:
            session.delete(legacy)

    # 父菜单先于子菜单处理，保证 parent_id 能正确解析。
    ordered = sorted(BUILTIN_PERMISSION_NODES, key=lambda spec: (spec.parent is not None, spec.sort))
    for spec in ordered:
        parent = result.get(spec.parent) if spec.parent else None
        menu = result.get(spec.name)
        if menu is None:
            menu = Menu(
                name=spec.name, title=spec.title, path=spec.path,
                component=spec.component, icon=spec.icon, redirect=spec.redirect,
                sort=spec.sort, parent_id=parent.id if parent else None,
                permission_code=spec.permission_code, hidden=spec.hidden,
            )
            session.add(menu)
            await session.flush()
            result[spec.name] = menu
            continue
        # 内置菜单重划后，把已有记录同步到最新定义。
        menu.title = spec.title
        menu.path = spec.path
        menu.component = spec.component
        menu.icon = spec.icon
        menu.redirect = spec.redirect
        menu.sort = spec.sort
        menu.parent_id = parent.id if parent else None
        menu.permission_code = spec.permission_code
        menu.hidden = spec.hidden
    return result


async def ensure_builtin_roles(session: DatabaseSession, menus: dict[str, Menu]) -> dict[str, Role]:
    """幂等创建内置角色（admin 全权限、user 文档权限），已有角色同步菜单。

    user 角色是注册用户的默认角色，授予文档导航与文档写权限；写操作的数据范围
    由 owner_id + data_scope 限制，仅能操作自己的文档。
    """
    # user 角色：文档导航 + 文档写权限。数据隔离（owner_id + data_scope）保证
    # 其只能增删改自己的文档，授予 document:write 不会越权。
    user_menu_names = {
        "Dashboard", "Analysis", "Document", "DocumentList", "DocumentWritePermission"
    }
    specs = (
        ("admin", "超级管理员", "系统内置管理员角色", [menus[spec.name] for spec in BUILTIN_PERMISSION_NODES]),
        (
            "user", "普通用户", "注册用户默认角色",
            [menus[spec.name] for spec in BUILTIN_PERMISSION_NODES if spec.name in user_menu_names],
        ),
    )
    existing = {
        role.code: role
        for role in (await session.execute(select(Role))).scalars().all()
    }
    result = dict(existing)
    for code, name, description, role_menus in specs:
        role = result.get(code)
        if role is None:
            role = Role(code=code, name=name, description=description, menus=list(role_menus))
            session.add(role)
            result[code] = role
        else:
            # 仅补齐缺失的内置菜单，保留用户额外授予的自定义菜单。
            role.name = name
            role.description = description
            existing_ids = {menu.id for menu in role.menus}
            for menu in role_menus:
                if menu.id not in existing_ids:
                    role.menus.append(menu)
    await session.flush()
    return result


async def ensure_builtin_configs(session: DatabaseSession) -> None:
    """幂等补齐内置系统参数，老库升级也能获得新增开关。"""
    builtin = {
        "watermark.enabled": ("1", "水印开关", "1 开启 / 0 关闭全局水印"),
    }
    existing = {
        item.key: item
        for item in (await session.execute(select(SysConfig))).scalars().all()
    }
    for key, (value, name, remark) in builtin.items():
        if key not in existing:
            session.add(SysConfig(key=key, value=value, name=name, remark=remark))
    await session.flush()


async def seed_initial_data(session: DatabaseSession, settings: Settings) -> None:
    """初始化内置菜单与角色；仅在用户表为空时创建管理员与示例数据。

    初始管理员口令来自环境变量，开发环境未配置时随机生成并打印一次，
    避免在代码中硬编码任何口令。
    """
    menus = await ensure_builtin_menus(session)
    roles = await ensure_builtin_roles(session, menus)
    await ensure_builtin_configs(session)
    user_count = (await session.execute(select(func.count()).select_from(User))).scalar_one()

    if user_count:
        # 已有库：内置角色与参数由对应 ensure 函数统一同步。
        await session.commit()
        return

    role = roles["admin"]

    password = settings.initial_admin_password or secrets.token_urlsafe(12)
    admin = User(
        username="admin",
        password_hash=hash_password(password),
        real_name="系统管理员",
        status=1,
        is_superuser=True,
        roles=[role],
    )
    session.add(admin)
    await session.flush()

    samples = [
        Document(
            title="在线文档系统使用说明",
            description="介绍系统的登录、文档上传与版本管理流程",
            owner_id=admin.id,
        ),
        Document(
            title="项目开发规范",
            description="前后端交互契约、命名与注释规范",
            owner_id=admin.id,
        ),
    ]
    session.add_all(samples)
    await session.flush()
    session.add_all(
        [
            DocumentVersion(
                document_id=item.id,
                version_no=1,
                change_log="创建文档",
                created_by=admin.id,
            )
            for item in samples
        ]
    )
    await session.commit()

    if settings.initial_admin_password:
        logger.info("已使用环境变量提供的口令创建初始管理员 admin")
    else:
        logger.warning("初始管理员 admin 的随机口令（仅显示一次）: %s", password)
