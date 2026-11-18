<script setup lang="ts">
  import { ref } from 'vue'
  import { PowerPointViewer } from 'pptx-vue-viewer'
  import 'pptx-vue-viewer/styles.css'
  import type { CollaborationSession } from '@/utils/collaboration'
  import { useEditorPreferences } from '@/hooks/useEditorPreferences'

  const { editorLocale, pptxTheme } = useEditorPreferences()

  interface PptHandle {
    getContent(): Promise<Uint8Array>
  }

  const props = defineProps<{
    bytes: Uint8Array
    fileName: string
    collaboration?: CollaborationSession | null
    readOnly?: boolean
  }>()

  const emit = defineEmits<{
    (e: 'dirty-change', dirty: boolean): void
  }>()

  const viewerRef = ref<PptHandle | null>(null)

  async function exportBytes(): Promise<Uint8Array> {
    const handle = viewerRef.value
    if (!handle) throw new Error('编辑器尚未就绪')
    return handle.getContent()
  }

  defineExpose({ exportBytes, markClean: () => {} })
</script>

<template>
  <PowerPointViewer
    ref="viewerRef"
    :content="props.bytes"
    :file-name="props.fileName"
    :can-edit="!props.readOnly"
    :read-only="props.readOnly ?? false"
    :collaboration="props.collaboration ?? undefined"
    :default-locale="editorLocale"
    :theme="pptxTheme"
    class="editor-surface"
    @dirty-change="(dirty: boolean) => emit('dirty-change', dirty)"
  />
</template>
