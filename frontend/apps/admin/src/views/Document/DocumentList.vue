<script setup lang="ts">
  import { computed, onMounted, reactive, ref } from 'vue'
  import { useRouter } from 'vue-router'
  import {
    ElButton,
    ElCard,
    ElCheckbox,
    ElDialog,
    ElDropdown,
    ElDropdownItem,
    ElDropdownMenu,
    ElForm,
    ElFormItem,
    ElInput,
    ElMessage,
    ElMessageBox,
    ElOption,
    ElPagination,
    ElRadioButton,
    ElRadioGroup,
    ElSelect,
    ElTable,
    ElTableColumn
  } from 'element-plus'
  import {
    createDocumentApi,
    createShareApi,
    deleteDocumentApi,
    getDocumentDownloadApi,
    getDocumentListApi,
    getDocumentVersionsApi,
    getShareListApi,
    restoreDocumentApi,
    revokeShareApi,
    updateDocumentApi,
    uploadDocumentFileApi
  } from '@/api/document'
  import type { DocumentItem, DocumentVersionItem, ShareItem } from '@/api/document/types'
  import { base64ToBytes, buildBlankDocument, bytesToFile, detectDocFormat, formatFileSize, toArrayBuffer } from '@/utils/documentFile'
  import type { EditableDocFormat } from '@/utils/documentFile'
  import { useUserStoreWithOut } from '@/store/modules/user'

  const router = useRouter()
  const userStore = useUserStoreWithOut()
  const canCreate = computed(() => userStore.hasPermission('document:create'))
  const canUpload = computed(() => userStore.hasPermission('document:upload'))
  const canUpdate = computed(() => userStore.hasPermission('document:update'))
  const canDelete = computed(() => userStore.hasPermission('document:delete'))
  const canRestore = computed(() => userStore.hasPermission('document:restore'))
  const canShare = computed(() => userStore.hasPermission('document:share'))
  const loading = ref(false)
  const list = ref<DocumentItem[]>([])
  const total = ref(0)
  const keyword = ref('')
  const showDeleted = ref(false)
  const page = ref(1)
  const pageSize = ref(10)

  const params = computed(() => ({
    page: page.value,
    page_size: pageSize.value,
    keyword: keyword.value || undefined,
    include_deleted: showDeleted.value
  }))

  const fetchList = async () => {
    loading.value = true
    try {
      const res = await getDocumentListApi(params.value)
      list.value = res.data?.items ?? []
      total.value = res.data?.total ?? 0
    } catch (error) {
      ElMessage.error(error instanceof Error ? error.message : '文档列表加载失败')
    } finally {
      loading.value = false
    }
  }

  const handleSearch = () => {
    page.value = 1
    void fetchList()
  }

  const handleSizeChange = () => {
    page.value = 1
    void fetchList()
  }

  const handleReset = () => {
    keyword.value = ''
    showDeleted.value = false
    handleSearch()
  }

  const formatOptions: { value: EditableDocFormat; label: string }[] = [
    { value: 'docx', label: 'Word 文档' },
    { value: 'xlsx', label: 'Excel 表格' },
    { value: 'pptx', label: 'PPT 演示' },
    { value: 'vsdx', label: 'Visio 流程图' }
  ]

  const createVisible = ref(false)
  const creating = ref(false)
  const createForm = reactive({
    title: '',
    format: 'docx' as EditableDocFormat,
    description: ''
  })

  const openCreate = () => {
    createForm.title = ''
    createForm.format = 'docx'
    createForm.description = ''
    createVisible.value = true
  }

  const submitCreate = async () => {
    if (!createForm.title.trim()) {
      ElMessage.warning('请输入文档标题')
      return
    }
    creating.value = true
    try {
      const created = (await createDocumentApi({
        title: createForm.title.trim(),
        description: createForm.description || undefined
      })).data
      const blank = await buildBlankDocument(createForm.format)
      await uploadDocumentFileApi(created.id, bytesToFile(blank.bytes, blank.fileName, blank.mimeType), '创建空白文档')
      createVisible.value = false
      ElMessage.success('文档已创建')
      await fetchList()
      void router.push(`/document-editor/${created.id}`)
    } catch (error) {
      ElMessage.error(error instanceof Error ? error.message : '创建失败')
    } finally {
      creating.value = false
    }
  }

  const fileInput = ref<HTMLInputElement | null>(null)
  const uploadMode = ref<'create' | 'version'>('create')
  const uploadTarget = ref<DocumentItem | null>(null)

  const openUpload = (mode: 'create' | 'version', row?: DocumentItem) => {
    uploadMode.value = mode
    uploadTarget.value = row ?? null
    if (fileInput.value) {
      fileInput.value.value = ''
      fileInput.value.click()
    }
  }

  const handleFileChange = async (event: Event) => {
    const input = event.target as HTMLInputElement
    const file = input.files?.[0]
    if (!file) return
    try {
      let documentId = uploadTarget.value?.id
      if (uploadMode.value === 'create' || !documentId) {
        const created = (await createDocumentApi({
          title: file.name.replace(/\.[^.]+$/, ''),
          description: '通过文件上传创建'
        })).data
        documentId = created.id
      }
      const result = (await uploadDocumentFileApi(documentId, file, '通过文档列表上传')).data
      ElMessage.success(`已上传，当前版本 v${result.version_no}`)
      await fetchList()
      if (uploadMode.value === 'create') void router.push(`/document-editor/${documentId}`)
    } catch (error) {
      ElMessage.error(error instanceof Error ? error.message : '上传失败')
    } finally {
      input.value = ''
    }
  }

  const downloadDocument = async (row: DocumentItem) => {
    try {
      const res = await getDocumentDownloadApi(row.id)
      const data = res.data
      if (!data?.content_base64) {
        ElMessage.warning('文件内容为空，无法下载')
        return
      }
      const bytes = base64ToBytes(data.content_base64)
      const blob = new Blob([toArrayBuffer(bytes)], { type: data.mime_type || 'application/octet-stream' })
      const url = URL.createObjectURL(blob)
      const anchor = document.createElement('a')
      anchor.href = url
      anchor.download = data.file_name || row.title
      anchor.click()
      setTimeout(() => URL.revokeObjectURL(url), 1000)
    } catch (error) {
      ElMessage.error(error instanceof Error ? error.message : '下载失败')
    }
  }

  const openEditor = (row: DocumentItem) => {
    if (!detectDocFormat(row.file_name, row.mime_type)) {
      ElMessage.warning('当前文件不支持在线编辑，请先上传 docx/xlsx/pptx 文件')
      return
    }
    void router.push(`/document-editor/${row.id}`)
  }

  const removeDocument = async (row: DocumentItem) => {
    try {
      await ElMessageBox.confirm(`确认删除文档“${row.title}”？删除后可在回收站恢复。`, '提示', { type: 'warning' })
      await deleteDocumentApi(row.id)
      ElMessage.success('已移入回收站')
      await fetchList()
    } catch (error) {
      if (error !== 'cancel' && error !== 'close') {
        ElMessage.error(error instanceof Error ? error.message : '删除失败')
      }
    }
  }

  const restoreDocument = async (row: DocumentItem) => {
    try {
      await restoreDocumentApi(row.id)
      ElMessage.success('文档已恢复')
      await fetchList()
    } catch (error) {
      ElMessage.error(error instanceof Error ? error.message : '恢复失败')
    }
  }

  const editVisible = ref(false)
  const editing = ref<DocumentItem | null>(null)
  const savingMeta = ref(false)
  const editForm = reactive({
    title: '',
    description: ''
  })

  const openEdit = (row: DocumentItem) => {
    editing.value = row
    editForm.title = row.title
    editForm.description = row.description || ''
    editVisible.value = true
  }

  const submitEdit = async () => {
    if (!editing.value) return
    if (!editForm.title.trim()) {
      ElMessage.warning('请输入文档标题')
      return
    }
    savingMeta.value = true
    try {
      await updateDocumentApi(editing.value.id, {
        title: editForm.title.trim(),
        description: editForm.description || undefined
      })
      editVisible.value = false
      ElMessage.success('文档信息已更新')
      await fetchList()
    } catch (error) {
      ElMessage.error(error instanceof Error ? error.message : '更新失败')
    } finally {
      savingMeta.value = false
    }
  }

  const versionsVisible = ref(false)
  const versionDoc = ref<DocumentItem | null>(null)
  const versions = ref<DocumentVersionItem[]>([])

  const openVersions = async (row: DocumentItem) => {
    versionDoc.value = row
    try {
      versions.value = (await getDocumentVersionsApi(row.id)).data ?? []
      versionsVisible.value = true
    } catch (error) {
      ElMessage.error(error instanceof Error ? error.message : '版本列表加载失败')
    }
  }

  const shareVisible = ref(false)
  const shareDoc = ref<DocumentItem | null>(null)
  const shares = ref<ShareItem[]>([])
  const creatingShare = ref(false)
  const shareForm = reactive({
    permission: 'read' as 'read' | 'write',
    grantedUserId: undefined as number | undefined,
    expiresInHours: undefined as number | undefined
  })

  const shareUrl = (item: ShareItem) => `${window.location.origin}${window.location.pathname}#${item.share_path}`

  const loadShares = async (documentId: number) => {
    try {
      shares.value = (await getShareListApi(documentId)).data ?? []
    } catch (error) {
      ElMessage.error(error instanceof Error ? error.message : '分享列表加载失败')
    }
  }

  const openShare = async (row: DocumentItem) => {
    shareDoc.value = row
    shareForm.permission = 'read'
    shareForm.grantedUserId = undefined
    shareForm.expiresInHours = undefined
    await loadShares(row.id)
    shareVisible.value = true
  }

  const submitShare = async () => {
    if (!shareDoc.value) return
    creatingShare.value = true
    try {
      await createShareApi({
        document_id: shareDoc.value.id,
        permission: shareForm.permission,
        granted_user_id: shareForm.grantedUserId,
        expires_in_hours: shareForm.expiresInHours
      })
      ElMessage.success('分享已创建')
      await loadShares(shareDoc.value.id)
    } catch (error) {
      ElMessage.error(error instanceof Error ? error.message : '创建分享失败')
    } finally {
      creatingShare.value = false
    }
  }

  const copyShare = async (item: ShareItem) => {
    try {
      await navigator.clipboard.writeText(shareUrl(item))
      ElMessage.success('分享链接已复制')
    } catch {
      ElMessage.warning('浏览器拒绝复制，请手动复制链接')
    }
  }

  const revoke = async (item: ShareItem) => {
    try {
      await ElMessageBox.confirm('确认撤销该分享？链接将立即失效。', '提示', { type: 'warning' })
      await revokeShareApi(item.id)
      if (shareDoc.value) await loadShares(shareDoc.value.id)
      ElMessage.success('分享已撤销')
    } catch (error) {
      if (error !== 'cancel' && error !== 'close') {
        ElMessage.error(error instanceof Error ? error.message : '撤销失败')
      }
    }
  }

  const handleMoreCommand = (command: string, row: DocumentItem) => {
    switch (command) {
      case 'restore':
        void restoreDocument(row)
        break
      case 'info':
        openEdit(row)
        break
      case 'uploadVersion':
        openUpload('version', row)
        break
      case 'versions':
        void openVersions(row)
        break
      case 'download':
        void downloadDocument(row)
        break
      case 'delete':
        void removeDocument(row)
        break
    }
  }

  onMounted(() => {
    void fetchList()
  })
