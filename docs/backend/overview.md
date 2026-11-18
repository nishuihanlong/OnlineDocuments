# 后端架构说明

## 分层架构

请求链路严格遵循：

```text
routers/  ->  services/  ->  repositories/  ->  models/  ->  数据库
   ^              ^                ^
   |              |                |
schemas/     事务/领域事件      SQLAlchemy Async
```

| 目录 | 职责 | 约束 |
| --- | --- | --- |
| `routers/v1/` | 接收请求、参数校验、调用 Service、包装响应 | 禁止编写业务逻辑或直接操作数据库 |
| `services/` | 业务规则、事务提交、对象存储、领域事件 | 不直接暴露 ORM 细节给路由层 |
| `repositories/` | 封装查询与 CRUD | 统一继承 `BaseRepository`，提供分页能力 |
| `models/` | SQLAlchemy 2.0 声明式模型 | 公共字段通过 Mixin 复用 |
| `schemas/` | Pydantic V2 DTO | 所有入参/出参必须有明确模型，禁止裸 `dict` |
| `core/` | 配置、响应、异常、安全、依赖注入、缓存、消息 | 所有配置来自环境变量 |

## 启动与生命周期

`src/main.py` 的 `lifespan` 依次执行：

1. `configure_logging()`：按环境设置日志级别。
2. `init_engine()`：按 `DATABASE_URL` 创建异步引擎与 `async_sessionmaker`。
3. `init_models()`：开发环境自动建表（生产应改用 Alembic）。
4. `seed_initial_data()`：仅当用户表为空时写入菜单、角色、管理员与示例文档。
5. 关闭时释放 RabbitMQ 连接与数据库连接池。

```bash
cd backend
uvicorn src.main:app --reload --port 8000
python -m pytest -q
```

## 全局机制

- **统一响应**：`core/response.py` 定义 `ApiResponse[T]`，路由统一使用 `response_model=ApiResponse[...]`。
- **异常处理**：`core/exceptions.py` 注册 `BizError`、`RequestValidationError`、`HTTPException`、`Exception` 处理器，任何错误都返回 `{code, message, data}`。
- **认证**：`Authorization: Bearer <JWT>`（兼容裸 token）；`core/deps.py` 提供 `CurrentUserDep` 与 `require_permissions()`。
- **缓存**：`get_cache()` 在配置 `REDIS_URL` 时使用 `redis.asyncio`，否则降级为进程内缓存；运行期 Redis 故障会临时回退内存缓存，不拖垮业务。`REDIS_URL` 必须是标准 URL（`redis://[:密码@]host:port/库号`，如 `redis://:pwd@127.0.0.1:6379/0`）；逗号分隔的键值格式无法被 `redis.from_url()` 解析，会静默降级为内存缓存。
  - 统一入口 `src/core/cache.py` 的 `cached_json(key, type, loader, ttl)` 负责读缓存/反序列化/回源/写缓存；key 前缀与失效集中在 `src/core/cache_keys.py`。
  - 已接入缓存的热点：用户权限上下文 `auth:ctx:{user_id}`（300s，鉴权每请求必用）、角色列表、菜单权限列表、机构/部门列表、API 路由清单（3600s）、仪表盘三项统计（60s，按数据范围+用户+日期分键）。
  - 失效保证：用户状态/资料/角色变更、角色菜单授权变更、菜单启用/权限码变更、组织部门增删改均在写路径主动清缓存；权限上下文还可通过 `delete_prefix` 全量失效。测试环境 `REDIS_URL` 为空走内存缓存，`conftest.py` 每用例 `reset_cache()` 隔离。
  - 水印开关：内置参数 `watermark.enabled`（`"1"` 开 / `"0"` 关，默认开）由 `seed` 幂等补齐、禁止删除；`GET /v1/system/public-configs` 免登录返回白名单开关（水印在登录页也渲染，故需公开），参数增删改会失效该缓存。前端参数管理页对该参数渲染开关控件，Watermark 组件按开关决定是否渲染。
- **基础设施监控**：监控管理菜单下新增「Redis 监控」「RabbitMQ 监控」只读页面（seed 自动补齐菜单）。后端 `src/services/monitor.py` 采集：`GET /v1/system/monitor/redis` 用 `INFO`/`DBSIZE` 取版本、内存、连接数、Key 数、命中率；`GET /v1/system/monitor/rabbitmq` 从 `rabbitmq_url` 推导 management HTTP API（host:15672，取 URL 中的用户名密码）取版本、交换机/队列数、消息堆积与队列明细。两者均带 30s 缓存，未配置或不可达时降级返回 `configured/reachable` 标志而非报错，前端展示「未配置/连接失败」。监控为**纯只读**，无删 Key、无发消息、无队列变更。
- **可靠性修复**：`psutil` 补入 requirements（服务监控 CPU/内存此前恒为 0）；RabbitMQ 事件发布 `publish()` 增加 try/except 降级，broker 不可用时只记日志不再拖垮文档写接口。
- **事件**：`get_event_publisher()` 在配置 `RABBITMQ_URL` 时使用 aio-pika 发布 `DomainEvent`，否则只记录日志。`RABBITMQ_URL` 必须是标准 AMQP URL（`amqp://用户:密码@host:port/虚拟主机`，如 `amqp://guest:guest@localhost:5672/`）；逗号分隔格式会报 `ValueError: host and port was not specified` 并每 5 秒重连刷屏。
- **URL 通用约定**：所有连接串凭据若含 `@`、`:`、`/` 等特殊字符，需做 URL 百分号编码（如 `@` → `%40`）。
- **对象存储**：`get_object_storage()` 在 `STORAGE_BACKEND=rustfs` 时使用 S3 兼容 API，否则写入 `STORAGE_LOCAL_DIR`。
- **实时协作**：`routers/v1/collaboration.py` 暴露 `WS /v1/collaboration/ws/{room_id}?token=...`，兼容 ooxml 三端编辑器使用的标准 Yjs sync/awareness 线协议。`services/collaboration.py` 维护房间参与者和近期消息历史：收到 type 0（sync）消息时缓存并广播给房间内其他人，后加入者会收到历史回放。房间号格式 `doc-{documentId}-{format}`，按“文档+格式”隔离（docx/xlsx/pptx 的 Y.Doc 顶层键不可混用）。鉴权走 query token（浏览器 WebSocket 无法自定义 header），要求用户启用且有 `document:write` 权限（超级用户豁免），文档须存在且未删除；鉴权用短会话完成，长连接不持有数据库会话。当前房间状态为进程内共享，仅适用于单 worker 部署；多 worker 需外接共享发布订阅后改造。`GET /v1/collaboration/rooms/{room_id}` 返回在线人数。
- **敏感信息**：JWT 密钥与初始管理员口令只从环境变量读取，生产环境缺失时启动即报错。

## 测试

`tests/` 使用内存 SQLite、随机密钥与随机管理员口令，覆盖：

- 统一响应与健康检查
- 登录、鉴权、当前用户、动态菜单
- 文档 CRUD、版本、上传下载、软删除与恢复
- 仪表盘统计
- 应用 `lifespan` 真实启动路径

```bash
cd backend && python -m pytest -q
```
