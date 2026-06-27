import {afterEach, describe, expect, it, vi} from 'vitest'

import {writeTextToClipboard} from './useClipboard.js'

describe('writeTextToClipboard', () => {
    afterEach(() => {
        vi.restoreAllMocks()
        document.body.innerHTML = ''
        Object.defineProperty(navigator, 'clipboard', {
            configurable: true,
            value: undefined,
        })
    })

    it('uses the Clipboard API when available', async () => {
        const writeText = vi.fn().mockResolvedValue()
        Object.defineProperty(navigator, 'clipboard', {
            configurable: true,
            value: {writeText},
        })

        await writeTextToClipboard('hello')

        expect(writeText).toHaveBeenCalledWith('hello')
    })

    it('falls back to execCommand when navigator.clipboard is unavailable', async () => {
        Object.defineProperty(navigator, 'clipboard', {
            configurable: true,
            value: undefined,
        })
        const execCommand = vi.fn().mockReturnValue(true)
        Object.defineProperty(document, 'execCommand', {
            configurable: true,
            value: execCommand,
        })

        await writeTextToClipboard('log line')

        expect(execCommand).toHaveBeenCalledWith('copy')
        expect(document.querySelector('textarea')).toBeNull()
    })

    it('falls back to execCommand when Clipboard API rejects the copy', async () => {
        const writeText = vi.fn().mockRejectedValue(new Error('NotAllowedError'))
        Object.defineProperty(navigator, 'clipboard', {
            configurable: true,
            value: {writeText},
        })
        const execCommand = vi.fn().mockReturnValue(true)
        Object.defineProperty(document, 'execCommand', {
            configurable: true,
            value: execCommand,
        })

        await writeTextToClipboard('log line')

        expect(writeText).toHaveBeenCalledWith('log line')
        expect(execCommand).toHaveBeenCalledWith('copy')
        expect(document.querySelector('textarea')).toBeNull()
    })

    it('raises when the fallback copy command is rejected', async () => {
        Object.defineProperty(navigator, 'clipboard', {
            configurable: true,
            value: undefined,
        })
        Object.defineProperty(document, 'execCommand', {
            configurable: true,
            value: vi.fn().mockReturnValue(false),
        })

        await expect(writeTextToClipboard('log line')).rejects.toThrow(
            'Copy command was rejected.'
        )
        expect(document.querySelector('textarea')).toBeNull()
    })

    it('raises a controlled error when no copy API is available', async () => {
        Object.defineProperty(navigator, 'clipboard', {
            configurable: true,
            value: undefined,
        })
        Object.defineProperty(document, 'execCommand', {
            configurable: true,
            value: undefined,
        })

        await expect(writeTextToClipboard('log line')).rejects.toThrow(
            'Clipboard copy is not available in this browser.'
        )
    })
})