</script>

<template>
  <div class="document-list">
    <ElCard shadow="never">
      <template #header>
        <div class="card-header">
          <span>文档列表</span>
          <div>
            <ElButton v-if="canCreate" type="primary" size="small" @click="openCreate">新建空白文档</ElButton>
            <ElButton v-if="canUpload" size="small" @click="openUpload('create')">上传文件</ElButton>
            <ElButton size="small" :loading="loading" @click="fetchList()">刷新</ElButton>
          </div>
        </div>
      </template>

      <ElForm inline size="small" class="search-form" @submit.prevent="handleSearch">
        <ElFormItem label="关键词">
          <ElInput v-model="keyword" placeholder="标题或描述" clearable style="width: 180px" @keyup.enter="handleSearch" />
        </ElFormItem>
        <ElFormItem>
          <ElCheckbox v-model="showDeleted" @change="handleSearch">回收站</ElCheckbox>
        </ElFormItem>
        <ElFormItem>
          <ElButton type="primary" @click="handleSearch">查询</ElButton>
          <ElButton @click="handleReset">重置</ElButton>
        </ElFormItem>
      </ElForm>

      <ElTable :data="list" v-loading="loading" border stripe size="small">
        <ElTableColumn prop="title" label="文档标题" min-width="180" show-overflow-tooltip />
        <ElTableColumn label="版本" width="80">
          <template #default="{ row }">v{{ (row as DocumentItem).current_version }}</template>
        </ElTableColumn>
        <ElTableColumn label="文件" min-width="160" show-overflow-tooltip>
          <template #default="{ row }">
            <span>{{ (row as DocumentItem).file_name || '暂无文件' }}</span>
            <span v-if="(row as DocumentItem).file_size" class="file-size">
              {{ formatFileSize((row as DocumentItem).file_size) }}
            </span>
          </template>
        </ElTableColumn>
        <ElTableColumn prop="updated_at" label="更新时间" width="170" />
        <ElTableColumn label="操作" width="220" fixed="right">
          <template #default="{ row }">
            <template v-if="(row as DocumentItem).deleted_at">
              <ElButton v-if="canRestore" link type="primary" size="small" @click="restoreDocument(row as DocumentItem)">恢复</ElButton>
            </template>
            <template v-else>
              <ElButton v-if="canUpdate" link type="primary" size="small" @click="openEditor(row as DocumentItem)">编辑</ElButton>
              <ElButton v-if="canShare" link size="small" @click="openShare(row as DocumentItem)">分享</ElButton>
              <ElDropdown trigger="click" @command="handleMoreCommand(String($event), row as DocumentItem)">
                <ElButton link size="small">更多 ▾</ElButton>
                <template #dropdown>
                  <ElDropdownMenu>
                    <ElDropdownItem v-if="canUpdate" command="info">文档信息</ElDropdownItem>
                    <ElDropdownItem v-if="canUpload" command="uploadVersion">上传新版本</ElDropdownItem>
                    <ElDropdownItem command="versions">版本历史</ElDropdownItem>
                    <ElDropdownItem command="download">下载文件</ElDropdownItem>
                    <ElDropdownItem v-if="canDelete" command="delete" divided>删除</ElDropdownItem>
                  </ElDropdownMenu>
                </template>
              </ElDropdown>
            </template>
          </template>
        </ElTableColumn>
      </ElTable>

      <div class="pagination">
        <ElPagination
          v-model:current-page="page"
          v-model:page-size="pageSize"
          :total="total"
          :page-sizes="[10, 20, 50]"
          layout="total, sizes, prev, pager, next"
          background
          @size-change="handleSizeChange"
          @current-change="fetchList()"
        />
      </div>
    </ElCard>

    <input ref="fileInput" type="file" class="hidden-input" @change="handleFileChange" />

    <ElDialog v-model="createVisible" title="新建空白文档" width="460px">
      <ElForm label-width="80px" size="small">
        <ElFormItem label="标题" required>
          <ElInput v-model="createForm.title" placeholder="请输入文档标题" />
        </ElFormItem>
        <ElFormItem label="类型">
          <ElRadioGroup v-model="createForm.format">
            <ElRadioButton v-for="option in formatOptions" :key="option.value" :value="option.value">
              {{ option.label }}
            </ElRadioButton>
          </ElRadioGroup>
        </ElFormItem>
        <ElFormItem label="描述">
          <ElInput v-model="createForm.description" type="textarea" :rows="2" placeholder="可选" />
        </ElFormItem>
      </ElForm>
      <template #footer>
        <ElButton size="small" @click="createVisible = false">取消</ElButton>
        <ElButton type="primary" size="small" :loading="creating" @click="submitCreate">创建并打开</ElButton>
      </template>
    </ElDialog>

    <ElDialog v-model="editVisible" title="文档信息" width="480px">
      <ElForm label-width="80px" size="small">
        <ElFormItem label="标题" required><ElInput v-model="editForm.title" /></ElFormItem>
        <ElFormItem label="描述"><ElInput v-model="editForm.description" type="textarea" :rows="3" /></ElFormItem>
      </ElForm>
      <template #footer>
        <ElButton size="small" @click="editVisible = false">取消</ElButton>
        <ElButton type="primary" size="small" :loading="savingMeta" @click="submitEdit">保存</ElButton>
      </template>
    </ElDialog>

    <ElDialog v-model="versionsVisible" :title="`版本历史 - ${versionDoc?.title || ''}`" width="640px">
      <ElTable :data="versions" size="small" border>
        <ElTableColumn prop="version_no" label="版本" width="80">
          <template #default="{ row }">v{{ (row as DocumentVersionItem).version_no }}</template>
        </ElTableColumn>
        <ElTableColumn prop="change_log" label="变更说明" min-width="180">
          <template #default="{ row }">{{ (row as DocumentVersionItem).change_log || '-' }}</template>
        </ElTableColumn>
        <ElTableColumn label="大小" width="100">
          <template #default="{ row }">{{ formatFileSize((row as DocumentVersionItem).file_size) }}</template>
        </ElTableColumn>
        <ElTableColumn prop="created_by" label="操作人" width="90" />
        <ElTableColumn prop="created_at" label="时间" width="170" />
      </ElTable>
    </ElDialog>

    <ElDialog v-model="shareVisible" :title="`分享管理 - ${shareDoc?.title || ''}`" width="680px">
      <ElForm inline size="small" class="share-form">
        <ElFormItem label="权限">
          <ElRadioGroup v-model="shareForm.permission">
            <ElRadioButton value="read">只读</ElRadioButton>
            <ElRadioButton value="write">可编辑</ElRadioButton>
          </ElRadioGroup>
        </ElFormItem>
        <ElFormItem label="指定用户ID">
          <ElInput v-model.number="shareForm.grantedUserId" placeholder="留空为公开链接" style="width: 160px" />
        </ElFormItem>
        <ElFormItem label="有效期">
          <ElSelect v-model="shareForm.expiresInHours" clearable placeholder="永久" style="width: 110px">
            <ElOption :value="1" label="1 小时" />
            <ElOption :value="24" label="24 小时" />
            <ElOption :value="168" label="7 天" />
          </ElSelect>
        </ElFormItem>
        <ElFormItem>
          <ElButton v-if="canShare" type="primary" :loading="creatingShare" @click="submitShare">创建分享</ElButton>
        </ElFormItem>
      </ElForm>
      <ElTable :data="shares" size="small" border>
        <ElTableColumn label="类型" width="110">
          <template #default="{ row }">
            {{ (row as ShareItem).is_public ? '公开链接' : `用户 ${(row as ShareItem).granted_user_id}` }}
          </template>
        </ElTableColumn>
        <ElTableColumn label="权限" width="80">
          <template #default="{ row }">
            {{ (row as ShareItem).permission === 'read' ? '只读' : '可编辑' }}
          </template>
        </ElTableColumn>
        <ElTableColumn label="链接" min-width="240" show-overflow-tooltip>
          <template #default="{ row }">{{ shareUrl(row as ShareItem) }}</template>
        </ElTableColumn>
        <ElTableColumn prop="expires_at" label="过期时间" width="170" />
        <ElTableColumn label="操作" width="140">
          <template #default="{ row }">
            <ElButton link type="primary" size="small" @click="copyShare(row as ShareItem)">复制</ElButton>
            <ElButton v-if="canShare" link type="danger" size="small" @click="revoke(row as ShareItem)">撤销</ElButton>
          </template>
        </ElTableColumn>
      </ElTable>
    </ElDialog>
  </div>
</template>

<style scoped>
  .card-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
  }

  .search-form {
    margin-bottom: 12px;
  }

  .file-size {
    margin-left: 6px;
  }

  .pagination {
    display: flex;
    justify-content: flex-end;
    margin-top: 12px;
  }

  .share-form {
    margin-bottom: 12px;
  }

  .hidden-input {
    display: none;
  }

  :deep(.el-button.is-link) {
    vertical-align: middle;
  }

  :deep(.el-dropdown) {
    display: inline-flex;
    vertical-align: middle;
  }
</style>
