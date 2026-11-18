# 前端说明

## 基础

`frontend/` 是基于 [ElementAdminV3](https://github.com/kailong321200875/vue-element-plus-admin) 的 pnpm workspace，主应用为 `apps/admin`：

- Vue 3.5 + `<script setup lang="ts">`、Pinia、Vue Router 5、Element Plus、Axios。
- HTTP 请求封装在 `packages/request`（`createRequest`）与 `apps/admin/src/request`（业务拦截器）。
- 业务路由由后端 `GET /v1/system/menus` 动态下发，`src/utils/routerHelper.ts` 把 `views/...` 映射到 `src/views` 下的组件。

## 当前状态

当前为脚手架原始状态，尚未接入后端与 ooxml 编辑器。接入时需完成以下改造（对应后端契约见 `docs/backend/api-contract.md`）：

| 改造点 | 内容 |
| --- | --- |
| `apps/admin/src/constants/index.ts` | `SUCCESS_CODE` 由 `0` 改为 `200`，与后端统一响应契约对齐 |
| `apps/admin/src/request/index.ts` | Token 注入改为标准 `Bearer <JWT>`；`401` 清除本地会话 |
| `apps/admin/vite.config.ts` | 增加 `/api` → `http://127.0.0.1:8000` 代理，转发时剥掉 `/api` 前缀 |
| `apps/admin/src/api/login/*` | 登录、登出、当前用户、动态菜单对接 `/v1/auth/*`、`/v1/system/menus` |
| `apps/admin/src/api/document/*` | 文档、版本、分享 API 与类型定义 |
| `apps/admin/src/views/Document/*` | 文档列表/新建/版本/分享页；新建支持浏览器端生成空白 docx/xlsx/pptx/vsdx |
| ooxml 编辑器 | Word/Excel/PPT/Visio 分别用 `docx-vue-viewer`、`xlsx-vue-viewer`、`pptx-vue-viewer`、`visio-vue-viewer` 的 Vue 组件挂载；协作走 `WS /v1/collaboration/ws/{room_id}` |

空白文档生成直接调用 `ooxml-core`：`saveDocx(createDocument())`、`saveXlsx(createWorkbook())`、`buildBlankPresentationArchive({ initialSlideCount: 1 })`、`createVsdx()`，无需二进制模板。

Visio 采用 `visio-vue-viewer` 的 `<VisioViewer>`，它是真正的画布编辑器（功能区、图形窗口、页面标签、拖拽式图形增删改），不是图形列表；通过 `load()` 载入字节、`exportVsdx()` 导出写回。协作配置由 `src/utils/collaboration.ts` 统一构造，遵循 ooxml 共享契约使用 `user.name` 标识协作者，支持光标与选区同步。

图标统一由 `src/icons.ts` 的 `iconCatalog` 离线注册（当前 158 个），种子菜单与代码中引用的 `mdi:` 图标名必须已在该集合中注册，否则渲染为空；`IconPicker` 只从该集合检索。新增菜单图标时先在 `icons.ts` 导入对应 `@iconify-icons/mdi/*` 并登记目录项。

字体大小统一由 `packages/styles/src/var.css` 的 `--app-font-size-base`（当前 15px）一处控制：xs/sm/md/lg/xl/2xl 各档以 `calc()` 相对基准派生，并覆盖 Element Plus 的 `--el-font-size-*`，`App.vue` 的 `body` 也以该基准为字号。**改一个 `--app-font-size-base` 即可整体缩放全站字号**；业务页面已把散落的字号替换为 `--app-font-size-*` 语义变量。登录页的 `clamp()` 大标题、kicker、数字卡片等属品牌视觉设计，保留固定 px 不随基准缩放。

PPTX 编辑器界面文本走宿主 vue-i18n：`pptx-vue-viewer` 的中文词条（`translationsZhCN`）经 `toVueI18nSyntax` 转换后并入 `src/config/locale.ts` 的 `zh-CN` 消息表，界面随宿主语言切换中文/英文。

四个编辑器统一由 `src/hooks/useEditorPreferences.ts` 派生界面偏好：语言跟随 ElementAdmin 的 vue-i18n（`locale`），明暗主题跟随 Pinia `appStore.isDark`。Word/Excel 传 `locale` 与 `theme`（`light`/`dark`），PPTX 传 `default-locale` 与 `theme` 主题对象（vermilion light/dark），Visio 传 `locale`；编辑器容器的 `color-scheme` 随 `isDark` 切换，让基于 CSS 变量的 viewer（含 Visio）一并跟随明暗。

保存：`DocumentEditor` 统一提供手动「保存为新版本」与防抖自动保存（默认开启，5 秒无编辑后写新版本，变更日志标注「自动保存」）；工具栏可切换「自动/手动」。各面板只需暴露 `exportBytes()`/`markClean()` 并抛出 `dirty-change`，`DocumentEditor` 负责复位 dirty（兼容 PPTX 无 `markClean` 的情况）。

## 环境变量

| 变量 | 值 | 说明 |
| --- | --- | --- |
| `VITE_API_BASE_PATH` | `/api` | Axios baseURL；开发由 Vite 代理转发，生产由 Nginx 反向代理 |
| `VITE_USE_MOCK` | `false` | 关闭脚手架 mock |
| `VITE_APP_TITLE` | `在线文档管理系统` | 页面标题 |
| `VITE_BASE_PATH` / `VITE_OUT_DIR` | 按环境区分 | 构建输出 |

## 页面与路由映射

后端菜单表 `component` 字段必须与前端文件对应，`src/views` 的目录按后端菜单分组组织，不再把全部后台页面堆在 `System/` 下：

| 菜单分组 | component 前缀 | 前端目录 |
| --- | --- | --- |
| 仪表盘 | `views/Dashboard/` | `src/views/Dashboard/` |
| 文档管理 | `views/Document/` | `src/views/Document/` |
| 系统管理（用户/角色/权限） | `views/System/` | `src/views/System/` |
| 审计日志（操作/登录） | `views/Audit/` | `src/views/Audit/` |
| 配置管理（参数/定时任务/系统接口） | `views/Config/` | `src/views/Config/` |
| 监控管理（服务监控/在线用户/文件管理） | `views/Monitor/` | `src/views/Monitor/` |
| 通知公告 | `views/Notice/` | `src/views/Notice/` |
| 组织管理（机构/部门） | `views/Organization/` | `src/views/Organization/` |

其中 `#` 渲染 `src/layout/Layout.vue`（目录菜单），`##` 为隐藏操作权限、不渲染组件。后端 `ensure_builtin_menus()` 每次启动会同步 `component` 到已有记录，老库升级后自动指向新路径；`tests/test_menu_hierarchy.py` 校验每个内置菜单的 component 都能在前端找到对应 `.vue` 文件。

## 常用命令

```bash
cd frontend
pnpm install --registry=https://registry.npmjs.org
pnpm dev:admin          # 开发服务器
pnpm typecheck:admin    # vue-tsc 类型检查
pnpm build:admin        # 生产构建（dist-pro）
pnpm lint               # oxlint
```
