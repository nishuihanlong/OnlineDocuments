import { useUserStoreWithOut } from '@/store/modules/user'

/** 页面按钮级权限判定，返回 can('resource:action') 形态的便捷函数。 */
export const usePermission = () => {
  const userStore = useUserStoreWithOut()
  return {
    can: (code: string): boolean => userStore.hasPermission(code)
  }
}
