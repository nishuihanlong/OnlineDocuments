import request from '@/request'
import type { LoginParams, LoginResult, RegisterParams, RegisterResult } from './types'

/** 登录：POST /v1/auth/login，返回 accessToken 与用户信息。 */
export const loginApi = (data: LoginParams) => {
  return request.post<LoginResult>({ url: '/v1/auth/login', data })
}

/** 注册：POST /v1/auth/register，注册后需管理员激活。 */
export const registerApi = (data: RegisterParams) => {
  return request.post<RegisterResult>({ url: '/v1/auth/register', data })
}

/** 登出审计：POST /v1/auth/logout。 */
export const logoutApi = () => {
  return request.post({ url: '/v1/auth/logout' })
}

/** 动态菜单：GET /v1/system/menus，返回前端 AppCustomRouteRecordRaw 形状。 */
export const getRouteListApi = () => {
  return request.get<AppCustomRouteRecordRaw[]>({ url: '/v1/system/menus' })
}
