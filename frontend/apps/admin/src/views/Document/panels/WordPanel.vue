<script setup lang="ts">
  import { onMounted, ref } from 'vue'
  import { WordEditor } from 'docx-vue-viewer'
  import type { CollaborationSession } from '@/utils/collaboration'
  import { useEditorPreferences } from '@/hooks/useEditorPreferences'

  const { editorLocale, editorThemeMode } = useEditorPreferences()

  interface WordHandle {
    load(input: Uint8Array | ArrayBuffer): Promise<void>
    save(): Promise<Blob>
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

  const editorRef = ref<WordHandle | null>(null)

  onMounted(async () => {
    await editorRef.value?.load(props.bytes)
  })

  async function exportBytes(): Promise<Uint8Array> {
    const handle = editorRef.value
    if (!handle) throw new Error('编辑器尚未就绪')
    const blob = await handle.save()
    return new Uint8Array(await blob.arrayBuffer())
  }

  function markClean(): void {
    editorRef.value?.markClean()
  }

  defineExpose({ exportBytes, markClean })
</script>

<template>
  <WordEditor
    ref="editorRef"
    :file-name="props.fileName"
    :read-only="props.readOnly ?? false"
    :locale="editorLocale"
    :theme="editorThemeMode"
    :collaboration="props.collaboration ?? null"
    class="editor-surface"
    @dirty-change="(dirty: boolean) => emit('dirty-change', dirty)"
  />
</template>
