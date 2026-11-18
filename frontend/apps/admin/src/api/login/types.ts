export interface LoginParams {
  username: string
  password: string
}

export interface UserInfo {
  id: number
  username: string
  real_name?: string
  is_superuser?: boolean
  dept_id?: number | null
  data_scope?: 'all' | 'self' | 'dept'
  roles?: string[]
  /** 用户拥有的权限码；超管为 ['*']，用于前端按钮级权限控制。 */
  permissions?: string[]
}

export interface LoginResult {
  accessToken: string
  user: UserInfo
}

export interface RegisterParams {
  username: string
  password: string
  real_name?: string
  email?: string
}

export interface RegisterResult {
  username: string
  message: string
}
