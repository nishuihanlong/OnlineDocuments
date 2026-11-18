<script setup lang="ts">
  import { ref } from 'vue'
  import { SpreadsheetEditor } from 'xlsx-vue-viewer'
  import type { CollaborationSession } from '@/utils/collaboration'
  import { useEditorPreferences } from '@/hooks/useEditorPreferences'

  const { editorLocale, editorThemeMode } = useEditorPreferences()

  interface SheetHandle {
    saveBytes(format?: 'xlsx' | 'csv'): Promise<Uint8Array>
    markClean(): void
    readonly dirty: boolean
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

  const editorRef = ref<SheetHandle | null>(null)

  async function exportBytes(): Promise<Uint8Array> {
    const handle = editorRef.value
    if (!handle) throw new Error('编辑器尚未就绪')
    return handle.saveBytes('xlsx')
  }

  function markClean(): void {
    editorRef.value?.markClean()
  }

  defineExpose({ exportBytes, markClean })
</script>

<template>
  <SpreadsheetEditor
    ref="editorRef"
    :bytes="props.bytes"
    :file-name="props.fileName"
    :read-only="props.readOnly ?? false"
    :locale="editorLocale"
    :theme="editorThemeMode"
    :collaboration="props.collaboration ?? null"
    class="editor-surface"
    @dirty-change="(dirty: boolean) => emit('dirty-change', dirty)"
  />
</template>
