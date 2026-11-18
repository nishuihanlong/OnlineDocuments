<script setup lang="ts">
  import { onMounted, ref } from 'vue'
  import {
    ElButton, ElCard, ElForm, ElFormItem, ElInput,
    ElPagination, ElTable, ElTableColumn, ElMessage
  } from 'element-plus'
  import { getLoginLogListApi } from '@/api/system'
  import type { LoginLogItem } from '@/api/system/types'

  const loading = ref(false)
  const list = ref<LoginLogItem[]>([])
  const total = ref(0)
  const page = ref(1)
  const pageSize = ref(10)
  const keyword = ref('')

  const fetchList = async () => {
    loading.value = true
    try {
      const res = await getLoginLogListApi({
        page: page.value, page_size: pageSize.value, keyword: keyword.value || undefined
      })
      list.value = res.data?.items ?? []
      total.value = res.data?.total ?? 0
    } catch (error) {
      ElMessage.error(error instanceof Error ? error.message : '日志加载失败')
    } finally {
      loading.value = false
    }
  }

  const handleSearch = () => {
    page.value = 1
    void fetchList()
  }

  onMounted(() => { void fetchList() })
</script>

<template>
  <ElCard shadow="never">
    <template #header>登录日志</template>
    <ElForm inline size="small" @submit.prevent="handleSearch">
      <ElFormItem label="关键词">
        <ElInput v-model="keyword" placeholder="用户名/IP" clearable style="width: 200px" @keyup.enter="handleSearch" />
      </ElFormItem>
      <ElFormItem>
        <ElButton type="primary" @click="handleSearch">查询</ElButton>
      </ElFormItem>
    </ElForm>
    <ElTable :data="list" v-loading="loading" border stripe size="small">
      <ElTableColumn prop="username" label="用户名" width="130" />
      <ElTableColumn prop="ip" label="IP" width="140" />
      <ElTableColumn label="结果" width="90">
        <template #default="{ row }">
          {{ (row as LoginLogItem).success ? '成功' : '失败' }}
        </template>
      </ElTableColumn>
      <ElTableColumn prop="message" label="说明" min-width="160" show-overflow-tooltip />
      <ElTableColumn prop="user_agent" label="客户端" min-width="200" show-overflow-tooltip />
      <ElTableColumn prop="created_at" label="时间" width="170" />
    </ElTable>
    <div class="pagination">
      <ElPagination v-model:current-page="page" v-model:page-size="pageSize" :total="total"
        :page-sizes="[10, 20, 50]" layout="total, sizes, prev, pager, next" background
        @current-change="fetchList()" @size-change="handleSearch" />
    </div>
  </ElCard>
</template>

<style scoped>
  .pagination { display: flex; justify-content: flex-end; margin-top: 12px; }
</style>
