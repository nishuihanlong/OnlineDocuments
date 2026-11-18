# 开发指南

## 本地开发流程

```bash
# 终端 1：后端
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
uvicorn src.main:app --reload --port 8000

# 终端 2：前端
cd frontend
pnpm install
pnpm dev:admin
```

后端 Swagger 位于 `http://127.0.0.1:8000/docs`。前端页面尚未对接后端认证，接入完成后使用 `admin` 与启动日志中的初始口令登录。

## 日常验证

```bash
cd backend && python -m pytest -q
cd frontend && pnpm typecheck:admin && pnpm build:admin
```

## 代码规范

- **后端**：PEP 8；公共函数、类与复杂逻辑必须写注释；所有函数参数与返回值带类型提示；严格分层，路由层不写业务逻辑；入参/出参必须定义 Pydantic 模型。
- **前端**：Vue 3 Composition API + TypeScript；组件文件名 PascalCase；Props/Emits 使用 `defineProps` / `defineEmits` 类型定义；模板不写复杂逻辑，复杂计算用 `computed`，副作用用 `watch` / `onMounted`；Store 通过 Actions 更新；数据访问使用可选链判空；样式使用 Scoped CSS 或 CSS Modules，优先使用实用类。
- **命名**：变量/函数 camelCase，类/组件 PascalCase，常量 UPPER_SNAKE_CASE（Python 遵循 snake_case）。
- **敏感信息**：密钥、口令、连接凭据只能来自环境变量，禁止硬编码或提交 `.env`。
- **时间**：所有时间字段统一使用 UTC ISO 8601，例如 `2026-11-13T10:00:00Z`。
- **接口**：统一返回 `{ code, message, data }`，`code` 使用标准 HTTP 状态码，前端按 `code` 判断业务结果。

## 版本控制

仓库当前尚未初始化 Git。初始化后提交信息遵循 Conventional Commits：

```text
feat: add document version management
fix: resolve date format error
docs: add api contract
```

`.gitignore` 已排除 `.env`、`*.db`、`storage/`、`node_modules/`、构建产物与 IDE 配置；`.codebuddy/` 为项目数据目录，**不要删除**。

## 后续路线

1. 前端在 vue-element-plus-admin 上重新接入：认证与动态菜单、文档管理页、ooxml 编辑器（ooxml-ui Vue 绑定）、实时协作与分享界面（见 `docs/frontend/overview.md`）。
2. 已补齐参数、通知公告、定时任务、在线用户、日志、监控、文件与接口清单等系统管理模块；部门、岗位、字典管理仍待实施。
3. 补齐文档审核、归档、导出、导入、预览、转换与全文搜索。
4. 接入 Redis / RabbitMQ / RustFS 真实实例，替换本地降级实现；协作房间改为多 worker 共享发布订阅。
5. 增加按钮级权限、操作日志查询界面、文件上传大小限制与病毒扫描。
6. 生产环境用 Alembic 迁移替代 `init_models()`，并为大文件下载改为预签名 URL。

已完成：达梦 8 适配并在真实环境验证（见 `docs/backend/database.md`）；分享后端 `/v1/shares` 系列接口与协作 WebSocket（见 `docs/backend/api-contract.md`）。
