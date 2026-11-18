import request from '@/request'
import type { PageResult } from '@/api/system/types'
import type { UserCreateIn, UserItem, UserQuery, UserUpdateIn } from './types'

export const getUserListApi = (params: UserQuery) =>
  request.get<PageResult<UserItem>>({ url: '/v1/users', params })

export const createUserApi = (data: UserCreateIn) =>
  request.post<UserItem>({ url: '/v1/users', data })

export const updateUserApi = (id: number, data: UserUpdateIn) =>
  request.put<UserItem>({ url: `/v1/users/${id}`, data })

export const disableUserApi = (id: number) =>
  request.delete<null>({ url: `/v1/users/${id}` })

export const activateUserApi = (id: number) =>
  request.post<UserItem>({ url: `/v1/users/${id}/activate` })
