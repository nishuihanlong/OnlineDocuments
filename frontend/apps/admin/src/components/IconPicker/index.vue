<script setup lang="ts">
  import { computed, ref } from 'vue'
  import { ElButton, ElDialog, ElInput } from 'element-plus'
  import { iconCatalog } from '@/icons'

  const props = defineProps<{
    modelValue: string
    placeholder?: string
  }>()

  const emit = defineEmits<{
    'update:modelValue': [value: string]
  }>()

  const visible = ref(false)
  const keyword = ref('')

  const filtered = computed(() => {
    const key = keyword.value.trim().toLowerCase()
    if (!key) return Object.values(iconCatalog)
    return Object.values(iconCatalog).filter(
      (item) =>
        item.name.toLowerCase().includes(key) ||
        item.label.toLowerCase().includes(key) ||
        item.keywords.toLowerCase().includes(key)
    )
  })

  const openPicker = () => {
    keyword.value = ''
    visible.value = true
  }

  const selectIcon = (name: string) => {
    emit('update:modelValue', name)
    visible.value = false
  }
</script>

<template>
  <div class="icon-picker">
    <ElInput
      :model-value="props.modelValue"
      readonly
      :placeholder="props.placeholder || '点击选择图标'"
      class="picker-input"
      @click="openPicker"
    >
      <template v-if="props.modelValue" #prefix>
        <Icon :icon="props.modelValue" :size="16" />
      </template>
      <template #suffix>
        <ElButton link size="small" @click.stop="openPicker">选择</ElButton>
      </template>
    </ElInput>

    <ElDialog v-model="visible" title="选择图标" width="680px">
      <ElInput v-model="keyword" placeholder="搜索图标名称、中文名或关键词" clearable class="search-input" />
      <div class="icon-grid">
        <button
          v-for="item in filtered"
          :key="item.name"
          type="button"
          class="icon-item"
          :class="{ active: props.modelValue === item.name }"
          :title="item.name"
          @click="selectIcon(item.name)"
        >
          <Icon :icon="item.name" :size="22" />
          <span class="icon-label">{{ item.label }}</span>
        </button>
        <div v-if="!filtered.length" class="empty">未找到匹配图标</div>
      </div>
      <template #footer>
        <ElButton size="small" @click="visible = false">关闭</ElButton>
      </template>
    </ElDialog>
  </div>
</template>

<style scoped>
  .picker-input {
    cursor: pointer;
  }

  .search-input {
    margin-bottom: 12px;
  }

  .icon-grid {
    display: grid;
    grid-template-columns: repeat(6, minmax(0, 1fr));
    gap: 8px;
    max-height: 380px;
    overflow-y: auto;
  }

  .icon-item {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 6px;
    padding: 10px 4px;
    border: 1px solid var(--el-border-color-lighter);
    border-radius: 6px;
    background: var(--el-bg-color);
    color: var(--el-text-color-regular);
    cursor: pointer;
    transition: all 0.15s ease;
  }

  .icon-item:hover {
    border-color: var(--el-color-primary);
    color: var(--el-color-primary);
  }

  .icon-item.active {
    border-color: var(--el-color-primary);
    background: var(--el-color-primary-light-9);
    color: var(--el-color-primary);
  }

  .icon-label {
    font-size: var(--app-font-size-xs);
    line-height: 14px;
    max-width: 100%;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .empty {
    grid-column: 1 / -1;
    text-align: center;
    color: var(--el-text-color-secondary);
    padding: 24px 0;
  }
</style>
