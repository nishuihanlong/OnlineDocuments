<script setup lang="ts">
  import { computed, defineAsyncComponent, onBeforeUnmount, onMounted, ref, watch } from 'vue'
  import { useRoute, useRouter } from 'vue-router'
  import { ElButton, ElMessage, ElSwitch, ElTag } from 'element-plus'
  import { getDocumentApi, getDocumentDownloadApi, uploadDocumentFileApi } from '@/api/document'
  import type { DocumentItem } from '@/api/document/types'
  import { base64ToBytes, bytesToFile, detectDocFormat } from '@/utils/documentFile'
  import type { EditableDocFormat } from '@/utils/documentFile'
  import { buildCollaborationSession } from '@/utils/collaboration'
  import type { CollaborationSession } from '@/utils/collaboration'
  import { useUserStoreWithOut } from '@/store/modules/user'
  import { useEditorPreferences } from '@/hooks/useEditorPreferences'

  const { isDark } = useEditorPreferences()

  const WordPanel = defineAsyncComponent(() => import('./panels/WordPanel.vue'))
  const SpreadsheetPanel = defineAsyncComponent(() => import('./panels/SpreadsheetPanel.vue'))
  const PowerPointPanel = defineAsyncComponent(() => import('./panels/PowerPointPanel.vue'))
  const VisioPanel = defineAsyncComponent(() => import('./panels/VisioPanel.vue'))

  const route = useRoute()
  const router = useRouter()
  const userStore = useUserStoreWithOut()
  const canUpdate = computed(() => userStore.hasPermission('document:update'))

  const documentId = computed(() => Number(route.params.id))
  const documentInfo = ref<DocumentItem | null>(null)
  const bytes = ref<Uint8Array>(new Uint8Array())
  const format = ref<EditableDocFormat | null>(null)
  const loading = ref(true)
  const loadError = ref('')
  const dirty = ref(false)
  const saving = ref(false)
  const collaborationEnabled = ref(true)
  const autoSaveEnabled = ref(true)
  // 只读用户不参与协作写入，避免 WebSocket 编辑被后端拒绝。
  if (!canUpdate.value) {
    collaborationEnabled.value = false
    autoSaveEnabled.value = false
  }
  const lastSavedAt = ref<string>('')
  const AUTO_SAVE_DELAY = 5000

  const panelRef = ref<{ exportBytes(): Promise<Uint8Array>; markClean(): void } | null>(null)
  let autoSaveTimer: number | undefined

  const collaboration = computed<CollaborationSession | null>(() => {
    if (!collaborationEnabled.value || !format.value || !documentInfo.value) return null
    const token = userStore.token
    if (!token) return null
    const userName = userStore.userInfo?.real_name || userStore.userInfo?.username || '匿名用户'
    return buildCollaborationSession(documentId.value, format.value, userName, token)
  })

  const loadDocument = async () => {
    loading.value = true
    loadError.value = ''
    try {
      const info = (await getDocumentApi(documentId.value)).data
      documentInfo.value = info
      const detected = detectDocFormat(info.file_name, info.mime_type)
      if (!detected) {
        loadError.value = `暂不支持在线编辑该格式：${info.file_name || info.mime_type || '未知'}`
        return
      }
      format.value = detected
      const download = (await getDocumentDownloadApi(documentId.value)).data
      bytes.value = base64ToBytes(download.content_base64)
    } catch (error) {
      loadError.value = error instanceof Error ? error.message : '文档加载失败'
    } finally {
      loading.value = false
    }
  }

  onMounted(() => void loadDocument())

  /** 清除待执行的自动保存定时器。 */
  const clearAutoSave = () => {
    if (autoSaveTimer !== undefined) {
      window.clearTimeout(autoSaveTimer)
      autoSaveTimer = undefined
    }
  }

  /**
   * 保存当前文档为新版本。silent 用于自动保存，避免频繁弹提示。
   * 四个编辑器的 markClean 实现不一致（PPTX 为空），这里统一兜底复位 dirty。
   */
  const saveDocument = async (silent = false) => {
    if (!canUpdate.value) return
    if (!documentInfo.value || !format.value || !panelRef.value) return
    if (saving.value) return
    clearAutoSave()
    saving.value = true
    try {
      const content = await panelRef.value.exportBytes()
      if (!content.length) throw new Error('导出内容为空')
      const file = bytesToFile(content, documentInfo.value.file_name || `document-${documentId.value}.${format.value}`, documentInfo.value.mime_type || 'application/octet-stream')
      const changeLog = silent ? '自动保存' : '在线编辑保存'
      const result = (await uploadDocumentFileApi(documentId.value, file, changeLog)).data
      documentInfo.value.current_version = result.version_no
      panelRef.value.markClean()
      dirty.value = false
      lastSavedAt.value = new Date().toLocaleTimeString('zh-CN', { hour12: false })
      if (!silent) ElMessage.success(`已保存为版本 v${result.version_no}`)
    } catch (error) {
      ElMessage.error(error instanceof Error ? error.message : '保存失败')
    } finally {
      saving.value = false
    }
  }

  /** 监听脏标记，编辑后防抖自动保存；关闭开关或复位时取消定时器。 */
  watch(dirty, (value) => {
    if (!autoSaveEnabled.value || !value) {
      clearAutoSave()
      return
    }
    clearAutoSave()
    autoSaveTimer = window.setTimeout(() => void saveDocument(true), AUTO_SAVE_DELAY)
  })

  /** 自动保存开关关闭时取消待执行任务。 */
  watch(autoSaveEnabled, (enabled) => {
    if (!enabled) clearAutoSave()
  })

  onBeforeUnmount(() => {
    clearAutoSave()
  })

  const goBack = () => router.push('/document/list')

  const panelComponent = computed(() => {
    if (format.value === 'docx') return WordPanel
    if (format.value === 'xlsx') return SpreadsheetPanel
    if (format.value === 'pptx') return PowerPointPanel
    if (format.value === 'vsdx') return VisioPanel
    return null
  })
