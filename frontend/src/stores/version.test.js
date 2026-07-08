import {createPinia, setActivePinia} from 'pinia'
import {beforeEach, describe, expect, it} from 'vitest'
import {useVersionStore} from './version.js'

describe('version store', () => {
    beforeEach(() => {
        setActivePinia(createPinia())
    })

    it('clears the navbar update indicator when the latest check is up to date', () => {
        const store = useVersionStore()

        store.setVersionInfo({new_version: true})
        expect(store.newVersionAvailable).toBe(true)

        store.setVersionInfo({new_version: false})
        expect(store.newVersionAvailable).toBe(false)
    })
})
