<script setup lang="ts">
  import { onMounted, reactive, ref } from 'vue'
  import {
    ElButton, ElCard, ElDialog, ElForm, ElFormItem, ElInput,
    ElMessage, ElMessageBox, ElSwitch, ElTable, ElTableColumn
  } from 'element-plus'
  import { createJobApi, deleteJobApi, getJobListApi, runJobApi, updateJobApi } from '@/api/system'
  import type { JobItem } from '@/api/system/types'
  import { usePermission } from '@/hooks/usePermission'

  const { can } = usePermission()

  const loading = ref(false)
  const list = ref<JobItem[]>([])
  const dialogVisible = ref(false)
  const editingId = ref<number | null>(null)
  const saving = ref(false)
  const form = reactive({ name: '', code: '', interval_seconds: 60, enabled: false })

  const fetchList = async () => {
    loading.value = true
    try {
      list.value = (await getJobListApi()).data ?? []
    } catch (error) {
      ElMessage.error(error instanceof Error ? error.message : '任务加载失败')
    } finally {
      loading.value = false
    }
  }

  const openCreate = () => {
    editingId.value = null
    Object.assign(form, { name: '', code: '', interval_seconds: 60, enabled: false })
    dialogVisible.value = true
  }

  const openEdit = (row: JobItem) => {
    editingId.value = row.id
    Object.assign(form, {
      name: row.name, code: row.code, interval_seconds: row.interval_seconds, enabled: row.enabled
    })
    dialogVisible.value = true
  }

  const submit = async () => {
    if (!form.name.trim() || !form.code.trim()) {
      ElMessage.warning('请输入任务名称与编码')
      return
    }
    saving.value = true
    try {
      const payload = {
        name: form.name.trim(), code: form.code.trim(),
        interval_seconds: form.interval_seconds, enabled: form.enabled
      }
      if (editingId.value) await updateJobApi(editingId.value, payload)
      else await createJobApi(payload)
      dialogVisible.value = false
      ElMessage.success('已保存')
      await fetchList()
    } catch (error) {
      ElMessage.error(error instanceof Error ? error.message : '保存失败')
    } finally {
      saving.value = false
    }
  }

  const run = async (row: JobItem) => {
    try {
      await runJobApi(row.id)
      ElMessage.success('任务已执行')
      await fetchList()
    } catch (error) {
      ElMessage.error(error instanceof Error ? error.message : '执行失败')
    }
  }

  const remove = async (row: JobItem) => {
    try {
      await ElMessageBox.confirm(`确认删除任务“${row.name}”？`, '提示', { type: 'warning' })
      await deleteJobApi(row.id)
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
        <span>定时任务</span>
        <ElButton v-if="can('job:create')" type="primary" size="small" @click="openCreate">新增任务</ElButton>
      </div>
    </template>
    <ElTable :data="list" v-loading="loading" border stripe size="small">
      <ElTableColumn prop="name" label="任务名称" width="160" />
      <ElTableColumn prop="code" label="任务编码" width="160" />
      <ElTableColumn label="间隔(秒)" width="100">
        <template #default="{ row }">{{ (row as JobItem).interval_seconds }}</template>
      </ElTableColumn>
      <ElTableColumn label="启用" width="80">
        <template #default="{ row }">{{ (row as JobItem).enabled ? '是' : '否' }}</template>
      </ElTableColumn>
      <ElTableColumn prop="last_run_at" label="上次执行" width="180" />
      <ElTableColumn label="操作" width="180" fixed="right">
        <template #default="{ row }">
          <ElButton v-if="can('job:run')" link type="primary" size="small" @click="run(row as JobItem)">执行</ElButton>
          <ElButton v-if="can('job:update')" link size="small" @click="openEdit(row as JobItem)">编辑</ElButton>
          <ElButton v-if="can('job:delete')" link type="danger" size="small" @click="remove(row as JobItem)">删除</ElButton>
        </template>
      </ElTableColumn>
    </ElTable>
    <ElDialog v-model="dialogVisible" :title="editingId ? '编辑任务' : '新增任务'" width="480px">
      <ElForm label-width="90px" size="small">
        <ElFormItem label="任务名称" required><ElInput v-model="form.name" /></ElFormItem>
        <ElFormItem label="任务编码" required><ElInput v-model="form.code" :disabled="!!editingId" /></ElFormItem>
        <ElFormItem label="间隔(秒)"><ElInput v-model.number="form.interval_seconds" type="number" :min="10" /></ElFormItem>
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
  .header { display: flex; align-items: center; justify-content: space-between; }
</style>
