<script setup lang="ts">
  import { onMounted, reactive, ref } from 'vue'
  import {
    ElButton, ElCard, ElDialog, ElForm, ElFormItem, ElInput,
    ElMessage, ElMessageBox, ElOption, ElPagination, ElSelect, ElTag,
    ElTable, ElTableColumn
  } from 'element-plus'
  import { activateUserApi, createUserApi, disableUserApi, getUserListApi, updateUserApi } from '@/api/user'
  import type { UserCreateIn, UserItem, UserUpdateIn } from '@/api/user/types'
  import { getRoleListApi } from '@/api/access'
  import type { RoleItem } from '@/api/access/types'
  import { usePermission } from '@/hooks/usePermission'

  const { can } = usePermission()

  const loading = ref(false)
  const list = ref<UserItem[]>([])
  const roleOptions = ref<RoleItem[]>([])
  const total = ref(0)
  const page = ref(1)
  const pageSize = ref(10)
  const keyword = ref('')
  const dialogVisible = ref(false)
  const editingId = ref<number | null>(null)
  const saving = ref(false)
  const form = reactive({
    username: '', password: '', real_name: '', email: '',
    dept_id: undefined as number | undefined,
    data_scope: 'self' as 'all' | 'self' | 'dept',
    status: 1,
    role_ids: [] as number[]
  })

  const scopeOptions = [
    { value: 'self', label: '仅本人数据' },
    { value: 'dept', label: '本部门数据' },
    { value: 'all', label: '全部数据' }
  ]

  const fetchList = async () => {
    loading.value = true
    try {
      const res = await getUserListApi({
        keyword: keyword.value || undefined, page: page.value, page_size: pageSize.value
      })
      list.value = res.data?.items ?? []
      total.value = res.data?.total ?? 0
    } catch (error) {
      ElMessage.error(error instanceof Error ? error.message : '用户列表加载失败')
    } finally {
      loading.value = false
    }
  }

  /** 加载全部角色，供用户表单多选。 */
  const fetchRoles = async () => {
    try {
      const res = await getRoleListApi()
      roleOptions.value = res.data ?? []
    } catch (error) {
      ElMessage.error(error instanceof Error ? error.message : '角色列表加载失败')
    }
  }

  const openCreate = () => {
    editingId.value = null
    Object.assign(form, {
      username: '', password: '', real_name: '', email: '',
      dept_id: undefined, data_scope: 'self', status: 1,
      role_ids: []
    })
    dialogVisible.value = true
  }

  const openEdit = (row: UserItem) => {
    editingId.value = row.id
    Object.assign(form, {
      username: row.username, password: '', real_name: row.real_name || '',
      email: row.email || '', dept_id: row.dept_id ?? undefined,
      data_scope: row.data_scope, status: row.status,
      role_ids: (row.roles ?? []).map((role) => role.id)
    })
    dialogVisible.value = true
  }

  const submit = async () => {
    if (!form.username.trim() || (!editingId.value && !form.password)) {
      ElMessage.warning('请输入用户名与密码')
      return
    }
    saving.value = true
    try {
      if (editingId.value) {
        const payload: UserUpdateIn = {
          real_name: form.real_name || undefined,
          email: form.email || undefined,
          dept_id: form.dept_id ?? null,
          data_scope: form.data_scope,
          status: form.status,
          role_ids: form.role_ids
        }
        await updateUserApi(editingId.value, payload)
      } else {
        const payload: UserCreateIn = {
          username: form.username.trim(),
          password: form.password,
          real_name: form.real_name || undefined,
          email: form.email || undefined,
          dept_id: form.dept_id,
          data_scope: form.data_scope,
          role_ids: form.role_ids
        }
        await createUserApi(payload)
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

  const disable = async (row: UserItem) => {
    try {
      await ElMessageBox.confirm(`确认停用用户“${row.username}”？`, '提示', { type: 'warning' })
      await disableUserApi(row.id)
      ElMessage.success('已停用')
      await fetchList()
    } catch (error) {
      if (error !== 'cancel' && error !== 'close') {
        ElMessage.error(error instanceof Error ? error.message : '操作失败')
      }
    }
  }

  /** 激活待激活或已停用的用户。 */
  const activate = async (row: UserItem) => {
    try {
      await activateUserApi(row.id)
      ElMessage.success(`已激活用户“${row.username}”`)
      await fetchList()
    } catch (error) {
      ElMessage.error(error instanceof Error ? error.message : '激活失败')
    }
  }

  /** 用户状态展示：0 停用 / 1 正常 / 2 待激活。 */
  const statusMeta = (status: number): { label: string; type: 'success' | 'info' | 'warning' } => {
    if (status === 1) return { label: '正常', type: 'success' }
    if (status === 2) return { label: '待激活', type: 'warning' }
    return { label: '停用', type: 'info' }
  }

  onMounted(() => {
    void fetchList()
    void fetchRoles()
  })
</script>

<template>
  <ElCard shadow="never">
    <template #header>
      <div class="header">
        <span>用户管理</span>
        <div>
          <ElInput v-model="keyword" placeholder="用户名/姓名" clearable style="width: 180px" @keyup.enter="fetchList()" />
          <ElButton size="small" @click="fetchList()">查询</ElButton>
          <ElButton v-if="can('user:create')" type="primary" size="small" @click="openCreate">新增用户</ElButton>
        </div>
      </div>
    </template>
    <ElTable :data="list" v-loading="loading" border stripe size="small">
      <ElTableColumn prop="username" label="用户名" width="130" />
      <ElTableColumn prop="real_name" label="姓名" width="120" />
      <ElTableColumn prop="email" label="邮箱" min-width="170" show-overflow-tooltip />
      <ElTableColumn label="角色" min-width="160">
        <template #default="{ row }">
          <template v-if="(row as UserItem).roles?.length">
            <ElTag v-for="role in (row as UserItem).roles" :key="role.id" size="small" type="info" effect="plain" class="role-tag">
              {{ role.name }}
            </ElTag>
          </template>
          <span v-else class="text-muted">未分配</span>
        </template>
      </ElTableColumn>
      <ElTableColumn label="数据范围" width="130">
        <template #default="{ row }">
          {{ scopeOptions.find((item) => item.value === (row as UserItem).data_scope)?.label || '仅本人数据' }}
        </template>
      </ElTableColumn>
      <ElTableColumn label="状态" width="90">
        <template #default="{ row }">
          <ElTag :type="statusMeta((row as UserItem).status).type" size="small" effect="plain">
            {{ statusMeta((row as UserItem).status).label }}
          </ElTag>
        </template>
      </ElTableColumn>
      <ElTableColumn prop="created_at" label="创建时间" width="170" />
      <ElTableColumn label="操作" width="180" fixed="right">
        <template #default="{ row }">
          <ElButton v-if="can('user:update')" link type="primary" size="small" @click="openEdit(row as UserItem)">设置</ElButton>
          <ElButton v-if="can('user:activate') && (row as UserItem).status !== 1" link type="success" size="small" @click="activate(row as UserItem)">激活</ElButton>
          <ElButton v-if="can('user:activate') && (row as UserItem).status !== 0" link type="danger" size="small" @click="disable(row as UserItem)">停用</ElButton>
        </template>
      </ElTableColumn>
    </ElTable>
    <div class="pagination">
      <ElPagination v-model:current-page="page" v-model:page-size="pageSize" :total="total"
        :page-sizes="[10, 20, 50]" layout="total, sizes, prev, pager, next" background
        @current-change="fetchList()" @size-change="fetchList()" />
    </div>
    <ElDialog v-model="dialogVisible" :title="editingId ? '设置用户' : '新增用户'" width="480px">
      <ElForm label-width="90px" size="small">
        <ElFormItem label="用户名" required><ElInput v-model="form.username" :disabled="!!editingId" /></ElFormItem>
        <ElFormItem v-if="!editingId" label="密码" required><ElInput v-model="form.password" type="password" show-password /></ElFormItem>
        <ElFormItem label="姓名"><ElInput v-model="form.real_name" /></ElFormItem>
        <ElFormItem label="邮箱"><ElInput v-model="form.email" /></ElFormItem>
        <ElFormItem label="部门ID"><ElInput v-model.number="form.dept_id" type="number" placeholder="用于本部门数据范围" /></ElFormItem>
        <ElFormItem label="数据范围">
          <ElSelect v-model="form.data_scope" style="width: 160px">
            <ElOption v-for="option in scopeOptions" :key="option.value" :value="option.value" :label="option.label" />
          </ElSelect>
        </ElFormItem>
        <ElFormItem label="角色">
          <ElSelect v-model="form.role_ids" multiple clearable collapse-tags collapse-tags-tooltip placeholder="选择角色" style="width: 100%">
            <ElOption v-for="role in roleOptions" :key="role.id" :value="role.id" :label="role.name" />
          </ElSelect>
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
  .header { display: flex; align-items: center; justify-content: space-between; gap: 8px; }
  .pagination { display: flex; justify-content: flex-end; margin-top: 12px; }
  .role-tag { margin-right: 4px; }
  .text-muted { color: var(--el-text-color-secondary); }
</style>
