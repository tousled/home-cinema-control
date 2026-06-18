import {onMounted, onUnmounted} from 'vue'

export function usePoll(fn, interval) {
    let timer = null

    function start() {
        if (!timer) timer = setInterval(fn, interval)
    }

    function stop() {
        clearInterval(timer)
        timer = null
    }

    function onVisibilityChange() {
        if (document.hidden) {
            stop()
        } else {
            fn()
            start()
        }
    }

    onMounted(() => {
        start()
        document.addEventListener('visibilitychange', onVisibilityChange)
    })

    onUnmounted(() => {
        stop()
        document.removeEventListener('visibilitychange', onVisibilityChange)
    })
}
