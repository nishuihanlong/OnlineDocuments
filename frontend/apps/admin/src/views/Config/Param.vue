<script setup lang="ts">
  import { onMounted, reactive, ref } from 'vue'
  import {
    ElButton, ElCard, ElDialog, ElForm, ElFormItem, ElInput,
    ElMessage, ElMessageBox, ElSwitch, ElTable, ElTableColumn
  } from 'element-plus'
  import { createConfigApi, deleteConfigApi, getConfigListApi, updateConfigApi } from '@/api/system'
  import type { ConfigItem } from '@/api/system/types'
  import { usePermission } from '@/hooks/usePermission'

  const { can } = usePermission()

  const WATERMARK_KEY = 'watermark.enabled'

  const loading = ref(false)
  const list = ref<ConfigItem[]>([])
  const keyword = ref('')
  const dialogVisible = ref(false)
  const editingId = ref<number | null>(null)
  const saving = ref(false)
  const form = reactive({ key: '', name: '', value: '', remark: '' })

  const fetchList = async () => {
    loading.value = true
    try {
      const res = await getConfigListApi({ keyword: keyword.value || undefined, page: 1, page_size: 100 })
      list.value = res.data?.items ?? []
    } catch (error) {
      ElMessage.error(error instanceof Error ? error.message : '参数加载失败')
    } finally {
      loading.value = false
    }
  }

  const openCreate = () => {
    editingId.value = null
    Object.assign(form, { key: '', name: '', value: '', remark: '' })
    dialogVisible.value = true
  }

  const openEdit = (row: ConfigItem) => {
    editingId.value = row.id
    Object.assign(form, {
      key: row.key, name: row.name, value: row.value || '', remark: row.remark || ''
    })
    dialogVisible.value = true
  }

  const submit = async () => {
    if (!form.key.trim()) {
      ElMessage.warning('请输入参数键')
      return
    }
    saving.value = true
    try {
      if (editingId.value) {
        await updateConfigApi(editingId.value, {
          name: form.name, value: form.value, remark: form.remark || undefined
        })
      } else {
        await createConfigApi({
          key: form.key.trim(), name: form.name, value: form.value, remark: form.remark || undefined
        })
      }
      dialogVisible.value = false
      ElMessage.success('已保存')
      await fetchList()
    } catch (error) {
      ElMessage.error(error instanceof Error ? error.message : '保存失败')
    } finally {
      saving.value = false
    }
  }

  const isWatermarkRow = (row: ConfigItem) => row.key === WATERMARK_KEY

  const toggleWatermark = async (row: ConfigItem, value: unknown) => {
    try {
      await updateConfigApi(row.id, { value: value ? '1' : '0' })
      row.value = value ? '1' : '0'
      ElMessage.success('水印设置已更新，刷新页面后对新页面生效')
    } catch (error) {
      ElMessage.error(error instanceof Error ? error.message : '设置失败')
    }
  }

  const remove = async (row: ConfigItem) => {
    try {
      await ElMessageBox.confirm(`确认删除参数“${row.key}”？`, '提示', { type: 'warning' })
      await deleteConfigApi(row.id)
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
        <span>参数管理</span>
        <div>
          <ElInput v-model="keyword" placeholder="参数键/名称" clearable style="width: 180px" @keyup.enter="fetchList()" />
          <ElButton size="small" @click="fetchList()">查询</ElButton>
          <ElButton v-if="can('config:create')" type="primary" size="small" @click="openCreate">新增参数</ElButton>
        </div>
      </div>
    </template>
    <ElTable :data="list" v-loading="loading" border stripe size="small">
      <ElTableColumn prop="key" label="参数键" width="180" />
      <ElTableColumn prop="name" label="参数名称" width="160" />
      <ElTableColumn prop="value" label="参数值" min-width="200" show-overflow-tooltip>
        <template #default="{ row }">
          <ElSwitch
            v-if="isWatermarkRow(row as ConfigItem)"
            :model-value="(row as ConfigItem).value === '1'"
            :disabled="!can('config:update')"
            inline-prompt
            active-text="开"
            inactive-text="关"
            @update:model-value="toggleWatermark(row as ConfigItem, $event)"
          />
          <span v-else>{{ (row as ConfigItem).value }}</span>
        </template>
      </ElTableColumn>
      <ElTableColumn prop="remark" label="备注" min-width="160" show-overflow-tooltip />
      <ElTableColumn prop="updated_at" label="更新时间" width="170" />
      <ElTableColumn label="操作" width="130" fixed="right">
        <template #default="{ row }">
          <ElButton v-if="can('config:update')" link type="primary" size="small" @click="openEdit(row as ConfigItem)">编辑</ElButton>
          <ElButton v-if="can('config:delete') && !isWatermarkRow(row as ConfigItem)" link type="danger" size="small" @click="remove(row as ConfigItem)">删除</ElButton>
        </template>
      </ElTableColumn>
    </ElTable>
    <ElDialog v-model="dialogVisible" :title="editingId ? '编辑参数' : '新增参数'" width="480px">
      <ElForm label-width="80px" size="small">
        <ElFormItem label="参数键" required><ElInput v-model="form.key" :disabled="!!editingId" /></ElFormItem>
        <ElFormItem label="名称"><ElInput v-model="form.name" /></ElFormItem>
        <ElFormItem label="参数值"><ElInput v-model="form.value" type="textarea" :rows="3" /></ElFormItem>
        <ElFormItem label="备注"><ElInput v-model="form.remark" /></ElFormItem>
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
