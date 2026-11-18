<script setup lang="ts">
  import ConfigGlobal from '@/components/ConfigGlobal/index.vue'
  import Watermark from '@/components/Watermark/index.vue'
  import { useTheme } from '@/hooks/useTheme'
  import { useTitle } from '@/hooks/useTitle'

  useTheme()
  useTitle()
</script>

<template>
  <ConfigGlobal>
    <RouterView />
    <Watermark />
  </ConfigGlobal>
</template>

<style lang="less">
  .size {
    width: 100%;
    height: 100%;
  }

  html,
  body {
    padding: 0 !important;
    margin: 0;
    overflow: hidden;
    font-size: var(--app-font-size-base);
    .size;

    #app {
      .size;
    }
  }

  #nprogress .bar {
    background: var(--el-color-primary) !important;
  }
</style>
