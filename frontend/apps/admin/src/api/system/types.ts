export interface PageResult<T> {
  items: T[]
  total: number
  page: number
  page_size: number
}

export interface SystemQuery {
  keyword?: string
  username?: string
  user_id?: number
  page?: number
  page_size?: number
}

export interface PublicConfig {
  watermark_enabled: boolean
}

export interface ConfigItem {
  id: number
  key: string
  value?: string | null
  name: string
  remark?: string | null
  created_at: string
  updated_at: string
}

export interface NoticeItem {
  id: number
  title: string
  content?: string | null
  type: 'notice' | 'announcement'
  enabled: boolean
  created_at: string
  updated_at: string
}

export interface JobItem {
  id: number
  name: string
  code: string
  interval_seconds: number
  enabled: boolean
  last_run_at?: string | null
  created_at: string
}

export interface OperationLogItem {
  id: number
  user_id?: number | null
  username: string
  module: string
  action: string
  method: string
  path: string
  ip: string
  status_code: number
  detail?: string | null
  created_at: string
}

export interface LoginLogItem {
  id: number
  username: string
  ip: string
  user_agent: string
  success: boolean
  message: string
  created_at: string
}

export interface OnlineUserItem {
  id: number
  username: string
  real_name: string
  ip: string
  login_at?: string | null
}

export interface MonitorInfo {
  app_name: string
  env: string
  cpu_percent: number
  memory_percent: number
  memory_total_mb: number
  disk_percent: number
  python_version: string
  database: string
  storage: string
}

export interface RedisMonitorInfo {
  configured: boolean
  reachable: boolean
  version?: string | null
  uptime_seconds: number
  used_memory_mb: number
  connected_clients: number
  total_keys: number
  hit_rate: number
  error?: string | null
}

export interface RabbitMQQueueInfo {
  name: string
  vhost: string
  messages: number
  messages_ready: number
  messages_unacknowledged: number
  consumers: number
}

export interface RabbitMQMonitorInfo {
  configured: boolean
  reachable: boolean
  version?: string | null
  exchange_count: number
  queue_count: number
  total_messages: number
  queues: RabbitMQQueueInfo[]
  error?: string | null
}

export interface FileItem {
  name: string
  path: string
  size: number
  is_dir: boolean
  modified_at: string
}

export interface ApiRouteItem {
  path: string
  methods: string[]
  summary: string
  tags: string[]
}
