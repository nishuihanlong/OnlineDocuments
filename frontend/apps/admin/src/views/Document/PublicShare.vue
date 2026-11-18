<script setup lang="ts">
  import { computed, defineAsyncComponent, onMounted, ref } from 'vue'
  import { useRoute } from 'vue-router'
  import { ElButton, ElMessage, ElTag } from 'element-plus'
  import { getPublicShareApi, savePublicShareApi } from '@/api/document'
  import type { PublicShareItem } from '@/api/document/types'
  import { base64ToBytes, bytesToBase64, detectDocFormat, formatFileSize, toArrayBuffer } from '@/utils/documentFile'
  import type { EditableDocFormat } from '@/utils/documentFile'

  const WordPanel = defineAsyncComponent(() => import('./panels/WordPanel.vue'))
  const SpreadsheetPanel = defineAsyncComponent(() => import('./panels/SpreadsheetPanel.vue'))
  const PowerPointPanel = defineAsyncComponent(() => import('./panels/PowerPointPanel.vue'))

  const route = useRoute()
  const token = computed(() => String(route.params.token || ''))
  const share = ref<PublicShareItem | null>(null)
  const bytes = ref<Uint8Array>(new Uint8Array())
  const format = ref<EditableDocFormat | null>(null)
  const loading = ref(true)
  const error = ref('')
  const saving = ref(false)
  const panelRef = ref<{ exportBytes(): Promise<Uint8Array>; markClean(): void } | null>(null)

  const canEdit = computed(() => share.value?.permission === 'write')

  const panelComponent = computed(() => {
    if (format.value === 'docx') return WordPanel
    if (format.value === 'xlsx') return SpreadsheetPanel
    if (format.value === 'pptx') return PowerPointPanel
    return null
  })

  const loadShare = async () => {
    loading.value = true
    error.value = ''
    try {
      const res = await getPublicShareApi(token.value)
      share.value = res.data
      if (!res.data.content_base64) {
        error.value = '该分享文档暂无文件版本'
        return
      }
      const detected = detectDocFormat(res.data.file_name, res.data.mime_type)
      if (!detected) {
        error.value = `暂不支持在线预览该格式：${res.data.file_name || res.data.mime_type || '未知'}`
        return
      }
      format.value = detected
      bytes.value = base64ToBytes(res.data.content_base64)
    } catch (e) {
      error.value = e instanceof Error ? e.message : '分享链接无效或已失效'
    } finally {
      loading.value = false
    }
  }

  onMounted(() => void loadShare())

  const saveShare = async () => {
    if (!share.value || !panelRef.value) return
    saving.value = true
    try {
      const content = await panelRef.value.exportBytes()
      if (!content.length) throw new Error('导出内容为空')
      const result = (
        await savePublicShareApi(token.value, {
          file_name: share.value.file_name || `shared.${format.value}`,
          content_base64: bytesToBase64(content),
          mime_type: share.value.mime_type || undefined,
          change_log: '通过公开分享链接保存'
        })
      ).data
      panelRef.value.markClean()
      ElMessage.success(`已保存为版本 v${result.version_no}`)
      await loadShare()
    } catch (e) {
      ElMessage.error(e instanceof Error ? e.message : '保存失败')
    } finally {
      saving.value = false
    }
  }

  const download = () => {
    if (!share.value?.content_base64) return
    const blob = new Blob([toArrayBuffer(base64ToBytes(share.value.content_base64))], {
      type: share.value.mime_type || 'application/octet-stream'
    })
    const url = URL.createObjectURL(blob)
    const anchor = document.createElement('a')
    anchor.href = url
    anchor.download = share.value.file_name || 'document'
    anchor.click()
    URL.revokeObjectURL(url)
  }
</script>

<template>
  <div class="share-page">
    <div class="share-toolbar">
      <span class="share-title">{{ share?.document_title || '分享文档' }}</span>
      <ElTag :type="canEdit ? 'success' : 'info'" size="small" effect="plain">
        {{ canEdit ? '可编辑' : '只读' }}
      </ElTag>
      <span v-if="share?.file_name" class="share-file">{{ share.file_name }}</span>
      <span v-if="share?.size" class="share-file">{{ formatFileSize(share.size) }}</span>
      <div class="share-actions">
        <ElButton v-if="share?.content_base64" size="small" @click="download">下载文件</ElButton>
        <ElButton v-if="canEdit" type="primary" size="small" :loading="saving" @click="saveShare">
          保存为新版本
        </ElButton>
      </div>
    </div>
    <div v-if="loading" class="share-status">正在打开分享文档…</div>
    <div v-else-if="error" class="share-status share-status--error">
      <p>{{ error }}</p>
      <ElButton size="small" @click="loadShare()">重试</ElButton>
    </div>
    <div v-else-if="panelComponent" class="share-body">
      <component
        :is="panelComponent"
        ref="panelRef"
        :bytes="bytes"
        :file-name="share?.file_name || ''"
        :read-only="!canEdit"
      />
    </div>
  </div>
</template>

<style scoped>
  .share-page {
    display: flex;
    flex-direction: column;
    height: 100vh;
    overflow: hidden;
  }

  .share-toolbar {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 8px 16px;
    border-bottom: 1px solid var(--el-border-color-light);
    background: var(--el-bg-color);
  }

  .share-title {
    font-weight: 600;
  }

  .share-file {
    font-size: var(--app-font-size-xs);
    color: var(--el-text-color-secondary);
  }

  .share-actions {
    display: flex;
    gap: 8px;
    margin-left: auto;
  }

  .share-status {
    display: flex;
    flex: 1;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 12px;
    color: var(--el-text-color-secondary);
  }

  .share-status--error {
    color: var(--el-color-danger);
  }

  .share-body {
    flex: 1;
    min-height: 0;
  }

  .share-body :deep(.editor-surface) {
    height: 100%;
  }
</style>
