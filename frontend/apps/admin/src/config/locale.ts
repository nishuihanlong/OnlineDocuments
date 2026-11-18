import zhCNMessages from '@/locales/zh-CN'
import enMessages from '@/locales/en'
import zhCNElement from 'element-plus/es/locale/lang/zh-cn'
import enElement from 'element-plus/es/locale/lang/en'
import { toVueI18nSyntax, translationsEn } from 'pptx-vue-viewer/i18n'
import { translationsZhCN } from 'pptx-vue-viewer/i18n/zh-CN'

/**
 * pptx-vue-viewer 使用宿主的 vue-i18n 渲染界面文本，需把它的词条并入宿主消息表；
 * 共享词典用 `{{var}}` 占位，必须先经 toVueI18nSyntax 转成 vue-i18n 可编译的形式。
 */
const pptxMessages = {
  'zh-CN': toVueI18nSyntax(translationsZhCN),
  en: toVueI18nSyntax(translationsEn)
}

export const localeRegistry = {
  'zh-CN': {
    label: '简体中文',
    messages: { ...zhCNMessages, ...pptxMessages['zh-CN'] },
    elementLocale: zhCNElement
  },
  en: {
    label: 'English',
    messages: { ...enMessages, ...pptxMessages.en },
    elementLocale: enElement
  }
} as const

export type LocaleCode = keyof typeof localeRegistry

export const DEFAULT_LOCALE: LocaleCode = 'zh-CN'

export const isLocale = (value: unknown): value is LocaleCode =>
  typeof value === 'string' && value in localeRegistry

export const localeOptions = (Object.keys(localeRegistry) as LocaleCode[]).map((value) => ({
  value,
  label: localeRegistry[value].label
}))

export const localeMessages = Object.fromEntries(
  (Object.keys(localeRegistry) as LocaleCode[]).map((locale) => [
    locale,
    localeRegistry[locale].messages
  ])
)
