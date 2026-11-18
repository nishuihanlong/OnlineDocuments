import type { EditableDocFormat } from './documentFile'

/** 协作者在房间内的身份；ooxml 编辑器据此显示光标姓名与在线列表。 */
export interface CollaborationUser {
  name: string
  role?: 'owner' | 'collaborator' | 'viewer'
}

/** 传给 ooxml 编辑器的协作会话配置（Word/Excel/PPT/Visio 通用子集）。 */
export interface CollaborationSession {
  roomId: string
  serverUrl: string
  authToken: string
  /** ooxml 共享契约使用 user.name；顶层 userName 会被忽略，故统一放在此。 */
  user: CollaborationUser
}

/** 协作房间号：按“文档+格式”隔离，与后端 WS 路由的校验规则一致。 */
export function buildRoomId(documentId: number, format: EditableDocFormat): string {
  return `doc-${documentId}-${format}`
}

/**
 * Yjs 协作服务地址。浏览器 WebSocket 无法自定义请求头，
 * token 由编辑器以 query 参数携带；服务端路径为 /v1/collaboration/ws/{room_id}，
 * 经 `/api` 代理转发并剥掉前缀。
 */
export function collaborationServerUrl(): string {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  return `${protocol}//${window.location.host}/api/v1/collaboration/ws`
}

/** 由当前登录用户与文档信息构造协作会话。 */
export function buildCollaborationSession(
  documentId: number,
  format: EditableDocFormat,
  userName: string,
  token: string,
  role: CollaborationUser['role'] = 'collaborator'
): CollaborationSession {
  return {
    roomId: buildRoomId(documentId, format),
    serverUrl: collaborationServerUrl(),
    authToken: token,
    user: { name: userName, role }
  }
}
