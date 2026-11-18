import request from '@/request'
import type { PageResult } from './types'
import type {
  DocumentCreateIn,
  DocumentDownload,
  DocumentItem,
  DocumentQuery,
  DocumentUpdateIn,
  DocumentUploadResult,
  DocumentVersionItem,
  PublicShareItem,
  ShareCreateIn,
  ShareItem
} from './types'

/** 分页查询文档。 */
export const getDocumentListApi = (params: DocumentQuery) => {
  return request.get<PageResult<DocumentItem>>({ url: '/v1/documents', params })
}

/** 新建文档元数据（生成 v1 空版本）。 */
export const createDocumentApi = (data: DocumentCreateIn) => {
  return request.post<DocumentItem>({ url: '/v1/documents', data })
}

/** 文档详情。 */
export const getDocumentApi = (id: number) => {
  return request.get<DocumentItem>({ url: `/v1/documents/${id}` })
}

/** 更新文档元数据。 */
export const updateDocumentApi = (id: number, data: DocumentUpdateIn) => {
  return request.put<DocumentItem>({ url: `/v1/documents/${id}`, data })
}

/** 软删除文档（进入回收站）。 */
export const deleteDocumentApi = (id: number) => {
  return request.delete<null>({ url: `/v1/documents/${id}` })
}

/** 从回收站恢复文档。 */
export const restoreDocumentApi = (id: number) => {
  return request.post<DocumentItem>({ url: `/v1/documents/${id}/restore` })
}

/** 版本历史。 */
export const getDocumentVersionsApi = (id: number) => {
  return request.get<DocumentVersionItem[]>({ url: `/v1/documents/${id}/versions` })
}

/** 上传文件生成新版本（multipart/form-data）。 */
export const uploadDocumentFileApi = (id: number, file: File, changeLog?: string) => {
  const formData = new FormData()
  formData.append('file', file)
  if (changeLog) formData.append('change_log', changeLog)
  return request.post<DocumentUploadResult>({
    url: `/v1/documents/${id}/upload`,
    data: formData
  })
}

/** 下载当前版本（Base64）。 */
export const getDocumentDownloadApi = (id: number) => {
  return request.get<DocumentDownload>({ url: `/v1/documents/${id}/download` })
}

/** 创建分享（公开链接或指定用户）。 */
export const createShareApi = (data: ShareCreateIn) => {
  return request.post<ShareItem>({ url: '/v1/shares', data })
}

/** 某文档的分享列表。 */
export const getShareListApi = (documentId: number) => {
  return request.get<ShareItem[]>({ url: '/v1/shares', params: { document_id: documentId } })
}

/** 撤销分享。 */
export const revokeShareApi = (shareId: number) => {
  return request.delete<null>({ url: `/v1/shares/${shareId}` })
}

/** 免登录读取分享文档。 */
export const getPublicShareApi = (token: string) => {
  return request.get<PublicShareItem>({ url: `/v1/shares/public/${token}` })
}

/** 免登录保存（仅 write 分享）。 */
export const savePublicShareApi = (token: string, data: {
  file_name: string
  content_base64: string
  mime_type?: string
  change_log?: string
}) => {
  return request.post<DocumentUploadResult>({ url: `/v1/shares/public/${token}/save`, data })
}
