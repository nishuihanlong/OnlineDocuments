<script setup lang="ts">
  import { computed, onMounted, reactive, ref } from 'vue'
  import {
    ElButton, ElCard, ElDialog, ElDivider, ElForm, ElFormItem, ElInput,
    ElMessage, ElMessageBox, ElOption, ElSelect, ElSwitch, ElTable,
    ElTableColumn, ElTag
  } from 'element-plus'
  import {
    createPermissionApi, deletePermissionApi,
    getPermissionListApi, updatePermissionApi
  } from '@/api/access'
  import type { MenuItem, MenuCreateIn, MenuUpdateIn } from '@/api/access/types'
  import { usePermission } from '@/hooks/usePermission'

  const { can } = usePermission()

  interface MenuNode extends MenuItem {
    children?: MenuNode[]
  }

  type MenuNodeType = 'directory' | 'page' | 'action'

  const NODE_TYPE_META: Record<
    MenuNodeType,
    { label: string; icon: string; tagType: 'primary' | 'success' | 'warning' }
  > = {
    directory: { label: '目录', icon: 'mdi:folder-outline', tagType: 'primary' },
    page: { label: '菜单', icon: 'mdi:file-document-outline', tagType: 'success' },
    action: { label: '按钮', icon: 'mdi:gesture-tap-button', tagType: 'warning' }
  }

  const loading = ref(false)
  const keyword = ref('')
  const list = ref<MenuItem[]>([])
  const dialogVisible = ref(false)
  const editingId = ref<number | null>(null)
  const saving = ref(false)
  const form = reactive({
    name: '', title: '', path: '', component: '', parent_id: undefined as number | undefined,
    permission_code: '', icon: '', sort: 0, hidden: false, enabled: true
  })

  /** 节点类型：## 为操作权限，# 为目录，其余为页面菜单。 */
  const typeOf = (row: MenuItem): MenuNodeType => {
    if (row.component === '##') return 'action'
    if (row.component === '#') return 'directory'
    return 'page'
  }

  const typeMetaOf = (row: MenuItem) => NODE_TYPE_META[typeOf(row)]

  const parentOptions = computed(() => list.value.filter((item) => !item.parent_id))

  const treeData = computed<MenuNode[]>(() => {
    const nodes = new Map<number, MenuNode>()
    list.value.forEach((item) => nodes.set(item.id, { ...item, children: [] }))
    const roots: MenuNode[] = []
    list.value.forEach((item) => {
      const node = nodes.get(item.id)
      if (!node) return
      const parent = item.parent_id ? nodes.get(item.parent_id) : undefined
      if (parent && parent !== node) parent.children?.push(node)
      else roots.push(node)
    })
    return roots
  })

  /** 关键字过滤：命中节点保留其祖先链，便于在折叠状态下定位。 */
  const filteredTreeData = computed<MenuNode[]>(() => {
    const kw = keyword.value.trim().toLowerCase()
    if (!kw) return treeData.value
    const filterNodes = (nodes: MenuNode[]): MenuNode[] =>
      nodes.flatMap((node) => {
        const children = filterNodes(node.children ?? [])
        const matched =
          node.title.toLowerCase().includes(kw) ||
          node.name.toLowerCase().includes(kw) ||
          (node.permission_code ?? '').toLowerCase().includes(kw)
        return matched || children.length ? [{ ...node, children }] : []
      })
    return filterNodes(treeData.value)
  })

  const rowClassName = ({ row }: { row: MenuItem }) => {
    if (!row.parent_id) return 'root-row'
    if (typeOf(row) === 'action') return 'action-row'
    return ''
  }

  const fetchList = async () => {
    loading.value = true
    try {
      list.value = (await getPermissionListApi()).data ?? []
    } catch (error) {
      ElMessage.error(error instanceof Error ? error.message : '权限列表加载失败')
    } finally {
      loading.value = false
    }
  }

  const openCreate = (parentId?: number) => {
    editingId.value = null
    Object.assign(form, {
      name: '', title: '', path: '', component: '', parent_id: parentId,
      permission_code: '', icon: '', sort: 0, hidden: false, enabled: true
    })
    dialogVisible.value = true
  }

  const openEdit = (row: MenuItem) => {
    editingId.value = row.id
    Object.assign(form, {
      name: row.name, title: row.title, path: row.path, component: row.component,
      parent_id: row.parent_id ?? undefined, permission_code: row.permission_code || '',
      icon: row.icon || '', sort: row.sort, hidden: row.hidden, enabled: row.enabled
    })
    dialogVisible.value = true
  }

  const toggleEnabled = async (row: MenuItem, enabled: unknown) => {
    try {
      await updatePermissionApi(row.id, { enabled: Boolean(enabled) })
      await fetchList()
    } catch (error) {
      ElMessage.error(error instanceof Error ? error.message : '操作失败')
    }
  }

  const submit = async () => {
    if (!form.name.trim() || !form.title.trim() || !form.path.trim() || !form.component.trim()) {
      ElMessage.warning('请填写名称、标题、路径与组件')
      return
    }
    saving.value = true
    try {
      const base = {
        name: form.name.trim(), title: form.title.trim(), path: form.path.trim(),
        component: form.component.trim(), parent_id: form.parent_id ?? null,
        permission_code: form.permission_code || undefined, icon: form.icon || undefined,
        sort: form.sort, hidden: form.hidden, enabled: form.enabled
      }
      if (editingId.value) await updatePermissionApi(editingId.value, base as MenuUpdateIn)
      else await createPermissionApi(base as MenuCreateIn)
      dialogVisible.value = false
      ElMessage.success('已保存')
      await fetchList()
    } catch (error) {
      ElMessage.error(error instanceof Error ? error.message : '保存失败')
    } finally {
      saving.value = false
    }
  }

  const remove = async (row: MenuItem) => {
    try {
      await ElMessageBox.confirm(`确认删除菜单“${row.title}”及其子项？`, '提示', { type: 'warning' })
      await deletePermissionApi(row.id)
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
  <div class="permission-page">
    <ElCard shadow="never">
      <template #header>
        <div class="card-header">
          <div class="header-title">
            <div class="title-icon"><Icon icon="mdi:key-variant" :size="20" /></div>
            <div>
              <div class="title-text">权限管理</div>
              <div class="title-desc">维护系统菜单与操作权限，按父子层级组织</div>
            </div>
          </div>
          <ElButton v-if="can('permission:create')" type="primary" size="small" @click="openCreate()">
            <Icon icon="mdi:plus" :size="15" class="mr-1" />新增权限
          </ElButton>
        </div>
      </template>

      <div class="toolbar">
        <ElInput v-model="keyword" placeholder="搜索名称、标识或权限码" clearable class="search-input">
          <template #prefix><Icon icon="mdi:magnify" :size="15" /></template>
        </ElInput>
        <ElTag type="info" size="small" effect="plain">共 {{ list.length }} 项</ElTag>
      </div>

      <ElTable :key="keyword ? 'filtered' : 'all'" :data="filteredTreeData" v-loading="loading"
        border size="small" row-key="id" :tree-props="{ children: 'children' }"
        :default-expand-all="!!keyword" :row-class-name="rowClassName">
        <ElTableColumn label="名称 / 权限码" min-width="240">
          <template #default="{ row }">
            <span class="node-icon" :class="`node-icon--${typeOf(row as MenuItem)}`">
              <Icon :icon="(row as MenuItem).icon || typeMetaOf(row as MenuItem).icon" :size="15" />
            </span>
            <span class="node-title">{{ (row as MenuItem).title }}</span>
            <ElTag v-if="(row as MenuItem).permission_code" size="small" type="warning"
              effect="plain" class="code-tag">{{ (row as MenuItem).permission_code }}</ElTag>
          </template>
        </ElTableColumn>
        <ElTableColumn label="类型" width="92" align="center">
          <template #default="{ row }">
            <ElTag :type="typeMetaOf(row as MenuItem).tagType" size="small" effect="plain">
              {{ typeMetaOf(row as MenuItem).label }}
            </ElTag>
          </template>
        </ElTableColumn>
        <ElTableColumn prop="name" label="标识" width="150" show-overflow-tooltip />
        <ElTableColumn prop="path" label="路径" width="160" show-overflow-tooltip />
        <ElTableColumn prop="component" label="组件" min-width="180" show-overflow-tooltip />
        <ElTableColumn label="隐藏" width="70" align="center">
          <template #default="{ row }">
            <ElTag v-if="(row as MenuItem).hidden" type="info" size="small" effect="plain">是</ElTag>
            <span v-else class="muted">否</span>
          </template>
        </ElTableColumn>
        <ElTableColumn label="启用" width="80" align="center">
          <template #default="{ row }">
            <ElSwitch :model-value="(row as MenuItem).enabled" size="small"
              :disabled="!can('permission:update')"
              @update:model-value="toggleEnabled(row as MenuItem, $event)" />
          </template>
        </ElTableColumn>
        <ElTableColumn label="操作" width="230" fixed="right">
          <template #default="{ row }">
            <ElButton v-if="can('permission:create')" link size="small" @click="openCreate((row as MenuItem).id)">
              <Icon icon="mdi:plus" :size="14" class="mr-1" />新增子项
            </ElButton>
            <ElButton v-if="can('permission:update')" link type="primary" size="small" @click="openEdit(row as MenuItem)">
              <Icon icon="mdi:pencil" :size="14" class="mr-1" />编辑
            </ElButton>
            <ElButton v-if="can('permission:delete')" link type="danger" size="small" @click="remove(row as MenuItem)">
              <Icon icon="mdi:delete" :size="14" class="mr-1" />删除
            </ElButton>
          </template>
        </ElTableColumn>
      </ElTable>

      <ElDialog v-model="dialogVisible" :title="editingId ? '编辑权限' : '新增权限'" width="560px">
        <ElForm label-width="90px" size="small">
          <ElDivider content-position="left">基础信息</ElDivider>
          <ElFormItem label="标识" required>
            <ElInput v-model="form.name" :disabled="!!editingId" placeholder="如 DocumentList" />
          </ElFormItem>
          <ElFormItem label="标题" required><ElInput v-model="form.title" /></ElFormItem>
          <ElFormItem label="路径" required><ElInput v-model="form.path" /></ElFormItem>
          <ElFormItem label="组件" required>
            <ElInput v-model="form.component" placeholder="如 views/Audit/OperationLog 或 # / ##" />
          </ElFormItem>
          <ElFormItem label="上级菜单">
            <ElSelect v-model="form.parent_id" clearable style="width: 100%">
              <ElOption v-for="item in parentOptions" :key="item.id" :value="item.id" :label="item.title" />
            </ElSelect>
          </ElFormItem>
          <ElDivider content-position="left">权限与展示</ElDivider>
          <ElFormItem label="权限码">
            <ElInput v-model="form.permission_code" placeholder="如 system:write" />
          </ElFormItem>
          <ElFormItem label="图标"><IconPicker v-model="form.icon" /></ElFormItem>
          <ElFormItem label="排序"><ElInput v-model.number="form.sort" type="number" /></ElFormItem>
          <ElFormItem label="隐藏"><ElSwitch v-model="form.hidden" /></ElFormItem>
          <ElFormItem label="启用"><ElSwitch v-model="form.enabled" /></ElFormItem>
        </ElForm>
        <template #footer>
          <ElButton size="small" @click="dialogVisible = false">取消</ElButton>
          <ElButton type="primary" size="small" :loading="saving" @click="submit">保存</ElButton>
        </template>
      </ElDialog>
    </ElCard>
  </div>
</template>

<style scoped>
  .card-header { display: flex; align-items: center; justify-content: space-between; }
  .header-title { display: flex; align-items: center; gap: 12px; }
  .title-icon {
    width: 38px; height: 38px; border-radius: 10px; display: flex; align-items: center;
    justify-content: center; color: #fff;
    background: linear-gradient(135deg, var(--el-color-primary), var(--el-color-primary-light-3));
  }
  .title-text { font-size: var(--app-font-size-md); font-weight: 600; color: var(--el-text-color-primary); }
  .title-desc { font-size: var(--app-font-size-xs); color: var(--el-text-color-secondary); margin-top: 2px; }
  .toolbar { display: flex; align-items: center; gap: 12px; margin-bottom: 14px; }
  .search-input { width: 280px; }
  .node-icon {
    display: inline-flex; align-items: center; justify-content: center;
    width: 26px; height: 26px; border-radius: 6px; margin-right: 8px; vertical-align: middle;
    background: var(--el-fill-color-light); color: var(--el-color-primary);
  }
  .node-icon--directory { color: var(--el-color-primary); }
  .node-icon--page { color: var(--el-color-success); }
  .node-icon--action { color: var(--el-color-warning); }
  .node-title { font-weight: 500; }
  .code-tag { margin-left: 8px; font-size: var(--app-font-size-xs); }
  .muted { color: var(--el-text-color-placeholder); }
  :deep(.root-row) { font-weight: 600; }
  :deep(.action-row) { color: var(--el-text-color-regular); }
</style>
