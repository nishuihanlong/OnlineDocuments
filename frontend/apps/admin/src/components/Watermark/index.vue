<script setup lang="ts">
  import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
  import { getPublicConfigApi } from '@/api/system'
  import { useAppStoreWithOut } from '@/store/modules/app'
  import { useUserStoreWithOut } from '@/store/modules/user'

  const props = defineProps<{
    /** 水印单元基准间距（同时决定单元高度） */
    gap?: number
    /** 水印字号 */
    fontSize?: number
    /** 水印单元宽度，越大每个水印横向跨度越宽 */
    width?: number
    /** 水印密度：单元内纵向行数，越大越密（横向固定 2 列） */
    density?: number
  }>()
  const appStore = useAppStoreWithOut()
  const userStore = useUserStoreWithOut()

  const backgroundImage = ref('')
  const enabled = ref(true)
  const now = ref(new Date())

  const username = computed(
    () => userStore.userInfo?.real_name || userStore.userInfo?.username || '未登录'
  )

  const watermarkText = computed(() => {
    const time = now.value.toLocaleString('zh-CN', { hour12: false })
    return `${username.value}  ${time}`
  })

  /** 用 Canvas 绘制平铺水印，颜色随明暗主题切换。 */
  const draw = () => {
    if (!enabled.value) {
      backgroundImage.value = ''
      return
    }
    const canvas = document.createElement('canvas')
    const context = canvas.getContext('2d')
    if (!context) return

    const gap = props.gap ?? 200
    const fontSize = props.fontSize ?? 13
    // 单元更宽；高度保持 gap，避免文字被拉伸变形。
    const width = props.width ?? Math.max(480, Math.round(gap * 2.4))
    const density = Math.max(1, props.density ?? 2)
    canvas.width = width
    canvas.height = gap

    context.font = `${fontSize}px "Helvetica Neue", Helvetica, Arial, sans-serif`
    context.fillStyle = appStore.isDark ? 'rgba(255,255,255,0.14)' : 'rgba(0,0,0,0.10)'
    context.textAlign = 'center'
    context.textBaseline = 'middle'

    const text = watermarkText.value
    // 网格平铺：横向固定 2 列（避免长文本重叠），纵向行数由密度决定。
    // 连边界行/列一起绘制，旋转裁切后相邻单元可无缝拼接，不会出现半截水印。
    const columns = 2
    const rows = density
    for (let row = 0; row <= rows; row += 1) {
      for (let column = 0; column <= columns; column += 1) {
        context.save()
        context.translate((column / columns) * width, (row / rows) * gap)
        context.rotate((-22 * Math.PI) / 180)
        context.fillText(text, 0, 0)
        context.restore()
      }
    }
    backgroundImage.value = `url(${canvas.toDataURL('image/png')})`
  }

  let timer: number | undefined

  onMounted(async () => {
    try {
      const res = await getPublicConfigApi()
      enabled.value = res.data?.watermark_enabled ?? true
    } catch {
      // 后端未升级或网络异常时保持水印开启，避免绕过审计。
      enabled.value = true
    }
    draw()
    timer = window.setInterval(() => {
      now.value = new Date()
      draw()
    }, 60_000)
  })

  onBeforeUnmount(() => {
    if (timer !== undefined) window.clearInterval(timer)
  })

  watch(() => appStore.isDark, draw)
  watch(() => userStore.userInfo, draw, { deep: true })
</script>

<template>
  <div
    v-if="enabled"
    class="global-watermark"
    :style="{ backgroundImage }"
    aria-hidden="true"
  />
</template>

<style scoped>
  .global-watermark {
    position: fixed;
    inset: 0;
    z-index: 1000;
    pointer-events: none;
    background-repeat: repeat;
    user-select: none;
  }
</style>
