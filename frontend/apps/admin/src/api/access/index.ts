import request from '@/request'
import type {
  MenuCreateIn,
  MenuItem,
  MenuUpdateIn,
  RoleCreateIn,
  RoleItem,
  RoleUpdateIn
} from './types'

export const getRoleListApi = () => request.get<RoleItem[]>({ url: '/v1/roles' })

export const createRoleApi = (data: RoleCreateIn) =>
  request.post<RoleItem>({ url: '/v1/roles', data })

export const updateRoleApi = (id: number, data: RoleUpdateIn) =>
  request.put<RoleItem>({ url: `/v1/roles/${id}`, data })

export const deleteRoleApi = (id: number) =>
  request.delete<null>({ url: `/v1/roles/${id}` })

export const getPermissionListApi = () =>
  request.get<MenuItem[]>({ url: '/v1/permissions' })

export const createPermissionApi = (data: MenuCreateIn) =>
  request.post<MenuItem>({ url: '/v1/permissions', data })

export const updatePermissionApi = (id: number, data: MenuUpdateIn) =>
  request.put<MenuItem>({ url: `/v1/permissions/${id}`, data })

export const deletePermissionApi = (id: number) =>
  request.delete<null>({ url: `/v1/permissions/${id}` })