</script>

<template>
  <div class="editor-page">
    <div class="editor-toolbar">
      <ElButton size="small" @click="goBack">返回列表</ElButton>
      <span class="editor-title">{{ documentInfo?.title || '加载中…' }}</span>
      <span v-if="format" class="editor-format">{{ format.toUpperCase() }}</span>
      <span class="editor-version">v{{ documentInfo?.current_version ?? '-' }}</span>
      <ElTag v-if="dirty" type="warning" size="small" effect="plain">
        {{ autoSaveEnabled && collaboration ? '待自动保存' : '未保存修改' }}
      </ElTag>
      <span v-if="lastSavedAt" class="editor-saved-at">已保存 {{ lastSavedAt }}</span>
      <ElTag :type="collaboration ? 'success' : 'info'" size="small" effect="plain">
        {{ collaboration ? '协作已开启' : '协作已关闭' }}
      </ElTag>
      <div class="editor-toolbar-actions">
        <ElTag v-if="!canUpdate" type="info" size="small" effect="plain">只读</ElTag>
        <template v-if="canUpdate">
          <ElSwitch v-model="autoSaveEnabled" size="small" inline-prompt active-text="自动" inactive-text="手动" />
          <ElSwitch v-model="collaborationEnabled" size="small" inline-prompt active-text="协作" inactive-text="单人" />
          <ElButton size="small" type="primary" :loading="saving" :disabled="!format" @click="saveDocument(false)">
            保存为新版本
          </ElButton>
        </template>
      </div>
    </div>

    <div v-if="loading" class="editor-status">文档加载中…</div>
    <div v-else-if="loadError" class="editor-status editor-status--error">
      <p>{{ loadError }}</p>
      <ElButton size="small" @click="goBack">返回列表</ElButton>
    </div>
    <div
      v-else-if="panelComponent"
      class="editor-body"
      :style="{ colorScheme: isDark ? 'dark' : 'light' }"
    >
      <component
        :is="panelComponent"
        ref="panelRef"
        :bytes="bytes"
        :file-name="documentInfo?.file_name || ''"
        :collaboration="collaboration"
        @dirty-change="dirty = $event"
      />
    </div>
  </div>
</template>

<style scoped>
  .editor-page {
    display: flex;
    flex-direction: column;
    height: 100vh;
    overflow: hidden;
  }

  .editor-toolbar {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 8px 16px;
    border-bottom: 1px solid var(--el-border-color-light);
    background: var(--el-bg-color);
  }

  .editor-toolbar-actions {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-left: auto;
  }

  .editor-title {
    font-weight: 600;
    overflow: hidden;
    max-width: 320px;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .editor-format {
    font-family: monospace;
    font-size: var(--app-font-size-xs);
    color: var(--el-text-color-secondary);
  }

  .editor-version {
    font-size: var(--app-font-size-xs);
    color: var(--el-text-color-secondary);
  }

  .editor-saved-at {
    font-size: var(--app-font-size-xs);
    color: var(--el-text-color-secondary);
  }

  .editor-status {
    display: flex;
    flex: 1;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 12px;
    color: var(--el-text-color-secondary);
  }

  .editor-status--error {
    color: var(--el-color-danger);
  }

  .editor-body {
    flex: 1;
    min-height: 0;
  }

  .editor-body :deep(.editor-surface) {
    height: 100%;
  }
</style>
