import {createRouter, createWebHistory} from 'vue-router'

const routes = [
    {path: '/', redirect: '/control-room'},
    {path: '/control-room', component: () => import('../views/ControlRoomView.vue'), meta: {title: 'Control Room'}},
    {path: '/status', component: () => import('../views/StatusView.vue'), meta: {title: 'Diagnostics'}},
    {path: '/media-server', component: () => import('../views/MediaServerView.vue'), meta: {title: 'Media Server'}},
    {path: '/media-player', component: () => import('../views/MediaPlayerView.vue'), meta: {title: 'Media Player'}},
    {path: '/media-paths', component: () => import('../views/MediaPathsView.vue'), meta: {title: 'Media Paths'}},
    {path: '/sala', component: () => import('../views/SalaView.vue'), meta: {title: 'Room Setup'}},
    {path: '/tv', redirect: '/sala'},
    {path: '/av', redirect: '/sala'},
    {path: '/settings', component: () => import('../views/AppSettingsView.vue'), meta: {title: 'Settings'}},
    {path: '/remote', component: () => import('../views/RemoteView.vue'), meta: {title: 'Remote'}},
    {path: '/logs', component: () => import('../views/LogsView.vue'), meta: {title: 'Logs'}},
]

export const router = createRouter({
    history: createWebHistory(),
    routes,
})

router.afterEach((to) => {
    document.title = to.meta.title ? `${to.meta.title} — HCC` : 'Home Cinema Control'
})
