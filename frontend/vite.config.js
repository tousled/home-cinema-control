import {defineConfig} from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
    plugins: [vue()],
    test: {
        environment: 'jsdom',
    },
    server: {
        proxy: {
            '/api': {
                target: 'http://localhost:8090',
                changeOrigin: true,
            },
        },
    },
    build: {
        outDir: 'dist',
    },
})
