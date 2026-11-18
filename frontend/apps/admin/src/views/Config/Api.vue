<script setup lang="ts">
  import { onMounted, ref } from 'vue'
  import { ElButton, ElCard, ElInput, ElTable, ElTableColumn, ElTag, ElMessage } from 'element-plus'
  import { getApiRouteListApi } from '@/api/system'
  import type { ApiRouteItem } from '@/api/system/types'
  import { computed } from 'vue'

  const loading = ref(false)
  const list = ref<ApiRouteItem[]>([])
  const keyword = ref('')

  const filtered = computed(() => {
    const key = keyword.value.trim().toLowerCase()
    if (!key) return list.value
    return list.value.filter((item) => item.path.toLowerCase().includes(key) || item.summary.includes(key))
  })

  const fetchList = async () => {
    loading.value = true
    try {
      list.value = (await getApiRouteListApi()).data ?? []
    } catch (error) {
      ElMessage.error(error instanceof Error ? error.message : '接口清单加载失败')
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
        <span>系统接口清单</span>
        <ElInput v-model="keyword" placeholder="搜索路径或说明" clearable style="width: 220px" />
        <ElButton size="small" :loading="loading" @click="fetchList()">刷新</ElButton>
      </div>
    </template>
    <ElTable :data="filtered" v-loading="loading" border stripe size="small">
      <ElTableColumn prop="path" label="接口路径" min-width="260" show-overflow-tooltip />
      <ElTableColumn label="方法" width="180">
        <template #default="{ row }">
          <ElTag v-for="method in (row as ApiRouteItem).methods" :key="method" size="small" effect="plain" class="method-tag">
            {{ method }}
          </ElTag>
        </template>
      </ElTableColumn>
      <ElTableColumn prop="summary" label="说明" min-width="180" show-overflow-tooltip />
      <ElTableColumn label="标签" min-width="140" show-overflow-tooltip>
        <template #default="{ row }">{{ (row as ApiRouteItem).tags.join(', ') }}</template>
      </ElTableColumn>
    </ElTable>
  </ElCard>
</template>

<style scoped>
  .header { display: flex; align-items: center; gap: 12px; }
  .method-tag { margin-right: 4px; }
</style>
