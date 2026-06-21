import {defineConfig} from 'vite'
import vue from '@vitejs/plugin-vue'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
    plugins: [vue(), tailwindcss()],
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
