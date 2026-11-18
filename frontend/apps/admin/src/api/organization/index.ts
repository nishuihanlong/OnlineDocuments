import request from '@/request'
import type {
  DeptCreateIn,
  DeptItem,
  DeptUpdateIn,
  OrgCreateIn,
  OrgItem,
  OrgUpdateIn
} from './types'

export const getOrgListApi = () => request.get<OrgItem[]>({ url: '/v1/orgs' })

export const createOrgApi = (data: OrgCreateIn) =>
  request.post<OrgItem>({ url: '/v1/orgs', data })

export const updateOrgApi = (id: number, data: OrgUpdateIn) =>
  request.put<OrgItem>({ url: `/v1/orgs/${id}`, data })

export const deleteOrgApi = (id: number) =>
  request.delete<null>({ url: `/v1/orgs/${id}` })

export const getDeptListApi = () => request.get<DeptItem[]>({ url: '/v1/depts' })

export const createDeptApi = (data: DeptCreateIn) =>
  request.post<DeptItem>({ url: '/v1/depts', data })

export const updateDeptApi = (id: number, data: DeptUpdateIn) =>
  request.put<DeptItem>({ url: `/v1/depts/${id}`, data })

export const deleteDeptApi = (id: number) =>
  request.delete<null>({ url: `/v1/depts/${id}` })
