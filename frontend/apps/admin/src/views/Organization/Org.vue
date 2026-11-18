<script setup lang="ts">
  import { computed, onMounted, reactive, ref } from 'vue'
  import {
    ElButton, ElCard, ElDialog, ElForm, ElFormItem, ElInput,
    ElMessage, ElMessageBox, ElOption, ElSelect, ElTable, ElTableColumn
  } from 'element-plus'
  import { createOrgApi, deleteOrgApi, getOrgListApi, updateOrgApi } from '@/api/organization'
  import type { OrgItem } from '@/api/organization/types'
  import { usePermission } from '@/hooks/usePermission'

  const { can } = usePermission()

  interface OrgNode extends OrgItem {
    children?: OrgNode[]
  }

  const loading = ref(false)
  const list = ref<OrgItem[]>([])
  const dialogVisible = ref(false)
  const editingId = ref<number | null>(null)
  const saving = ref(false)
  const form = reactive({
    name: '', code: '', parent_id: undefined as number | undefined,
    sort: 0, leader: '', phone: '', remark: ''
  })

  const treeData = computed<OrgNode[]>(() => {
    const nodes = new Map<number, OrgNode>()
    list.value.forEach((item) => nodes.set(item.id, { ...item, children: [] }))
    const roots: OrgNode[] = []
    list.value.forEach((item) => {
      const node = nodes.get(item.id)
      if (!node) return
      const parent = item.parent_id ? nodes.get(item.parent_id) : undefined
      if (parent && parent !== node) parent.children?.push(node)
      else roots.push(node)
    })
    return roots
  })

  const parentOptions = computed(() =>
    list.value.filter((item) => item.id !== editingId.value)
  )

  const fetchList = async () => {
    loading.value = true
    try {
      list.value = (await getOrgListApi()).data ?? []
    } catch (error) {
      ElMessage.error(error instanceof Error ? error.message : '机构列表加载失败')
    } finally {
      loading.value = false
    }
  }

  const openCreate = () => {
    editingId.value = null
    Object.assign(form, {
      name: '', code: '', parent_id: undefined, sort: 0, leader: '', phone: '', remark: ''
    })
    dialogVisible.value = true
  }

  const openEdit = (row: OrgItem) => {
    editingId.value = row.id
    Object.assign(form, {
      name: row.name, code: row.code, parent_id: row.parent_id ?? undefined,
      sort: row.sort, leader: row.leader || '', phone: row.phone || '', remark: row.remark || ''
    })
    dialogVisible.value = true
  }

  const submit = async () => {
    if (!form.name.trim() || (!editingId.value && !form.code.trim())) {
      ElMessage.warning('请输入机构名称与编码')
      return
    }
    saving.value = true
    try {
      if (editingId.value) {
        await updateOrgApi(editingId.value, {
          name: form.name.trim(), parent_id: form.parent_id ?? null,
          sort: form.sort, leader: form.leader || undefined,
          phone: form.phone || undefined, remark: form.remark || undefined
        })
      } else {
        await createOrgApi({
          name: form.name.trim(), code: form.code.trim(),
          parent_id: form.parent_id ?? null, sort: form.sort,
          leader: form.leader || undefined, phone: form.phone || undefined,
          remark: form.remark || undefined
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

  const remove = async (row: OrgItem) => {
    try {
      await ElMessageBox.confirm(`确认删除机构“${row.name}”？`, '提示', { type: 'warning' })
      await deleteOrgApi(row.id)
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
        <span>机构管理</span>
        <ElButton v-if="can('org:create')" type="primary" size="small" @click="openCreate">新增机构</ElButton>
      </div>
    </template>
    <ElTable :data="treeData" v-loading="loading" border size="small" row-key="id"
      :tree-props="{ children: 'children' }" default-expand-all>
      <ElTableColumn label="机构名称" min-width="200">
        <template #default="{ row }">
          <span>{{ (row as OrgItem).name }}</span>
          <span class="code"> {{ (row as OrgItem).code }}</span>
        </template>
      </ElTableColumn>
      <ElTableColumn prop="leader" label="负责人" width="120">
        <template #default="{ row }">{{ (row as OrgItem).leader || '-' }}</template>
      </ElTableColumn>
      <ElTableColumn prop="phone" label="联系电话" width="140">
        <template #default="{ row }">{{ (row as OrgItem).phone || '-' }}</template>
      </ElTableColumn>
      <ElTableColumn prop="sort" label="排序" width="80" />
      <ElTableColumn label="操作" width="140" fixed="right">
        <template #default="{ row }">
          <ElButton v-if="can('org:update')" link type="primary" size="small" @click="openEdit(row as OrgItem)">编辑</ElButton>
          <ElButton v-if="can('org:delete')" link type="danger" size="small" @click="remove(row as OrgItem)">删除</ElButton>
        </template>
      </ElTableColumn>
    </ElTable>
    <ElDialog v-model="dialogVisible" :title="editingId ? '编辑机构' : '新增机构'" width="480px">
      <ElForm label-width="80px" size="small">
        <ElFormItem label="机构名称" required><ElInput v-model="form.name" /></ElFormItem>
        <ElFormItem label="机构编码" required><ElInput v-model="form.code" :disabled="!!editingId" /></ElFormItem>
        <ElFormItem label="上级机构">
          <ElSelect v-model="form.parent_id" clearable style="width: 100%">
            <ElOption v-for="item in parentOptions" :key="item.id" :value="item.id" :label="item.name" />
          </ElSelect>
        </ElFormItem>
        <ElFormItem label="负责人"><ElInput v-model="form.leader" /></ElFormItem>
        <ElFormItem label="联系电话"><ElInput v-model="form.phone" /></ElFormItem>
        <ElFormItem label="排序"><ElInput v-model.number="form.sort" type="number" /></ElFormItem>
        <ElFormItem label="备注"><ElInput v-model="form.remark" type="textarea" :rows="2" /></ElFormItem>
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
  .code { color: var(--el-text-color-secondary); font-size: var(--app-font-size-xs); }
</style>
