<script setup lang="ts">
  import { onMounted, reactive, ref } from 'vue'
  import {
    ElButton, ElCard, ElDialog, ElForm, ElFormItem, ElInput,
    ElMessage, ElMessageBox, ElOption, ElSelect, ElSwitch, ElTable, ElTableColumn
  } from 'element-plus'
  import { createNoticeApi, deleteNoticeApi, getNoticeListApi, updateNoticeApi } from '@/api/system'
  import type { NoticeItem } from '@/api/system/types'
  import { usePermission } from '@/hooks/usePermission'

  const { can } = usePermission()

  const loading = ref(false)
  const list = ref<NoticeItem[]>([])
  const keyword = ref('')
  const dialogVisible = ref(false)
  const editingId = ref<number | null>(null)
  const saving = ref(false)
  const form = reactive({ title: '', content: '', type: 'notice' as 'notice' | 'announcement', enabled: true })

  const fetchList = async () => {
    loading.value = true
    try {
      const res = await getNoticeListApi({ keyword: keyword.value || undefined, page: 1, page_size: 100 })
      list.value = res.data?.items ?? []
    } catch (error) {
      ElMessage.error(error instanceof Error ? error.message : '公告加载失败')
    } finally {
      loading.value = false
    }
  }

  const openCreate = () => {
    editingId.value = null
    Object.assign(form, { title: '', content: '', type: 'notice', enabled: true })
    dialogVisible.value = true
  }

  const openEdit = (row: NoticeItem) => {
    editingId.value = row.id
    Object.assign(form, {
      title: row.title, content: row.content || '', type: row.type, enabled: row.enabled
    })
    dialogVisible.value = true
  }

  const submit = async () => {
    if (!form.title.trim()) {
      ElMessage.warning('请输入标题')
      return
    }
    saving.value = true
    try {
      const payload = { title: form.title.trim(), content: form.content, type: form.type, enabled: form.enabled }
      if (editingId.value) await updateNoticeApi(editingId.value, payload)
      else await createNoticeApi(payload)
      dialogVisible.value = false
      ElMessage.success('已保存')
      await fetchList()
    } catch (error) {
      ElMessage.error(error instanceof Error ? error.message : '保存失败')
    } finally {
      saving.value = false
    }
  }

  const remove = async (row: NoticeItem) => {
    try {
      await ElMessageBox.confirm(`确认删除公告“${row.title}”？`, '提示', { type: 'warning' })
      await deleteNoticeApi(row.id)
      ElMessage.success('已删除')
      await fetchList()
    } catch (error) {
      if (error !== 'cancel' && error !== 'close') {
        ElMessage.error(error instanceof Error ? error.message : '删除失败')
      }
    }
  }

  onMounted(() => { void fetchList() })
</script>

<template>
  <ElCard shadow="never">
    <template #header>
      <div class="header">
        <span>通知公告</span>
        <div>
          <ElInput v-model="keyword" placeholder="标题" clearable style="width: 180px" @keyup.enter="fetchList()" />
          <ElButton size="small" @click="fetchList()">查询</ElButton>
          <ElButton v-if="can('notice:create')" type="primary" size="small" @click="openCreate">新增公告</ElButton>
        </div>
      </div>
    </template>
    <ElTable :data="list" v-loading="loading" border stripe size="small">
      <ElTableColumn prop="title" label="标题" min-width="200" show-overflow-tooltip />
      <ElTableColumn label="类型" width="110">
        <template #default="{ row }">
          {{ (row as NoticeItem).type === 'announcement' ? '系统公告' : '通知' }}
        </template>
      </ElTableColumn>
      <ElTableColumn label="启用" width="80">
        <template #default="{ row }">{{ (row as NoticeItem).enabled ? '是' : '否' }}</template>
      </ElTableColumn>
      <ElTableColumn prop="created_at" label="创建时间" width="170" />
      <ElTableColumn label="操作" width="130" fixed="right">
        <template #default="{ row }">
          <ElButton v-if="can('notice:update')" link type="primary" size="small" @click="openEdit(row as NoticeItem)">编辑</ElButton>
          <ElButton v-if="can('notice:delete')" link type="danger" size="small" @click="remove(row as NoticeItem)">删除</ElButton>
        </template>
      </ElTableColumn>
    </ElTable>
    <ElDialog v-model="dialogVisible" :title="editingId ? '编辑公告' : '新增公告'" width="520px">
      <ElForm label-width="70px" size="small">
        <ElFormItem label="标题" required><ElInput v-model="form.title" /></ElFormItem>
        <ElFormItem label="类型">
          <ElSelect v-model="form.type" style="width: 140px">
            <ElOption value="notice" label="通知" />
            <ElOption value="announcement" label="系统公告" />
          </ElSelect>
        </ElFormItem>
        <ElFormItem label="内容"><ElInput v-model="form.content" type="textarea" :rows="4" /></ElFormItem>
        <ElFormItem label="启用"><ElSwitch v-model="form.enabled" /></ElFormItem>
      </ElForm>
      <template #footer>
        <ElButton size="small" @click="dialogVisible = false">取消</ElButton>
        <ElButton type="primary" size="small" :loading="saving" @click="submit">保存</ElButton>
      </template>
    </ElDialog>
  </ElCard>
</template>

<style scoped>
  .header { display: flex; align-items: center; justify-content: space-between; gap: 8px; }
</style>
