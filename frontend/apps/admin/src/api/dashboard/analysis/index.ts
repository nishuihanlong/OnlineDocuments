import request from '@/request'
import type { AnalysisTotal, WeeklyUserActivity, MonthlySales } from './types'

/** 概览四项指标：GET /v1/system/dashboard/total。 */
export const getAnalysisTotalApi = () => {
  return request.get<AnalysisTotal>({ url: '/v1/system/dashboard/total' })
}

/** 近 7 天操作活跃度（柱图）：GET /v1/system/dashboard/activity。 */
export const getWeeklyUserActivityApi = () => {
  return request.get<WeeklyUserActivity[]>({ url: '/v1/system/dashboard/activity' })
}

/** 近 12 月文档趋势（折线）：GET /v1/system/dashboard/trend。 */
export const getMonthlySalesApi = () => {
  return request.get<MonthlySales[]>({ url: '/v1/system/dashboard/trend' })
}
