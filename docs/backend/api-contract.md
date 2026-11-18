# 前后端交互契约

## 统一响应结构

所有 JSON 接口（含错误响应）均返回：

```json
{
  "code": 200,
  "message": "success",
  "data": {}
}
```

- `code` 为**业务状态码**，使用标准 HTTP 状态码；`200` 表示成功，其余为错误。
- HTTP 状态码与 `code` 保持一致；前端必须根据 `code` 判断业务结果。
- `message` 为提示信息，失败时携带可读原因。
- `data` 为实际数据，失败时为 `null`。

## 错误码

| code | 含义 | 典型场景 |
| --- | --- | --- |
| 200 | 成功 | 正常请求 |
| 400 | 请求参数或业务规则错误 | 上传空文件、无效的分享操作 |
| 401 | 未认证 / 令牌失效 | 未带令牌、口令错误 |
| 403 | 无权限 / 账号停用 | 缺少权限码 |
| 404 | 资源不存在 | 文档或用户不存在 |
| 409 | 资源冲突 | 用户名重复；文档无附件 |
| 422 | 参数校验失败 | Pydantic 校验不通过 |
| 500 | 服务器内部错误 | 未捕获异常（日志记录堆栈） |

## 时间格式

所有时间字段统一为 UTC 的 ISO 8601 字符串：`2026-11-13T10:00:00Z`。禁止时间戳与区域格式。`schemas/common.py` 的 `Iso8601DateTime` 负责统一序列化。

## 认证方式

1. `POST /v1/auth/login` 返回 `data.accessToken`。
2. 后续请求携带 `Authorization: Bearer <accessToken>`。
3. 后端校验 JWT、用户状态与角色菜单权限；`401` 时前端会清除本地会话。

## 分页契约

查询参数：`page`（从 1 开始）、`page_size`（1~100）。响应：

```json
{
  "code": 200,
  "message": "success",
  "data": { "items": [], "total": 0, "page": 1, "page_size": 20 }
}
```

## 动态菜单契约

`GET /v1/system/menus` 返回前端 `AppCustomRouteRecordRaw[]`：

```json
{
  "path": "/document",
  "name": "Document",
  "component": "#",
  "redirect": "/document/list",
  "meta": { "title": "文档管理", "icon": "mdi:file-document-multiple" },
  "children": [
    { "path": "list", "name": "DocumentList", "component": "views/Document/DocumentList", "meta": { "title": "文档列表" } }
  ]
}
```

- `#` 表示布局组件，`##` 表示纯分组，`views/...` 映射到前端 `src/views` 下真实存在的文件。
- `hidden` 菜单只承载按钮级权限码，不会下发给前端路由。

## 接口清单

| 方法 | 路径 | 说明 | 认证 |
| --- | --- | --- | --- |
| GET | `/health` | 存活探针 | 否 |
| POST | `/v1/auth/register` | 自助注册（默认 user 角色、待激活） | 否 |
| POST | `/v1/auth/login` | 登录（待激活账号返回 401「账号待管理员激活」） | 否 |
| GET | `/v1/auth/me` | 当前用户与权限 | 是 |
| POST | `/v1/auth/logout` | 登出审计 | 是 |
| GET | `/v1/system/health` | 服务与基础设施状态 | 否 |
| GET | `/v1/system/menus` | 动态路由 | 是 |
| GET | `/v1/system/dashboard/total` | 概览指标 | 是 |
| GET | `/v1/system/dashboard/activity` | 近 7 天操作活跃度 | 是 |
| GET | `/v1/system/dashboard/trend` | 近 12 月文档趋势 | 是 |
| GET / POST | `/v1/users` | 用户列表 / 新增 | 是 |
| GET / PUT / DELETE | `/v1/users/{id}` | 用户详情 / 更新 / 停用 | 是 |
| POST | `/v1/users/{id}/activate` | 激活用户（需 user:write） | 是 |
| GET / POST | `/v1/documents` | 文档列表 / 新建 | 是 |
| GET / PUT / DELETE | `/v1/documents/{id}` | 文档详情 / 更新 / 软删除 | 是 |
| POST | `/v1/documents/{id}/restore` | 恢复文档 | 是 |
| GET | `/v1/documents/{id}/versions` | 版本历史 | 是 |
| POST | `/v1/documents/{id}/upload` | 上传文件（`multipart/form-data`） | 是 |
| GET | `/v1/documents/{id}/download` | 下载当前版本（Base64 JSON） | 是 |
| GET | `/v1/collaboration/rooms/{room_id}` | 协作房间在线人数 | 否 |
| WS | `/v1/collaboration/ws/{room_id}?token=...` | Yjs 实时协作（标准 sync/awareness 二进制消息） | 是（query token） |
| POST | `/v1/shares` | 创建分享（公开链接或指定用户，read/write） | 是 |
| GET | `/v1/shares?document_id=` | 某文档的分享列表 | 是 |
| DELETE | `/v1/shares/{share_id}` | 撤销分享 | 是 |
| GET | `/v1/shares/public/{token}` | 免登录读取分享文档（含 Base64 内容） | 否 |
| POST | `/v1/shares/public/{token}/save` | 免登录保存（仅 write 分享，JSON+Base64） | 否 |

> 分享房间/链接的 token 为服务端随机生成并落库（`doc_share` 表），过期与撤销统一返回 404 避免泄露状态；公开保存的版本归属记为分享创建者。

写操作额外校验权限码：用户管理需要 `user:write`，文档管理需要 `document:write`，系统管理需要 `system:write`；超级管理员角色自动放行。

用户状态取值为 `0` 停用 / `1` 启用 / `2` 待激活：自助注册的用户为 `2`，不能登录；管理员调用激活接口后变为 `1`。内置角色 `admin` 与 `user` 不可删除，其中 `user` 是注册用户的默认角色（仅文档基础权限）。

数据隔离：普通用户默认 `data_scope=self`，仅能访问本人数据；管理员可配置为 `dept`（本部门）或 `all`（全库）。文档、用户、日志、仪表盘统计和协作鉴权共用该规则，越权访问统一返回 404。

> 协作房间号格式为 `doc-{documentId}-{format}`（format 取 `docx`/`xlsx`/`pptx`/`vsdx`）。浏览器 WebSocket 无法自定义请求头，token 经 query 传递；连接要求启用用户且具备 `document:write` 权限（超级用户豁免）、文档存在且未删除。服务端不理解 Yjs 文档语义，只做 sync 消息缓存回放与房间广播，房间状态为进程内共享，仅适用于单 worker。

> 下载接口为保证统一 JSON 契约返回 Base64 内容。生产环境处理大文件时建议改为带鉴权的 RustFS 预签名 URL，并同步更新前后端契约。

## 路径前缀

前端 `VITE_API_BASE_PATH=/api`，Vite/Nginx 代理把 `/api` 前缀剥离后转发到后端，因此后端路由**不含** `/api`，统一以 `/v1` 开头。
