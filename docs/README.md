# 在线文档管理系统

在线文档管理系统采用前后端分离架构：Vue 3 (vue-element-plus-admin) 管理后台 + FastAPI 服务。后端已完成统一响应契约、认证、文档管理主链路、基础设施抽象、自动化测试、工程文档，以及基于 `ChristopherVR/ooxml` 的协作服务（Yjs relay）与分享接口。前端当前为 `vue-element-plus-admin` 脚手架，登录/文档业务与 ooxml 编辑器接入待实施（见 `docs/frontend/overview.md`）。

## 技术栈

| 层次 | 选型 |
| --- | --- |
| 前端 | Vue 3、TypeScript、Vite、Element Plus、`vue-element-plus-admin` 3.x（pnpm monorepo：`apps/admin` + `packages/*`）；ooxml 编辑器待用其 Vue 绑定重新接入 |
| 后端 | FastAPI、Pydantic V2、SQLAlchemy 2.0 Async、Alembic、PyJWT、bcrypt |
| 数据库 | 开发默认 SQLite(aiosqlite)；生产支持达梦 8（官方 `dmSQLAlchemy` 方言，同步驱动经线程池门面适配，见 `docs/backend/database.md`） |
| 基础设施 | Redis（缓存）、RabbitMQ（领域事件）、RustFS（S3 兼容对象存储），未配置时自动降级为本地实现 |

## 目录结构

```text
OnlineDocuments/
├── backend/                 # FastAPI 后端
│   ├── src/
│   │   ├── core/            # 配置、统一响应、异常、安全、依赖注入、缓存、事件
│   │   ├── db/              # ORM 基类、异步会话、初始化数据
│   │   ├── models/          # SQLAlchemy 模型
│   │   ├── schemas/         # Pydantic 请求/响应 DTO
│   │   ├── repositories/    # 数据访问层
│   │   ├── services/        # 业务逻辑与事务
│   │   ├── routers/v1/      # 路由层
│   │   └── main.py          # 应用入口
│   ├── alembic/             # 数据库迁移
│   ├── tests/               # 后端自动化测试
│   ├── requirements.txt
│   └── .env.example
├── frontend/                # vue-element-plus-admin 管理后台（pnpm monorepo）
│   ├── apps/admin/          # 主应用（api/、router/、store/、views/ 等）
│   └── packages/            # components / hooks / request 等内部包
├── docs/                    # 项目文档（本目录）
└── .gitignore
```

## 快速开始

```bash
# 1. 后端（Windows PowerShell 示例）
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
uvicorn src.main:app --reload --port 8000

# 2. 前端（另开终端，需要 pnpm >= 9.5 与 Node 20/22/24）
cd frontend
pnpm install --registry=https://registry.npmjs.org
pnpm dev:admin
```

- 前端开发代理需在 `apps/admin` 的 Vite 配置中把 `/api/*` 转发到 `http://127.0.0.1:8000` 并剥掉 `/api` 前缀（脚手架默认未配置，接入时补上）。
- Swagger 文档：`http://127.0.0.1:8000/docs`；健康检查：`http://127.0.0.1:8000/health`。
- 初始管理员用户名为 `admin`。口令来自环境变量 `INITIAL_ADMIN_PASSWORD`；未配置时后端会随机生成，并在启动日志中以 WARNING 输出一次。生产环境强制要求显式配置该变量与 `JWT_SECRET_KEY`。
- 前端登录页为脚手架默认实现，接入后端认证时再对接真实口令流程。

## 当前已实现的能力

- 用户管理：登录、JWT 鉴权、用户资料与权限、用户 CRUD、停用/激活、登录日志与操作日志；支持自助注册（`/v1/auth/register`），注册用户默认绑定内置 `user` 角色且状态为「待激活」（2），需管理员激活（`/v1/users/{id}/activate`）后方可登录。内置角色 `admin`/`user` 均不可删除。
- 系统管理：用户、角色与权限（菜单）管理；审计日志、配置管理、监控管理、通知公告、组织管理（机构/部门）分属独立顶级菜单。
- 前端图标统一由 `src/icons.ts` 目录管理，权限管理中的图标字段可通过可搜索的图标选择器选取。
- 用户管理：用户 CRUD 与数据范围配置（`all` 全部 / `self` 仅本人 / `dept` 本部门）；角色可勾选菜单树授权。
- 文档管理：文档元数据 CRUD、版本历史、文件上传、下载、软删除与恢复、分页检索；操作栏保留编辑/分享，其余操作收入"更多"菜单。
- 数据隔离：文档、用户、日志、仪表盘统计与协作鉴权均按当前用户的数据范围过滤；超级管理员可见全库数据。
- 在线编辑：Word/Excel/PPT/Visio 均使用 `ooxml` 生态的 Vue 查看器编辑。Visio 采用 `visio-vue-viewer`（`VisioViewer`），提供 Visio 风格功能区、图形窗口、页面标签与画布拖拽式增删改，保存时通过 `exportVsdx()` 写回 VSDX 新版本。
- 实时协作：前端 Word/Excel/PPT/Visio 均已接入协作，`VisioViewer` 的 `collaboration` 选项携带房间号、服务地址、令牌与协作者身份；后端 `WS /v1/collaboration/ws/{room_id}` 负责 Yjs 消息广播与历史回放，房间按“文档+格式”隔离（含 `vsdx`，单 worker）。协作者光标与选区由 ooxml 在线状态层同步。
- 文档分享：后端 `/v1/shares` 系列接口已实现（公开链接/指定用户、read/write 权限、过期与撤销）；前端分享界面待接入。

功能清单中其余模块（部门/岗位/字典、定时任务、文档审核/导出/预览/转换、在线用户等）已在分层架构与数据模型中预留扩展位置，尚未实现具体接口。

## 验证命令

```bash
cd backend && python -m pytest -q          # 后端测试
cd frontend && pnpm typecheck              # 前端类型检查
cd frontend && pnpm build:admin            # 前端生产构建
```

## 文档索引

- `docs/permissions.md`：权限模型（导航菜单/操作权限、内置角色、权限码与接口、前端联动）
- `docs/backend/overview.md`：后端分层架构与运行方式
- `docs/backend/api-contract.md`：接口契约、错误码、时间格式与接口清单
- `docs/backend/database.md`：达梦 8 接入、迁移与初始化数据
- `docs/frontend/overview.md`：前端说明（随新框架接入后更新）
- `docs/development.md`：开发流程、规范与后续路线
