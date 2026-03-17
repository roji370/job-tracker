import { useState, useEffect, useCallback } from 'react'

/**
 * Generic data-fetching hook.
 * @param {Function} fetchFn - API function to call
 * @param {any} defaultValue - Default data value
 * @param {boolean} immediate - Fetch immediately on mount
 */
export function useFetch(fetchFn, defaultValue = null, immediate = true) {
    const [data, setData] = useState(defaultValue)
    const [loading, setLoading] = useState(immediate)
    const [error, setError] = useState(null)

    const execute = useCallback(async (...args) => {
        setLoading(true)
        setError(null)
        try {
            const res = await fetchFn(...args)
            setData(res.data)
            return res.data
        } catch (err) {
            setError(err)
            throw err
        } finally {
            setLoading(false)
        }
    }, [fetchFn])

    useEffect(() => {
        if (immediate) execute()
    }, []) // eslint-disable-line

    return { data, loading, error, refetch: execute }
}

/**
 * Score to color utility.
 */
export function scoreColor(score) {
    if (score >= 80) return 'var(--color-success)'
    if (score >= 65) return 'var(--color-warning)'
    return 'var(--color-error)'
}

export function scoreBadgeClass(score) {
    if (score >= 70) return 'badge-success'
    if (score >= 50) return 'badge-warning'
    return 'badge-error'
}

export function formatDate(iso) {
    if (!iso) return '—'
    return new Date(iso).toLocaleDateString('en-US', {
        year: 'numeric', month: 'short', day: 'numeric',
    })
}

export function truncate(str, n = 180) {
    if (!str) return ''
    return str.length > n ? str.slice(0, n) + '…' : str
}
