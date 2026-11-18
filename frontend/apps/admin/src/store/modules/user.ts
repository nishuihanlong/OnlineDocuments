import { defineStore } from 'pinia'
import { store } from '../index'
import type { LoginResult, UserInfo } from '@/api/login/types'
import { usePermissionStore } from './permission'
import { useTagsViewStore } from './tagsView'
import router, { resetRouter } from '@/router'

interface UserState {
  userInfo?: UserInfo
  token: string
  rememberMe: boolean
  rememberedUsername: string
}

/** 细粒度权限前缀到所属粗码的映射，与后端 core.permissions 保持一致。 */
const FINE_TO_COARSE: Record<string, string> = {
  document: 'document:write',
  user: 'user:write',
  role: 'system:write',
  permission: 'system:write',
  config: 'system:write',
  notice: 'system:write',
  job: 'system:write',
  org: 'system:write',
  dept: 'system:write'
}

export const useUserStore = defineStore('user', {
  state: (): UserState => {
    return {
      userInfo: undefined,
      token: '',
      rememberMe: true,
      rememberedUsername: ''
    }
  },
  getters: {
    isAuthenticated(): boolean {
      return Boolean(this.token && this.userInfo)
    },
    /** 按钮级权限判定：超管、通配符、显式拥有该码或其所属模块粗码即放行。 */
    hasPermission(): (code: string) => boolean {
      return (code: string) => {
        const permissions = this.userInfo?.permissions ?? []
        if (
          this.userInfo?.is_superuser === true ||
          permissions.includes('*') ||
          permissions.includes(code)
        ) {
          return true
        }
        // 细码可由所属模块的粗码蕴含，兼容未展开权限列表的场景。
        const coarseCode = FINE_TO_COARSE[code.split(':')[0]]
        return coarseCode ? permissions.includes(coarseCode) : false
      }
    }
  },
  actions: {
    setSession({ accessToken, user }: LoginResult) {
      this.token = accessToken
      this.userInfo = user
    },
    rememberUsername(username: string, remember: boolean) {
      this.rememberMe = remember
      this.rememberedUsername = remember ? username : ''
    },
    clearSession() {
      this.token = ''
      this.userInfo = undefined
      usePermissionStore().reset()
      useTagsViewStore().removeAllViews(false)
      resetRouter()
    },
    async logout() {
      this.clearSession()
      await router.replace('/login')
    }
  },
  persist: {
    key: 'vea-session-v1',
    pick: ['token', 'userInfo', 'rememberMe', 'rememberedUsername']
  }
})

export const useUserStoreWithOut = () => {
  return useUserStore(store)
}
