<script setup lang="ts">
  import { computed, onMounted, ref } from 'vue'
  import {
    ElAlert, ElButton, ElCard, ElDescriptions, ElDescriptionsItem, ElProgress, ElTag, ElMessage
  } from 'element-plus'
  import { getRedisMonitorApi } from '@/api/system'
  import type { RedisMonitorInfo } from '@/api/system/types'

  const loading = ref(false)
  const info = ref<RedisMonitorInfo | null>(null)

  const uptimeText = computed(() => {
    const seconds = info.value?.uptime_seconds ?? 0
    const days = Math.floor(seconds / 86400)
    const hours = Math.floor((seconds % 86400) / 3600)
    const minutes = Math.floor((seconds % 3600) / 60)
    return `${days} 天 ${hours} 小时 ${minutes} 分`
  })

  const fetchInfo = async () => {
    loading.value = true
    try {
      info.value = (await getRedisMonitorApi()).data
    } catch (error) {
      ElMessage.error(error instanceof Error ? error.message : 'Redis 监控加载失败')
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
        <span>
          Redis 监控
          <ElTag v-if="info" :type="info.reachable ? 'success' : 'danger'" size="small" effect="plain">
            {{ info.configured ? (info.reachable ? '已连接' : '连接失败') : '未配置' }}
          </ElTag>
        </span>
        <ElButton size="small" @click="fetchInfo()">刷新</ElButton>
      </div>
    </template>
    <template v-if="info">
      <ElAlert v-if="info.error" type="error" :title="info.error" show-icon class="alert" />
      <ElDescriptions :column="2" border>
        <ElDescriptionsItem label="Redis 版本">{{ info.version || '-' }}</ElDescriptionsItem>
        <ElDescriptionsItem label="运行时间">{{ uptimeText }}</ElDescriptionsItem>
        <ElDescriptionsItem label="已用内存">{{ info.used_memory_mb }} MB</ElDescriptionsItem>
        <ElDescriptionsItem label="客户端连接数">{{ info.connected_clients }}</ElDescriptionsItem>
        <ElDescriptionsItem label="当前库 Key 数">{{ info.total_keys }}</ElDescriptionsItem>
        <ElDescriptionsItem label="命中率">
          <ElProgress :percentage="info.hit_rate" />
        </ElDescriptionsItem>
      </ElDescriptions>
    </template>
  </ElCard>
</template>

<style scoped>
  .header { display: flex; align-items: center; justify-content: space-between; }
  .header .el-tag { margin-left: 8px; }
  .alert { margin-bottom: 16px; }
</style>
