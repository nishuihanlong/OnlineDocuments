export interface OrgItem {
  id: number
  name: string
  code: string
  parent_id?: number | null
  sort: number
  leader?: string | null
  phone?: string | null
  remark?: string | null
  created_at: string
  updated_at: string
}

export interface OrgCreateIn {
  name: string
  code: string
  parent_id?: number | null
  sort?: number
  leader?: string
  phone?: string
  remark?: string
}

export interface OrgUpdateIn {
  name?: string
  parent_id?: number | null
  sort?: number
  leader?: string
  phone?: string
  remark?: string
}

export interface DeptItem {
  id: number
  name: string
  code: string
  org_id?: number | null
  parent_id?: number | null
  sort: number
  leader?: string | null
  phone?: string | null
  created_at: string
  updated_at: string
}

export interface DeptCreateIn {
  name: string
  code?: string
  org_id?: number | null
  parent_id?: number | null
  sort?: number
  leader?: string
  phone?: string
}

export interface DeptUpdateIn {
  name?: string
  code?: string
  org_id?: number | null
  parent_id?: number | null
  sort?: number
  leader?: string
  phone?: string
}
