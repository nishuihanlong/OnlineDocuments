import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { vermilionDarkTheme, vermilionLightTheme } from 'pptx-vue-viewer'
import { useAppStoreWithOut } from '@/store/modules/app'

/** 编辑器界面支持的语言，与框架 locale 对齐。 */
export type EditorLocale = 'zh-CN' | 'en'

/**
 * 统一编辑器偏好：界面语言跟随 ElementAdmin 的 vue-i18n，明暗主题跟随
 * ElementAdmin 的 isDark。供 Word/Excel/PPT/Visio 四个面板共用，保证
 * 切换框架语言或明暗模式时，四个编辑器表现一致。
 */
export const useEditorPreferences = () => {
  const { locale } = useI18n()
  const appStore = useAppStoreWithOut()

  /** 编辑器界面语言，只保留各 viewer 支持的取值。 */
  const editorLocale = computed<EditorLocale>(() =>
    locale.value === 'en' ? 'en' : 'zh-CN'
  )

  /** ElementAdmin 当前是否为暗色模式。 */
  const isDark = computed(() => appStore.isDark)

  /** Word/Excel 接受的 'light' | 'dark' 主题模式。 */
  const editorThemeMode = computed<'light' | 'dark'>(() =>
    isDark.value ? 'dark' : 'light'
  )

  /** PPTX 接受的完整主题对象，随明暗模式切换。 */
  const pptxTheme = computed(() =>
    isDark.value ? vermilionDarkTheme : vermilionLightTheme
  )

  return { editorLocale, isDark, editorThemeMode, pptxTheme }
}
