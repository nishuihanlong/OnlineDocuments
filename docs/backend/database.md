# 数据库、迁移与初始化数据

## 当前状态

| 环境 | 配置 | 说明 |
| --- | --- | --- |
| 开发 / 测试 | `sqlite+aiosqlite:///./online_documents.db` | 原生异步引擎，开箱即用；测试使用 `:memory:` + `StaticPool` |
| 生产目标 | 达梦 8 | 官方 `dmSQLAlchemy` 方言。**已验证可用**：同步 `dm+dmPython://`（经线程池门面适配）；原生异步 `dm+dmAsync://` 在 dmSQLAlchemy 2.0.17 + SQLAlchemy 2.0.36 下存在适配器不兼容，暂不可用 |

配置集中在 `src/core/config.py` 的 `DATABASE_URL`；引擎与会话集中在 `src/db/session.py`；迁移入口为 `alembic/env.py`。

## 达梦 8 生产接入

达梦官方提供了 SQLAlchemy 方言包 [`dmSQLAlchemy`](https://gitee.com/DamengDB/dmSQLAlchemy)（含 SQLAlchemy 2.0 分支）。根据[官方文档](https://eco.dameng.com/document/dm/zh-cn/pm/dmsqlalchemy-dialect-package.html)，达梦 8 支持**两种**接入方式，连接串前缀不同：

| 方式 | 连接串前缀 | 驱动包 | 会话模型 | 状态 |
| --- | --- | --- | --- | --- |
| 同步驱动（已验证） | `dm+dmPython://` | `dmPython` | 经 `SyncDatabaseSession` 线程池门面适配 | ✅ 可用 |
| 原生异步 | `dm+dmAsync://` | `dmAsync` | 真正的 `AsyncSession` | ⚠️ dmSQLAlchemy 2.0.17 + SQLAlchemy 2.0.36 下异步适配器报错，暂不可用 |

目前**已验证可用的是同步驱动 `dm+dmPython`**：仅需 `dmPython`，由 `SyncDatabaseSession` 把同步 `Session` 适配为异步门面（所有操作经 `asyncio.to_thread` 在线程池中执行），已实测连通达梦 8 并执行查询。原生异步 `dm+dmAsync` 因 dmSQLAlchemy 2.0.17 的异步适配器与 SQLAlchemy 2.0.36 不兼容（连接时抛 `'_connection' is read-only`），暂不可用，建议等待 dmSQLAlchemy 更新或降级 SQLAlchemy 后再评估。`build_engine()` 按 URL 前缀自动选择：`sqlite+aiosqlite` 走原生异步引擎；`dm+dmPython`、同步 `sqlite://` 等走同步引擎 + 门面。

> **版本约束（重要）**：`dmSQLAlchemy 2.0.17` 的异步扩展要求 `SQLAlchemy > 2.0.22`，但 `SQLAlchemy 2.1.x` 移除了其依赖的旧符号（`await_fallback`、`AsyncAdaptFallback_dbapi_connection`），会导致导入即崩溃；而 `2.0.36` 下其异步适配器又与新版连接对象实现冲突（`'_connection' is read-only`）。因此 `requirements.txt` 将 SQLAlchemy 锁定在 **2.0.x 区间（`>=2.0.36,<2.1`）**，同步方言 `dm+dmPython` 在此区间可正常工作。请勿升级到 2.1，除非 dmSQLAlchemy 发布兼容版本。

业务代码统一依赖 `DatabaseSession`（即 `AsyncSession | SyncDatabaseSession`），仓储与服务层只使用 `await session.execute(...)` 等统一接口，因此同一套代码同时适配原生异步驱动（开发 aiosqlite / 达梦 `dm+dmAsync`）与同步驱动（达梦 `dm+dmPython`）。`user.py` 的 `UserRepository.get_by_id` 等方法通过 `selectinload` 预加载关联，避免在线程边界之外触发惰性加载。

### 切换到达梦 8 的步骤（同步驱动，已验证）

1. 在应用服务器安装达梦客户端，并安装方言与同步驱动：
   ```bash
   pip install dmSQLAlchemy dmPython
   ```
2. 复制 `.env.example` 为 `.env`，设置（注意下方两个坑）：
   ```bash
   DATABASE_URL=dm+dmPython://<user>:<password>@<host>:<port>
   JWT_SECRET_KEY=<高熵随机值>
   INITIAL_ADMIN_PASSWORD=<高熵随机值>
   ```
3. 使用 Alembic 同步迁移分支建表（需先给数据库用户建表权限，见下方说明）：
   ```bash
   alembic revision --autogenerate -m "init schema"
   alembic upgrade head
   ```
4. 启动应用；首次启动会写入菜单、角色与管理员（仅当用户表为空）。
5. 在达梦环境运行完整测试套件，重点验证分页、事务回滚、中文与日期聚合。

> **几个必踩的坑**：
> - **密码含 `@` 必须改成 `%40`**：`@` 在 SQLAlchemy 连接串里是「凭据/主机」分隔符，密码里的 `@` 必须 URL 编码为 `%40`，否则用户/密码/主机会被解析错乱。
> - **URL 不要带末尾的 `/库名` 段**：达梦方言会把该段作为 `database=` 参数传给 `dmPython.connect`，而达梦不接受此参数（报通讯失败 -70019）。达梦连接只需 `host:port`，用户登录后默认进入同名 schema。即使使用 `dm+dmAsync` 也应去掉该段。
> - **数据库用户需建表（DDL）权限**：Alembic 会自动建一张 `alembic_version` 跟踪表，若连接用户缺权限会报 `CODE:-5515 没有执行权限`。请用 SYSDBA 执行 `GRANT RESOURCE TO <user>;`（开发期图省事也可 `GRANT DBA TO <user>;`）。
>
> 凭据只通过环境变量注入，禁止写入配置文件或代码。

## Alembic autogenerate 的达梦适配

`dmSQLAlchemy 2.0.17` 的反射实现有多处与 SQLAlchemy 2.0 / Alembic 不兼容，直接在达梦上跑 `alembic revision --autogenerate` 会接连报错。项目已把这些适配集中处理，**业务方无需额外配置**：

| 现象 | 根因 | 处理位置 |
| --- | --- | --- |
| `KeyError: 'dm'` | Alembic 未注册达梦方言的 DDL 实现 | `alembic/env.py` 的 `DamengImpl(DefaultImpl)`（`__dialect__ = "dm"`） |
| `CODE:-2007 ... [)]附近语法错误`，SQL 为 `... FROM user_tab_comments)` | 方言 `get_multi_table_comment` 在无 IN 子句时仍追加 `)` | `src/db/dameng_compat.py` 替换该方法 |
| `Argument 'dm_tablespace' is not accepted by dialect 'dm'` | 方言反射返回 `dm_tablespace` 但 `construct_arguments` 未声明 | `dameng_compat.py` 为 Table 项补 `tablespace` |
| 大量 `VARCHAR(length=Decimal('128')) → String(128)` 假类型变更 | 达梦反射长度为 `Decimal`，模型为 `int` | `dameng_compat.py` 的 `compare_dameng_type` 回调 |
| 自增 `id` 列生成无意义 `alter_column` / 或渲染 Identity 崩溃 | 达梦自增列反射为 `Identity`，模型靠 `autoincrement=True` | `env.py` 设 `compare_server_default=False`（模型未用 `server_default`，无损失） |
| 每次 autogenerate 都生成空迁移文件 | Alembic 无变更时仍写文件 | `env.py` 的 `_skip_empty_revision` 钩子（无变更则跳过） |

健康状态下对已达梦库跑 autogenerate 应**不产生任何文件**。`src/db/session.py` 与 `alembic/env.py` 均在导入期加载 `dameng_compat`，确保运行期反射与迁移期一致。

## 运行期查询的布尔比较

达梦方言不支持 SQL 标准的 `IS 1` / `IS 0` 布尔写法：`Boolean` 列用 `.is_(True)` 会被编译成 `... IS 1`，运行时报 `CODE:-2007 ... [1]附近语法错误`。

- **写法约定**：布尔过滤一律用 `== True` / `== False`（达梦编译为 `= 1` / `= 0`，SQLite 下也一致），**不要用 `is_(True)` / `is_(False)`**。
- 已修正：`MenuRepository.list_enabled()` 原用 `Menu.enabled.is_(True)`，现改为 `Menu.enabled == True`。
- 该约束适用于所有运行时 ORM 查询，与 Alembic 无关。

## 线程池门面的验证

`tests/test_sync_adapter.py` 使用内存 SQLite **同步引擎**构建 `SyncDatabaseSession`，跑通登录、动态菜单、仪表盘、文档 CRUD、上传、下载、恢复等全链路——它与达梦 8 使用完全相同的代码路径，确保同步驱动适配层可用。`pytest` 同时覆盖开发用 aiosqlite 的原生异步路径（`tests/test_*.py`）。

## 数据库表

| 前缀 | 表 | 用途 |
| --- | --- | --- |
| `sys_` | `sys_user`、`sys_role`、`sys_menu`、`sys_dept`、`sys_post`、`sys_user_role`、`sys_role_menu` | 用户、角色、菜单与组织 |
| `sys_` | `sys_operation_log`、`sys_login_log` | 审计日志 |
| `doc_` | `doc_document`、`doc_version`、`doc_share` | 文档、版本与分享 |

公共字段：`id`（自增主键）、`created_at`、`updated_at`；文档主表额外带 `deleted_at` 支持软删除与恢复。

## 迁移

```bash
cd backend
alembic revision --autogenerate -m "init schema"
alembic upgrade head
```

- `alembic/env.py` 导入 `src.models`，保证 `Base.metadata` 包含全部表。
- 开发环境启动时 `init_models()` 会自动建表；生产环境应关闭自动建表，只使用 Alembic 迁移。
- `run_migrations_online()` 已按 URL 区分：`sqlite+aiosqlite` 走异步引擎；达梦 8（`dm+dmPython`）等同步驱动走 `engine_from_config` + `do_run_migrations` 同步分支。

## 初始化数据

`src/db/seed.py` 的 `seed_initial_data()` 每次启动都会增量同步内置菜单与角色（含父子关系与权限码），仅管理员与示例文档在用户表为空时创建：

- 菜单：仪表盘、文档管理、系统管理（用户/角色/权限）、审计日志（操作/登录）、配置管理（参数/定时任务/系统接口）、监控管理（服务监控/在线用户/文件管理）、通知公告（独立顶级菜单）、组织管理（机构/部门）。
- 操作权限项：以 `hidden=True, component='##'` 的隐藏子节点承载，挂在对应导航菜单下，不下发前端路由，仅供角色授权时勾选：
  - 粗码（权限组）：`document:write`、`user:write`、`system:write`，拥有即蕴含该模块全部细码。
  - 细粒度按钮权限（实际鉴权单元）：文档 `document:create/upload/update/delete/restore/share`、用户 `user:create/update/activate/delete`、角色 `role:*`、权限 `permission:*`、参数 `config:*`、公告 `notice:*`、定时任务 `job:create/update/run/delete`、机构 `org:*`、部门 `dept:*`。
  - 完整映射见 `src/core/permissions.py` 的 `COARSE_TO_FINE` 与 `docs/permissions.md`。老库中权限节点若为顶层或缺失，`ensure_builtin_menus()` 会在重启时补齐并修正其 `parent_id`。
- 用户：默认数据范围 `self`，管理员可在用户管理中调整为 `dept` 或 `all`。
- 角色：`admin`（全量导航菜单 + 全部操作权限）、`user`（文档导航 + `document:write`）。两个内置角色均不可删除，重复启动会幂等补齐其菜单/权限。
- 用户：`admin`（超级管理员）。
- 文档：两篇示例文档及各自的 v1 版本记录。

内置角色在 `seed_initial_data()` 中通过 `ensure_builtin_roles()` 创建，位于"用户表非空即早返回"逻辑之前，因此老库升级重启后也能补建 `user` 角色与其权限。

初始口令来自 `INITIAL_ADMIN_PASSWORD`；开发环境未配置时随机生成并在启动日志输出一次，生产环境强制要求显式配置。
