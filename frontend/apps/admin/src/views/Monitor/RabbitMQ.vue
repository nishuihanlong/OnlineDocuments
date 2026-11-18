<script setup lang="ts">
  import { onMounted, ref } from 'vue'
  import {
    ElAlert, ElButton, ElCard, ElDescriptions, ElDescriptionsItem,
    ElTable, ElTableColumn, ElTag, ElMessage
  } from 'element-plus'
  import { getRabbitMQMonitorApi } from '@/api/system'
  import type { RabbitMQMonitorInfo } from '@/api/system/types'

  const loading = ref(false)
  const info = ref<RabbitMQMonitorInfo | null>(null)

  const fetchInfo = async () => {
    loading.value = true
    try {
      info.value = (await getRabbitMQMonitorApi()).data
    } catch (error) {
      ElMessage.error(error instanceof Error ? error.message : 'RabbitMQ 监控加载失败')
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
          RabbitMQ 监控
          <ElTag v-if="info" :type="info.reachable ? 'success' : 'danger'" size="small" effect="plain">
            {{ info.configured ? (info.reachable ? '已连接' : '连接失败') : '未配置' }}
          </ElTag>
        </span>
        <ElButton size="small" @click="fetchInfo()">刷新</ElButton>
      </div>
    </template>
    <template v-if="info">
      <ElAlert v-if="info.error" type="error" :title="info.error" show-icon class="alert" />
      <ElDescriptions :column="3" border class="overview">
        <ElDescriptionsItem label="RabbitMQ 版本">{{ info.version || '-' }}</ElDescriptionsItem>
        <ElDescriptionsItem label="交换机数">{{ info.exchange_count }}</ElDescriptionsItem>
        <ElDescriptionsItem label="队列数">{{ info.queue_count }}</ElDescriptionsItem>
        <ElDescriptionsItem label="消息总数">{{ info.total_messages }}</ElDescriptionsItem>
      </ElDescriptions>
      <div class="section-title">队列明细</div>
      <ElTable :data="info.queues" border stripe size="small" v-loading="loading">
        <ElTableColumn prop="name" label="队列名" min-width="180" show-overflow-tooltip />
        <ElTableColumn prop="vhost" label="VHost" width="120" show-overflow-tooltip />
        <ElTableColumn prop="messages" label="消息数" width="100" align="center" />
        <ElTableColumn prop="messages_ready" label="就绪" width="100" align="center" />
        <ElTableColumn prop="messages_unacknowledged" label="未确认" width="100" align="center" />
        <ElTableColumn prop="consumers" label="消费者" width="100" align="center" />
      </ElTable>
    </template>
  </ElCard>
</template>

<style scoped>
  .header { display: flex; align-items: center; justify-content: space-between; }
  .header .el-tag { margin-left: 8px; }
  .alert { margin-bottom: 16px; }
  .overview { margin-bottom: 18px; }
  .section-title { font-weight: 600; margin-bottom: 10px; }
</style>
