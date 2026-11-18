<script setup lang="ts">
  import { computed, nextTick, onMounted, reactive, ref } from 'vue'
  import {
    ElButton, ElCard, ElDialog, ElForm, ElFormItem, ElInput,
    ElMessage, ElMessageBox, ElTable, ElTableColumn, ElTree
  } from 'element-plus'
  import {
    createRoleApi, deleteRoleApi, getPermissionListApi,
    getRoleListApi, updateRoleApi
  } from '@/api/access'
  import type { MenuItem, RoleItem } from '@/api/access/types'
  import { usePermission } from '@/hooks/usePermission'

  const { can } = usePermission()

  interface TreeNode {
    id: number
    label: string
    children: TreeNode[]
  }

  const loading = ref(false)
  const list = ref<RoleItem[]>([])
  const menus = ref<MenuItem[]>([])
  const treeRef = ref<InstanceType<typeof ElTree> | null>(null)
  const dialogVisible = ref(false)
  const editingId = ref<number | null>(null)
  const saving = ref(false)
  const form = reactive({ code: '', name: '', description: '' })

  /** 授权树按后端父子层级构建，操作权限作为对应菜单的子节点自然展示。 */
  const menuTree = computed<TreeNode[]>(() => {
    const nodes = new Map<number, TreeNode>()
    menus.value.forEach((item) => {
      nodes.set(item.id, {
        id: item.id,
        label: item.permission_code ? `${item.title} (${item.permission_code})` : item.title,
        children: []
      })
    })

    const roots: TreeNode[] = []
    menus.value.forEach((item) => {
      const node = nodes.get(item.id)
      if (!node) return
      const parent = item.parent_id ? nodes.get(item.parent_id) : undefined
      if (parent) parent.children.push(node)
      else roots.push(node)
    })
    return roots
  })

  const fetchList = async () => {
    loading.value = true
    try {
      list.value = (await getRoleListApi()).data ?? []
    } catch (error) {
      ElMessage.error(error instanceof Error ? error.message : '角色列表加载失败')
    } finally {
      loading.value = false
    }
  }

  const fetchMenus = async () => {
    try {
      menus.value = (await getPermissionListApi()).data ?? []
    } catch (error) {
      ElMessage.error(error instanceof Error ? error.message : '权限列表加载失败')
    }
  }

  const openCreate = () => {
    editingId.value = null
    Object.assign(form, { code: '', name: '', description: '' })
    dialogVisible.value = true
    void nextTick(() => treeRef.value?.setCheckedKeys([], false))
  }

  const openEdit = (row: RoleItem) => {
    editingId.value = row.id
    Object.assign(form, { code: row.code, name: row.name, description: row.description || '' })
    dialogVisible.value = true
    void nextTick(() => treeRef.value?.setCheckedKeys(row.menu_ids, false))
  }

  const submit = async () => {
    if (!form.code.trim() || !form.name.trim()) {
      ElMessage.warning('请输入角色编码与名称')
      return
    }
    const menuIds = (treeRef.value?.getCheckedKeys(false) as number[]) ?? []
    saving.value = true
    try {
      if (editingId.value) {
        await updateRoleApi(editingId.value, {
          name: form.name.trim(),
          description: form.description || undefined,
          menu_ids: menuIds
        })
      } else {
        await createRoleApi({
          code: form.code.trim(),
          name: form.name.trim(),
          description: form.description || undefined,
          menu_ids: menuIds
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

  const remove = async (row: RoleItem) => {
    try {
      await ElMessageBox.confirm(`确认删除角色“${row.name}”？`, '提示', { type: 'warning' })
      await deleteRoleApi(row.id)
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
    void fetchMenus()
  })
</script>

<template>
  <ElCard shadow="never">
    <template #header>
      <div class="header">
        <span>角色管理</span>
        <ElButton v-if="can('role:create')" type="primary" size="small" @click="openCreate">新增角色</ElButton>
      </div>
    </template>
    <ElTable :data="list" v-loading="loading" border stripe size="small">
      <ElTableColumn prop="code" label="角色编码" width="150" />
      <ElTableColumn prop="name" label="角色名称" width="150" />
      <ElTableColumn prop="description" label="说明" min-width="180" show-overflow-tooltip />
      <ElTableColumn label="授权菜单数" width="110">
        <template #default="{ row }">{{ (row as RoleItem).menu_ids.length }}</template>
      </ElTableColumn>
      <ElTableColumn prop="created_at" label="创建时间" width="170" />
      <ElTableColumn label="操作" width="130" fixed="right">
        <template #default="{ row }">
          <ElButton v-if="can('role:update')" link type="primary" size="small" @click="openEdit(row as RoleItem)">编辑</ElButton>
          <ElButton v-if="can('role:delete')" link type="danger" size="small" @click="remove(row as RoleItem)">删除</ElButton>
        </template>
      </ElTableColumn>
    </ElTable>
    <ElDialog v-model="dialogVisible" :title="editingId ? '编辑角色' : '新增角色'" width="520px">
      <ElForm label-width="80px" size="small">
        <ElFormItem label="角色编码" required><ElInput v-model="form.code" :disabled="!!editingId" /></ElFormItem>
        <ElFormItem label="角色名称" required><ElInput v-model="form.name" /></ElFormItem>
        <ElFormItem label="说明"><ElInput v-model="form.description" /></ElFormItem>
        <ElFormItem label="菜单授权">
          <div class="tree-wrap">
            <ElTree ref="treeRef" :data="menuTree" node-key="id" show-checkbox
              :props="{ label: 'label', children: 'children' }" default-expand-all />
          </div>
        </ElFormItem>
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
  .tree-wrap { width: 100%; max-height: 260px; overflow: auto; border: 1px solid var(--el-border-color); border-radius: 4px; padding: 6px; }
</style>
