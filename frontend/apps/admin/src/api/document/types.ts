export interface DocumentItem {
  id: number
  title: string
  description?: string | null
  owner_id: number
  current_version: number
  file_name?: string | null
  file_size: number
  mime_type?: string | null
  download_count: number
  created_at: string
  updated_at: string
  deleted_at?: string | null
}

export interface DocumentQuery {
  page?: number
  page_size?: number
  keyword?: string
  include_deleted?: boolean
}

export interface DocumentCreateIn {
  title: string
  description?: string
}

export interface DocumentUpdateIn {
  title?: string
  description?: string
}

export interface PageResult<T> {
  items: T[]
  total: number
  page: number
  page_size: number
}

export interface DocumentVersionItem {
  id: number
  document_id: number
  version_no: number
  file_size: number
  change_log?: string | null
  created_by: number
  created_at: string
}

export interface DocumentUploadResult {
  document_id: number
  version_no: number
  storage_key: string
  file_name: string
  file_size: number
}

/** 文件下载结果，内容为 Base64（统一 JSON 响应契约）。 */
export interface DocumentDownload {
  file_name: string
  mime_type: string
  size: number
  content_base64: string
}

export type SharePermission = 'read' | 'write'

export interface ShareCreateIn {
  document_id: number
  permission: SharePermission
  granted_user_id?: number | null
  expires_in_hours?: number | null
}

export interface ShareItem {
  id: number
  document_id: number
  permission: SharePermission
  granted_user_id?: number | null
  granted_username?: string | null
  is_public: boolean
  token: string
  share_path: string
  expires_at?: string | null
  revoked_at?: string | null
  created_by: number
  created_at: string
}

/** 免登录分享读取结果。 */
export interface PublicShareItem {
  token: string
  permission: SharePermission
  document_id: number
  document_title: string
  file_name?: string | null
  mime_type?: string | null
  size: number
  content_base64?: string | null
}
