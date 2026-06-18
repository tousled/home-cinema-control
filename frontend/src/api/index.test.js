import {describe, expect, it} from 'vitest'
import {api} from './index.js'

describe('api config save surface', () => {
    it('does not expose full-config saves to frontend setup screens', () => {
        expect(api.saveConfig).toBeUndefined()
        expect(api.saveConfigSection).toEqual(expect.any(Function))
    })
})
