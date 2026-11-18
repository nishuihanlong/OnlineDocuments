<script setup lang="ts">
  import { onMounted, ref } from 'vue'
  import { ElButton, ElCard, ElDescriptions, ElDescriptionsItem, ElProgress, ElMessage } from 'element-plus'
  import { getMonitorApi } from '@/api/system'
  import type { MonitorInfo } from '@/api/system/types'

  const loading = ref(false)
  const info = ref<MonitorInfo | null>(null)

  const fetchInfo = async () => {
    loading.value = true
    try {
      info.value = (await getMonitorApi()).data
    } catch (error) {
      ElMessage.error(error instanceof Error ? error.message : '监控信息加载失败')
    } finally {
      loading.value = false
    }
  }

  onMounted(() => { void fetchInfo() })
</script>

<template>
  <ElCard shadow="never" v-loading="loading">
    <template #header>
      <div class="header">
        <span>服务与服务器监控</span>
        <ElButton size="small" @click="fetchInfo()">刷新</ElButton>
      </div>
    </template>
    <template v-if="info">
      <ElDescriptions :column="2" border>
        <ElDescriptionsItem label="应用名称">{{ info.app_name }}</ElDescriptionsItem>
        <ElDescriptionsItem label="运行环境">{{ info.env }}</ElDescriptionsItem>
        <ElDescriptionsItem label="数据库">{{ info.database }}</ElDescriptionsItem>
        <ElDescriptionsItem label="存储后端">{{ info.storage }}</ElDescriptionsItem>
        <ElDescriptionsItem label="Python 版本">{{ info.python_version }}</ElDescriptionsItem>
        <ElDescriptionsItem label="内存总量">{{ info.memory_total_mb }} MB</ElDescriptionsItem>
        <ElDescriptionsItem label="CPU 使用率">
          <ElProgress :percentage="info.cpu_percent" />
        </ElDescriptionsItem>
        <ElDescriptionsItem label="内存使用率">
          <ElProgress :percentage="info.memory_percent" />
        </ElDescriptionsItem>
        <ElDescriptionsItem label="磁盘使用率">
          <ElProgress :percentage="info.disk_percent" />
        </ElDescriptionsItem>
      </ElDescriptions>
    </template>
  </ElCard>
</template>

<style scoped>
  .header { display: flex; align-items: center; justify-content: space-between; }
</style>
