<script setup lang="ts">
  import { onMounted, ref } from 'vue'
  import { VisioViewer } from 'visio-vue-viewer'
  import type { ViewerHandle, ViewerCallbacks, VisioCollaborationOptions } from 'visio-vue-viewer'
  import type { CollaborationSession } from '@/utils/collaboration'
  import { useEditorPreferences } from '@/hooks/useEditorPreferences'

  const { editorLocale } = useEditorPreferences()

  const props = defineProps<{
    bytes: Uint8Array
    fileName: string
    collaboration?: CollaborationSession | null
    readOnly?: boolean
  }>()

  const emit = defineEmits<{
    'dirty-change': [value: boolean]
  }>()

  const viewerRef = ref<ViewerHandle | null>(null)

  /** ooxml 协作选项：房间号、服务地址、令牌与协作者身份来自父级会话。 */
  const collabOptions = (): VisioCollaborationOptions | null => {
    const session = props.collaboration
    if (!session) return null
    return {
      roomId: session.roomId,
      serverUrl: session.serverUrl,
      authToken: session.authToken,
      user: { name: session.user.name, role: session.user.role ?? 'collaborator' },
      intent: 'join'
    }
  }

  const events: ViewerCallbacks = {
    'document-change': (detail) => emit('dirty-change', detail.dirty),
    'document-error': (error) => {
      // eslint-disable-next-line no-console
      console.error('[Visio] 文档处理失败', error)
    }
  }

  onMounted(async () => {
    await viewerRef.value?.load(props.bytes)
  })

  /** 导出平铺图形数据；私有编辑字段不参与。 */
  async function exportBytes(): Promise<Uint8Array> {
    const handle = viewerRef.value
    if (!handle) throw new Error('Visio 编辑器尚未就绪')
    const result = handle.exportVsdx()
    if (!result.bytes.length) throw new Error('导出内容为空')
    return result.bytes
  }

  function markClean(): void {
    viewerRef.value?.controller.markClean()
    emit('dirty-change', false)
  }

  defineExpose({ exportBytes, markClean })
</script>

<template>
  <VisioViewer
    ref="viewerRef"
    :can-edit="!props.readOnly"
    :read-only="props.readOnly ?? false"
    :show-toolbar="true"
    :collaboration="collabOptions()"
    :events="events"
    :locale="editorLocale"
    class="editor-surface"
  />
</template>
