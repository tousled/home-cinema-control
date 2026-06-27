export async function writeTextToClipboard(text) {
    if (navigator.clipboard?.writeText) {
        try {
            await navigator.clipboard.writeText(text)
            return
        } catch {
            // Some browsers expose the Clipboard API but reject it outside a
            // secure context or after permission changes. Try the legacy path.
        }
    }

    copyWithLegacySelection(text)
}

function copyWithLegacySelection(text) {
    if (typeof document.execCommand !== 'function') {
        throw new Error('Clipboard copy is not available in this browser.')
    }

    const textarea = document.createElement('textarea')
    textarea.value = text
    textarea.setAttribute('readonly', '')
    textarea.style.position = 'fixed'
    textarea.style.top = '-9999px'
    textarea.style.left = '-9999px'

    document.body.appendChild(textarea)
    textarea.focus()
    textarea.select()

    try {
        const copied = document.execCommand('copy')
        if (!copied) {
            throw new Error('Copy command was rejected.')
        }
    } finally {
        document.body.removeChild(textarea)
    }
}
