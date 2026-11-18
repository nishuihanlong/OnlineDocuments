declare module 'vue' {
  export interface GlobalComponents {
    Icon: (typeof import('@vea/components'))['Icon']
    IconPicker: (typeof import('../src/components/IconPicker/index.vue'))['default']
  }
}

export {}
