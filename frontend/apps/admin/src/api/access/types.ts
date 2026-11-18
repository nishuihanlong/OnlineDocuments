export interface RoleItem {
  id: number
  code: string
  name: string
  description?: string | null
  menu_ids: number[]
  created_at: string
}

export interface RoleCreateIn {
  code: string
  name: string
  description?: string
  menu_ids?: number[]
}

export interface RoleUpdateIn {
  name?: string
  description?: string
  menu_ids?: number[]
}

export interface MenuItem {
  id: number
  name: string
  title: string
  path: string
  component: string
  redirect?: string | null
  icon?: string | null
  parent_id?: number | null
  sort: number
  permission_code?: string | null
  hidden: boolean
  enabled: boolean
  created_at: string
}

export interface MenuCreateIn {
  name: string
  title: string
  path: string
  component: string
  parent_id?: number | null
  redirect?: string
  icon?: string
  sort?: number
  permission_code?: string
  hidden?: boolean
  enabled?: boolean
}

export interface MenuUpdateIn {
  title?: string
  path?: string
  component?: string
  parent_id?: number | null
  redirect?: string
  icon?: string
  sort?: number
  permission_code?: string
  hidden?: boolean
  enabled?: boolean
}
