# 权限模型

系统采用「导航菜单 + 操作权限（按钮权限）」模型，二者都以 `sys_menu` 记录承载，通过角色（`sys_role`）关联到用户。

## 两层权限

| 层次 | 载体 | permission_code | 作用 | 后端是否校验 |
| --- | --- | --- | --- | --- |
| 导航菜单 | 普通菜单（`hidden=false`） | `*:view`（如 `document:view`） | 控制用户「看得到」哪些页面，参与动态路由下发 | 否（仅前端标识与角色授权树展示） |
| 粗粒度模块权限 | 隐藏菜单（`hidden=true`、`component='##'`） | `*:write` | 权限组：拥有即蕴含该模块全部细粒度按钮权限，兼容旧角色授权 | 否（仅作为权限组，被展开使用） |
| 细粒度按钮权限 | 隐藏菜单（`hidden=true`、`component='##'`） | `resource:action`（如 `document:create`） | 对应页面上一个具体写按钮，是后端接口实际校验的单元 | 是，由 `require_permissions(...)` 与协作 WS 强制校验 |

全部操作权限按业务归属挂到对应导航菜单下，作为菜单子节点存在于权限表，不下发前端路由。

一个权限码要生效，必须同时满足：某菜单记录带该 `permission_code` 且 `enabled=true`，并且该菜单被分配给用户的某个角色。超管（`is_superuser`）直接放行所有权限（权限码为 `['*']`）。

## 粗码与细码的兼容

细粒度按钮权限（`resource:action`）是实际鉴权单元，但为了不给历史角色重新授权，保留了 `document:write`/`user:write`/`system:write` 三个粗码作为「权限组」：

- `src/core/permissions.py` 的 `COARSE_TO_FINE` 定义粗码蕴含的细码集合；
- 鉴权时（`get_current_user`、`AuthService._permissions_of`、协作 WS）调用 `expand_permissions()`，把用户持有的粗码展开为「粗码本身 + 全部所属细码」；
- 因此持有 `document:write` 的老角色自动拥有 `document:create`/`upload`/`update`/`delete`/`restore`/`share`，行为与改造前一致；
- 新增自定义角色时，可只勾选个别细码（如仅 `document:create`）实现更精细的控制。

## 按钮权限码清单

| 所属菜单 | 粗码 | 细粒度按钮权限 |
| --- | --- | --- |
| 文档管理 | `document:write` | `document:create`（新建空白文档）、`document:upload`（上传文件/新版本）、`document:update`（编辑内容/信息、在线保存）、`document:delete`、`document:restore`、`document:share`（创建/撤销分享） |
| 用户管理 | `user:write` | `user:create`、`user:update`（含设置角色）、`user:activate`（激活/停用）、`user:delete` |
| 角色管理 | `system:write` | `role:create`、`role:update`、`role:delete` |
| 权限管理 | `system:write` | `permission:create`、`permission:update`（含启停）、`permission:delete` |
| 参数管理 | `system:write` | `config:create`、`config:update`、`config:delete` |
| 通知公告 | `system:write` | `notice:create`、`notice:update`、`notice:delete` |
| 定时任务 | `system:write` | `job:create`、`job:update`、`job:run`、`job:delete` |
| 机构管理 | `system:write` | `org:create`、`org:update`、`org:delete` |
| 部门管理 | `system:write` | `dept:create`、`dept:update`、`dept:delete` |

按 id 的文档写操作还会经过数据隔离（`owner_id` + `data_scope`）：非超管的 `self`/`dept` 范围只能操作本人/本部门的文档，越权统一返回 404。因此授予文档写权限不会导致跨用户越权。

## 内置角色

| 角色 | 导航菜单 | 操作权限 | 数据范围 |
| --- | --- | --- | --- |
| `admin` | 全部 | 全部（超管 `*`） | 全库（超管） |
| `user` | 仪表盘、文档管理 | `document:write`（展开为全部文档细码） | 仅本人（`self`，可在用户管理中调整） |

- 两个内置角色均由 `seed.py` 的 `ensure_builtin_roles()` 幂等创建/同步，且不可删除。
- 自助注册的用户默认绑定 `user` 角色并处于待激活状态；管理员激活后即可在自身数据范围内完整使用文档 CRUD 与协作。
- `user` 不含 `user:write`/`system:write`，无法进行用户与系统管理。

## 前端联动

- 登录响应 `LoginOut.user` 携带 `roles` 与 `permissions`（超管为 `['*']`，其余为展开后的细码集合），存入 Pinia `user` store。
- `useUserStore().hasPermission(code)` 做按钮级判定：超管、通配符、显式拥有该码或所属模块粗码即放行。`src/hooks/usePermission.ts` 提供 `can('resource:action')` 便捷封装。
- 各页面写按钮按细粒度权限码显隐：文档列表的新建/上传/编辑/信息/恢复/删除/分享、编辑器的保存（只读用户隐藏并禁用自动保存与协作）、用户/角色/权限/参数/公告/定时任务/机构/部门的增删改与执行。
- 角色授权的树形控件按后端父子层级渲染：操作权限作为对应菜单的子节点展示，勾选父菜单会级联勾选其下操作权限。
