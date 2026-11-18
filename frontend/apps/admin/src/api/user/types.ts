/** 用户所属角色的简要信息，对应后端 RoleOut。 */
export interface UserRoleItem {
  id: number
  code: string
  name: string
  description?: string | null
}

export interface UserItem {
  id: number
  username: string
  real_name?: string | null
  email?: string | null
  phone?: string | null
  dept_id?: number | null
  data_scope: 'all' | 'self' | 'dept'
  post_id?: number | null
  status: number
  is_superuser: boolean
  roles: UserRoleItem[]
  created_at: string
}

export interface UserQuery {
  keyword?: string
  status?: number
  page?: number
  page_size?: number
}

export interface UserCreateIn {
  username: string
  password: string
  real_name?: string
  email?: string
  phone?: string
  dept_id?: number
  data_scope?: 'all' | 'self' | 'dept'
  post_id?: number
  role_ids?: number[]
}

export interface UserUpdateIn {
  real_name?: string
  email?: string
  phone?: string
  dept_id?: number | null
  data_scope?: 'all' | 'self' | 'dept'
  post_id?: number | null
  status?: number
  role_ids?: number[]
}
