import { defineConfig, loadEnv } from 'vite'
import devServer from '@hono/vite-dev-server'
import ssrPlugin from 'vite-ssr-components/plugin'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  return {
    plugins: [
      devServer({
        entry: 'src/index.tsx',
        env
      }),
      ssrPlugin()
    ]
  }
})
