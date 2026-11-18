<script setup lang="ts">
  import { computed, onMounted, reactive, ref } from 'vue'
  import {
    ElButton, ElCard, ElDialog, ElForm, ElFormItem, ElInput,
    ElMessage, ElMessageBox, ElOption, ElSelect, ElTable, ElTableColumn
  } from 'element-plus'
  import {
    createDeptApi, deleteDeptApi, getDeptListApi, getOrgListApi, updateDeptApi
  } from '@/api/organization'
  import type { DeptItem, OrgItem } from '@/api/organization/types'
  import { usePermission } from '@/hooks/usePermission'

  const { can } = usePermission()

  interface DeptNode extends DeptItem {
    children?: DeptNode[]
  }

  const loading = ref(false)
  const list = ref<DeptItem[]>([])
  const orgs = ref<OrgItem[]>([])
  const dialogVisible = ref(false)
  const editingId = ref<number | null>(null)
  const saving = ref(false)
  const form = reactive({
    name: '', code: '', org_id: undefined as number | undefined,
    parent_id: undefined as number | undefined, sort: 0, leader: '', phone: ''
  })

  const treeData = computed<DeptNode[]>(() => {
    const nodes = new Map<number, DeptNode>()
    list.value.forEach((item) => nodes.set(item.id, { ...item, children: [] }))
    const roots: DeptNode[] = []
    list.value.forEach((item) => {
      const node = nodes.get(item.id)
      if (!node) return
      const parent = item.parent_id ? nodes.get(item.parent_id) : undefined
      if (parent && parent !== node) parent.children?.push(node)
      else roots.push(node)
    })
    return roots
  })

  const parentOptions = computed(() => list.value.filter((item) => item.id !== editingId.value))

  const orgName = (orgId?: number | null) =>
    orgs.value.find((item) => item.id === orgId)?.name || '-'

  const fetchOrgList = async () => {
    try {
      orgs.value = (await getOrgListApi()).data ?? []
    } catch {
      orgs.value = []
    }
  }

  const fetchList = async () => {
    loading.value = true
    try {
      list.value = (await getDeptListApi()).data ?? []
    } catch (error) {
      ElMessage.error(error instanceof Error ? error.message : '部门列表加载失败')
    } finally {
      loading.value = false
    }
  }

  const openCreate = () => {
    editingId.value = null
    Object.assign(form, {
      name: '', code: '', org_id: undefined, parent_id: undefined,
      sort: 0, leader: '', phone: ''
    })
    dialogVisible.value = true
  }

  const openEdit = (row: DeptItem) => {
    editingId.value = row.id
    Object.assign(form, {
      name: row.name, code: row.code, org_id: row.org_id ?? undefined,
      parent_id: row.parent_id ?? undefined, sort: row.sort,
      leader: row.leader || '', phone: row.phone || ''
    })
    dialogVisible.value = true
  }

  const submit = async () => {
    if (!form.name.trim()) {
      ElMessage.warning('请输入部门名称')
      return
    }
    saving.value = true
    try {
      const payload = {
        name: form.name.trim(), code: form.code.trim(),
        org_id: form.org_id ?? null, parent_id: form.parent_id ?? null,
        sort: form.sort, leader: form.leader || undefined, phone: form.phone || undefined
      }
      if (editingId.value) await updateDeptApi(editingId.value, payload)
      else await createDeptApi(payload)
      dialogVisible.value = false
      ElMessage.success('已保存')
      await fetchList()
    } catch (error) {
      ElMessage.error(error instanceof Error ? error.message : '保存失败')
    } finally {
      saving.value = false
    }
  }

  const remove = async (row: DeptItem) => {
    try {
      await ElMessageBox.confirm(`确认删除部门“${row.name}”？`, '提示', { type: 'warning' })
      await deleteDeptApi(row.id)
      ElMessage.success('已删除')
      await fetchList()
    } catch (error) {
      if (error !== 'cancel' && error !== 'close') {
        ElMessage.error(error instanceof Error ? error.message : '删除失败')
      }
    }
  }

  onMounted(() => {
    void fetchList()
    void fetchOrgList()
  })
</script>

<template>
  <ElCard shadow="never">
    <template #header>
      <div class="header">
        <span>部门管理</span>
        <ElButton v-if="can('dept:create')" type="primary" size="small" @click="openCreate">新增部门</ElButton>
      </div>
    </template>
    <ElTable :data="treeData" v-loading="loading" border size="small" row-key="id"
      :tree-props="{ children: 'children' }" default-expand-all>
      <ElTableColumn label="部门名称" min-width="180">
        <template #default="{ row }">
          <span>{{ (row as DeptItem).name }}</span>
          <span v-if="(row as DeptItem).code" class="code"> {{ (row as DeptItem).code }}</span>
        </template>
      </ElTableColumn>
      <ElTableColumn label="所属机构" width="140">
        <template #default="{ row }">{{ orgName((row as DeptItem).org_id) }}</template>
      </ElTableColumn>
      <ElTableColumn label="负责人" width="110">
        <template #default="{ row }">{{ (row as DeptItem).leader || '-' }}</template>
      </ElTableColumn>
      <ElTableColumn label="联系电话" width="130">
        <template #default="{ row }">{{ (row as DeptItem).phone || '-' }}</template>
      </ElTableColumn>
      <ElTableColumn prop="sort" label="排序" width="70" />
      <ElTableColumn label="操作" width="140" fixed="right">
        <template #default="{ row }">
          <ElButton v-if="can('dept:update')" link type="primary" size="small" @click="openEdit(row as DeptItem)">编辑</ElButton>
          <ElButton v-if="can('dept:delete')" link type="danger" size="small" @click="remove(row as DeptItem)">删除</ElButton>
        </template>
      </ElTableColumn>
    </ElTable>
    <ElDialog v-model="dialogVisible" :title="editingId ? '编辑部门' : '新增部门'" width="480px">
      <ElForm label-width="80px" size="small">
        <ElFormItem label="部门名称" required><ElInput v-model="form.name" /></ElFormItem>
        <ElFormItem label="部门编码"><ElInput v-model="form.code" /></ElFormItem>
        <ElFormItem label="所属机构">
          <ElSelect v-model="form.org_id" clearable style="width: 100%">
            <ElOption v-for="item in orgs" :key="item.id" :value="item.id" :label="item.name" />
          </ElSelect>
        </ElFormItem>
        <ElFormItem label="上级部门">
          <ElSelect v-model="form.parent_id" clearable style="width: 100%">
            <ElOption v-for="item in parentOptions" :key="item.id" :value="item.id" :label="item.name" />
          </ElSelect>
        </ElFormItem>
        <ElFormItem label="负责人"><ElInput v-model="form.leader" /></ElFormItem>
        <ElFormItem label="联系电话"><ElInput v-model="form.phone" /></ElFormItem>
        <ElFormItem label="排序"><ElInput v-model.number="form.sort" type="number" /></ElFormItem>
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
