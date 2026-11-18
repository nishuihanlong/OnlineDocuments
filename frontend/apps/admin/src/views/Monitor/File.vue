<script setup lang="ts">
  import { onMounted, ref } from 'vue'
  import { ElButton, ElCard, ElTable, ElTableColumn, ElMessage } from 'element-plus'
  import { getFileListApi } from '@/api/system'
  import type { FileItem } from '@/api/system/types'

  const loading = ref(false)
  const list = ref<FileItem[]>([])

  const fetchList = async () => {
    loading.value = true
    try {
      list.value = (await getFileListApi()).data ?? []
    } catch (error) {
      ElMessage.error(error instanceof Error ? error.message : '文件列表加载失败')
    } finally {
      loading.value = false
    }
  }

  const formatSize = (size: number) => `${(size / 1024).toFixed(1)} KB`

  onMounted(() => { void fetchList() })
</script>

<template>
  <ElCard shadow="never">
    <template #header>
      <div class="header">
        <span>文件管理</span>
        <ElButton size="small" :loading="loading" @click="fetchList()">刷新</ElButton>
      </div>
    </template>
    <ElTable :data="list" v-loading="loading" border stripe size="small">
      <ElTableColumn prop="name" label="文件名" min-width="200" show-overflow-tooltip />
      <ElTableColumn label="类型" width="90">
        <template #default="{ row }">{{ (row as FileItem).is_dir ? '目录' : '文件' }}</template>
      </ElTableColumn>
      <ElTableColumn label="大小" width="110">
        <template #default="{ row }">{{ formatSize((row as FileItem).size) }}</template>
      </ElTableColumn>
      <ElTableColumn prop="path" label="相对路径" min-width="220" show-overflow-tooltip />
      <ElTableColumn prop="modified_at" label="修改时间" width="170" />
    </ElTable>
  </ElCard>
</template>

<style scoped>
  .header { display: flex; align-items: center; justify-content: space-between; }
</style>
