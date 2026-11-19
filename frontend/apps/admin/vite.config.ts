import { resolve } from 'path'
import { loadEnv } from 'vite'
import type { UserConfig, ConfigEnv } from 'vite'
import Vue from '@vitejs/plugin-vue'
import VueJsx from '@vitejs/plugin-vue-jsx'
import { viteMockServe } from 'vite-plugin-mock'
import VueI18nPlugin from '@intlify/unplugin-vue-i18n/vite'
import UnoCSS from 'unocss/vite'
import ElementPlus from 'unplugin-element-plus/vite'

const root = process.cwd()

function pathResolve(dir: string) {
  return resolve(root, '.', dir)
}

export default ({ mode }: ConfigEnv): UserConfig => {
  const env = loadEnv(mode, root)
  return {
    base: env.VITE_BASE_PATH,
    plugins: [
      Vue(),
      VueJsx(),
      ElementPlus(),
      VueI18nPlugin({
        runtimeOnly: true,
        compositionOnly: true,
        include: [resolve(import.meta.dirname, 'src/locales/**')]
      }),
      env.VITE_USE_MOCK === 'true'
        ? viteMockServe({
            ignore: /^_/,
            mockPath: 'mock'
          })
        : undefined,
      UnoCSS()
    ],

    resolve: {
      alias: [
        {
          find: /@\//,
          replacement: `${pathResolve('src')}/`
        }
      ]
    },
    build: {
      // ooxml-core 使用 BigInt（8n），需 es2020+ 目标，否则大整数字面量会被降级处理
      target: 'es2020',
      // Vite 8 默认用 lightningcss 压缩 CSS，对含 @layer 注释的样式会误判为空选择器，
      // 改用 esbuild 压缩以兼容（与 ooxml 等依赖无关）。
      cssMinify: 'esbuild',
      outDir: env.VITE_OUT_DIR || 'dist',
      sourcemap: env.VITE_SOURCEMAP === 'true',
      cssCodeSplit: !(env.VITE_USE_CSS_SPLIT === 'false'),
      cssTarget: ['chrome31'],
      rolldownOptions: {
        output: {
          codeSplitting: {
            groups: [
              {
                name: 'zrender',
                test: /node_modules[\\/]zrender[\\/]/
              }
            ]
          }
        }
      }
    },
    server: {
      port: 4000,
      proxy: {
        '/api': {
          target: 'http://127.0.0.1:8000',
          changeOrigin: true,
          ws: true,
          rewrite: (path) => path.replace(/^\/api/, '')
        }
      },
      hmr: {
        overlay: false
      },
      host: '0.0.0.0'
    }
  }
}
