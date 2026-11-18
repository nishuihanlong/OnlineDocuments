import { createDocument, saveDocx } from 'docx-vue-viewer'
import { createWorkbook, saveXlsx } from 'xlsx-vue-viewer'
import { buildBlankPresentationArchive } from 'ooxml-core/pptx'
import { createVsdx } from 'ooxml-core/visio'

/** 可在线编辑的文档格式。 */
export type EditableDocFormat = 'docx' | 'xlsx' | 'pptx' | 'vsdx'

export interface BlankDocument {
  format: EditableDocFormat
  fileName: string
  mimeType: string
  bytes: Uint8Array
}

const BLANK_BUILDERS: Record<EditableDocFormat, () => Promise<Uint8Array>> = {
  docx: async () => new Uint8Array(await saveDocx(createDocument())),
  xlsx: async () => new Uint8Array(await saveXlsx(createWorkbook())),
  pptx: async () => new Uint8Array(await buildBlankPresentationArchive({ initialSlideCount: 1 })),
  vsdx: () => createVsdx()
}

const BLANK_META: Record<EditableDocFormat, { fileName: string; mimeType: string }> = {
  docx: { fileName: '文档.docx', mimeType: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' },
  xlsx: { fileName: '表格.xlsx', mimeType: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' },
  pptx: { fileName: '演示文稿.pptx', mimeType: 'application/vnd.openxmlformats-officedocument.presentationml.presentation' },
  vsdx: { fileName: '绘图.vsdx', mimeType: 'application/vnd.ms-visio.drawing' }
}

/** 在浏览器端生成指定格式的空白 OOXML 文件，无需任何二进制模板。 */
export async function buildBlankDocument(format: EditableDocFormat): Promise<BlankDocument> {
  const meta = BLANK_META[format]
  return { format, ...meta, bytes: await BLANK_BUILDERS[format]() }
}

/** 从文件名或 MIME 类型识别可编辑格式；无法识别返回 null。 */
export function detectDocFormat(fileName?: string | null, mimeType?: string | null): EditableDocFormat | null {
  const ext = (fileName?.split('.').pop() ?? '').toLowerCase()
  if (ext === 'docx' || mimeType === 'application/vnd.openxmlformats-officedocument.wordprocessingml.document') return 'docx'
  if (ext === 'xlsx' || mimeType === 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet') return 'xlsx'
  if (ext === 'pptx' || mimeType === 'application/vnd.openxmlformats-officedocument.presentationml.presentation') return 'pptx'
  if (ext === 'vsdx' || mimeType === 'application/vnd.ms-visio.drawing') return 'vsdx'
  return null
}

/** Base64 解码为字节数组（用于编辑器加载文件内容）。 */
export function base64ToBytes(base64: string): Uint8Array {
  const binary = atob(base64)
  const bytes = new Uint8Array(binary.length)
  for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i)
  return bytes
}

/** 字节数组编码为 Base64（用于公开分享的 JSON 保存接口）。 */
export function bytesToBase64(bytes: Uint8Array): string {
  let binary = ''
  bytes.forEach((byte) => {
    binary += String.fromCharCode(byte)
  })
  return btoa(binary)
}

/** 把字节数组复制为独立 ArrayBuffer，满足 Blob/File 的类型要求。 */
export function toArrayBuffer(bytes: Uint8Array): ArrayBuffer {
  const copy = new Uint8Array(bytes.length)
  copy.set(bytes)
  return copy.buffer as ArrayBuffer
}

/** 字节数组包装为 File，便于走统一上传接口。 */
export function bytesToFile(bytes: Uint8Array, fileName: string, mimeType: string): File {
  return new File([toArrayBuffer(bytes)], fileName, { type: mimeType })
}

/** 字节数转可读文本。 */
export function formatFileSize(size: number): string {
  if (size < 1024) return `${size} B`
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`
  return `${(size / 1024 / 1024).toFixed(1)} MB`
}
