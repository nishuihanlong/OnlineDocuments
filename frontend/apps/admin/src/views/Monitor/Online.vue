<script setup lang="ts">
  import { onMounted, ref } from 'vue'
  import { ElButton, ElCard, ElTable, ElTableColumn, ElMessage } from 'element-plus'
  import { getOnlineUserListApi } from '@/api/system'
  import type { OnlineUserItem } from '@/api/system/types'

  const loading = ref(false)
  const list = ref<OnlineUserItem[]>([])

  const fetchList = async () => {
    loading.value = true
    try {
      list.value = (await getOnlineUserListApi()).data ?? []
    } catch (error) {
      ElMessage.error(error instanceof Error ? error.message : '在线用户加载失败')
    } finally {
      loading.value = false
    }
  }

  onMounted(() => { void fetchList() })
</script>

<template>
  <ElCard shadow="never">
    <template #header>
      <div class="header">
        <span>在线用户</span>
        <ElButton size="small" :loading="loading" @click="fetchList()">刷新</ElButton>
      </div>
    </template>
    <ElTable :data="list" v-loading="loading" border stripe size="small">
      <ElTableColumn prop="username" label="用户名" width="150" />
      <ElTableColumn prop="real_name" label="姓名" width="150" />
      <ElTableColumn prop="ip" label="登录 IP" width="150" />
      <ElTableColumn prop="login_at" label="登录时间" min-width="180" />
    </ElTable>
  </ElCard>
</template>

<style scoped>
  .header { display: flex; align-items: center; justify-content: space-between; }
</style>
