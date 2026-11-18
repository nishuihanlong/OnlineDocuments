import request from '@/request'
import type {
  ApiRouteItem,
  ConfigItem,
  FileItem,
  JobItem,
  LoginLogItem,
  MonitorInfo,
  NoticeItem,
  OnlineUserItem,
  OperationLogItem,
  PageResult,
  PublicConfig,
  RabbitMQMonitorInfo,
  RedisMonitorInfo,
  SystemQuery
} from './types'

export const getPublicConfigApi = () =>
  request.get<PublicConfig>({ url: '/v1/system/public-configs' })

export const getConfigListApi = (params: SystemQuery) =>
  request.get<PageResult<ConfigItem>>({ url: '/v1/system/configs', params })

export const createConfigApi = (data: { key: string; value?: string; name?: string; remark?: string }) =>
  request.post<ConfigItem>({ url: '/v1/system/configs', data })

export const updateConfigApi = (id: number, data: { value?: string; name?: string; remark?: string }) =>
  request.put<ConfigItem>({ url: `/v1/system/configs/${id}`, data })

export const deleteConfigApi = (id: number) =>
  request.delete<null>({ url: `/v1/system/configs/${id}` })

export const getNoticeListApi = (params: SystemQuery) =>
  request.get<PageResult<NoticeItem>>({ url: '/v1/system/notices', params })

export const createNoticeApi = (data: { title: string; content?: string; type?: string; enabled?: boolean }) =>
  request.post<NoticeItem>({ url: '/v1/system/notices', data })

export const updateNoticeApi = (id: number, data: { title?: string; content?: string; type?: string; enabled?: boolean }) =>
  request.put<NoticeItem>({ url: `/v1/system/notices/${id}`, data })

export const deleteNoticeApi = (id: number) =>
  request.delete<null>({ url: `/v1/system/notices/${id}` })

export const getJobListApi = () => request.get<JobItem[]>({ url: '/v1/system/jobs' })

export const createJobApi = (data: { name: string; code: string; interval_seconds?: number; enabled?: boolean }) =>
  request.post<JobItem>({ url: '/v1/system/jobs', data })

export const updateJobApi = (id: number, data: { name?: string; interval_seconds?: number; enabled?: boolean }) =>
  request.put<JobItem>({ url: `/v1/system/jobs/${id}`, data })

export const runJobApi = (id: number) => request.post<JobItem>({ url: `/v1/system/jobs/${id}/run` })

export const deleteJobApi = (id: number) => request.delete<null>({ url: `/v1/system/jobs/${id}` })

export const getOperationLogListApi = (params: SystemQuery) =>
  request.get<PageResult<OperationLogItem>>({ url: '/v1/system/logs/operation', params })

export const getLoginLogListApi = (params: SystemQuery) =>
  request.get<PageResult<LoginLogItem>>({ url: '/v1/system/logs/login', params })

export const getOnlineUserListApi = () =>
  request.get<OnlineUserItem[]>({ url: '/v1/system/online-users' })

export const getMonitorApi = () => request.get<MonitorInfo>({ url: '/v1/system/monitor' })

export const getFileListApi = () => request.get<FileItem[]>({ url: '/v1/system/files' })

export const getRedisMonitorApi = () =>
  request.get<RedisMonitorInfo>({ url: '/v1/system/monitor/redis' })

export const getRabbitMQMonitorApi = () =>
  request.get<RabbitMQMonitorInfo>({ url: '/v1/system/monitor/rabbitmq' })

export const getApiRouteListApi = () => request.get<ApiRouteItem[]>({ url: '/v1/system/api-routes' })
