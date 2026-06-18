import {useI18n} from 'vue-i18n'

// Codes whose suggestion text depends on the mount protocol that was attempted.
const MOUNT_FAILED_CODE = 'OPPO_MOUNT_FAILED'
const PATH_TEST_FAILED_CODE = 'PATH_TEST_FAILED'

export function useDiagnosticText() {
    const {t, te} = useI18n()

    function detailParam(diag) {
        const detail = diag?.details?.detail
        return detail ? String(detail) : t('x-diag-detail-unknown')
    }

    function genericParams(diag) {
        const details = diag?.details || {}
        const params = {}
        if ('detail' in details) params.detail = detailParam(diag)
        if ('result' in details) params.result = details.result
        if ('error' in details) params.error = details.error
        return params
    }

    function resolve(diag, kind) {
        if (!diag?.code) return diag?.[kind] || ''

        if (diag.code === MOUNT_FAILED_CODE) {
            const protocol = diag.details?.protocol === 'cifs' ? 'cifs' : 'nfs'
            const key = `x-diag-${kind}-${MOUNT_FAILED_CODE}-${protocol}`
            let text = te(key) ? t(key, genericParams(diag)) : (diag[kind] || '')
            if (kind === 'suggestion' && diag.details?.smb_not_attempted) {
                text += ' ' + t('x-diag-suggestion-smb-hint')
            }
            return text
        }

        if (diag.code === PATH_TEST_FAILED_CODE && kind === 'suggestion') {
            const key = `x-diag-suggestion-${PATH_TEST_FAILED_CODE}`
            let text = te(key) ? t(key) : (diag.suggestion || '')
            if (diag.details?.smb_not_attempted) {
                text += ' ' + t('x-diag-suggestion-smb-hint')
            }
            return text
        }

        const key = `x-diag-${kind}-${diag.code}`
        if (!te(key)) return diag[kind] || ''
        return t(key, genericParams(diag))
    }

    return {
        diagnosticReason: (diag) => resolve(diag, 'reason'),
        diagnosticSuggestion: (diag) => resolve(diag, 'suggestion'),
    }
}
