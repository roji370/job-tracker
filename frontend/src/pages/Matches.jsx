import React, { useCallback, useEffect, useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { Search, RefreshCw, Zap, MapPin, BarChart2, ChevronDown, X } from 'lucide-react'
import JobCard from '../components/JobCard'
import { listMatches } from '../utils/api'
import './Matches.css'

// ─── Config ──────────────────────────────────────────────────────────────────

const STATUS_FILTERS = [
    { id: 'all', label: 'All Matches' },
    { id: 'high', label: '≥70% Match' },
    { id: 'saved', label: 'Saved' },
    { id: 'applied', label: 'Applied' },
]

const EXPERIENCE_OPTIONS = [
    { value: '', label: 'Any Level' },
    { value: 'entry', label: '🌱 Entry' },
    { value: 'mid', label: '💼 Mid-level' },
    { value: 'senior', label: '⭐ Senior' },
    { value: 'lead', label: '🏗️ Lead / Staff' },
    { value: 'director', label: '🎯 Director / Principal' },
]

// ─── Component ───────────────────────────────────────────────────────────────

export default function Matches() {
    const [matches, setMatches] = useState([])
    const [totalMatches, setTotalMatches] = useState(0)
    const [loading, setLoading] = useState(true)

    // Pagination
    const [currentPage, setCurrentPage] = useState(1)
    const [pageSize, setPageSize] = useState(10)

    // Search & filters (client-side search, server-side rest)
    const [search, setSearch] = useState('')
    const [statusFilter, setStatus] = useState('all')
    const [expLevel, setExpLevel] = useState('')
    const [locationQuery, setLocation] = useState('')
    const [locInput, setLocInput] = useState('')     // live location input (before committed search)

    // Unique locations extracted from current result set (for suggestions)
    const [locationSuggestions, setLocationSuggestions] = useState([])
    const [showLocSuggest, setShowLocSuggest] = useState(false)

    const load = useCallback(async () => {
        setLoading(true)
        try {
            const params = { skip: (currentPage - 1) * pageSize, limit: pageSize }
            if (search) params.q = search
            if (statusFilter === 'high') params.min_score = 70
            if (statusFilter === 'saved') params.saved_only = true
            if (statusFilter === 'applied') params.applied_only = true
            if (expLevel) params.experience_level = expLevel
            if (locationQuery) params.location = locationQuery
            const res = await listMatches(params)
            const isArray = Array.isArray(res.data)
            setMatches(isArray ? res.data : (res.data.items || []))
            setTotalMatches(isArray ? res.data.length : (res.data.total || 0))

            // Build unique location set for suggestions
            const matchesArr = isArray ? res.data : (res.data.items || [])
            const locs = [...new Set(
                matchesArr
                    .map(m => m.job?.location)
                    .filter(Boolean)
                    .map(l => l.trim())
                    .filter(l => l.toLowerCase() !== 'remote')
            )].sort()
            setLocationSuggestions(locs)
        } finally {
            setLoading(false)
        }
    }, [statusFilter, expLevel, locationQuery, currentPage, pageSize, search])

    useEffect(() => { load() }, [load, currentPage, pageSize, search])

    // Reset pagination when search or filters change
    useEffect(() => {
        setCurrentPage(1)
    }, [search, statusFilter, expLevel, locationQuery])

    const totalPages = Math.ceil(totalMatches / pageSize)

    const hasActiveFilters = statusFilter !== 'all' || expLevel || locationQuery

    const clearAllFilters = () => {
        setStatus('all')
        setExpLevel('')
        setLocation('')
        setLocInput('')
        setSearch('')
    }

    const applyLocation = (val) => {
        setLocation(val)
        setLocInput(val)
        setShowLocSuggest(false)
    }

    return (
        <div className="page">
            <div className="page-header matches-page-header">
                <div>
                    <h1>Job <span className="gradient-text">Matches</span></h1>
                    <p>AI-scored matches between your resume and scraped jobs</p>
                </div>
                <div className="matches-header-actions">
                    {hasActiveFilters && (
                        <motion.button
                            initial={{ opacity: 0, scale: 0.9 }}
                            animate={{ opacity: 1, scale: 1 }}
                            className="btn btn-ghost clear-filters-btn"
                            onClick={clearAllFilters}
                            id="clear-filters-btn"
                        >
                            <X size={13} /> Clear filters
                        </motion.button>
                    )}
                    <button className="btn btn-ghost" onClick={load} id="matches-refresh-btn">
                        <RefreshCw size={14} /> Refresh
                    </button>
                </div>
            </div>

            {/* ── Filter row ───────────────────────────────────────────── */}
            <div className="matches-filters">

                {/* Search */}
                <div className="search-box">
                    <Search size={15} className="search-icon" />
                    <input
                        id="matches-search"
                        type="text"
                        placeholder="Search title or company…"
                        value={search}
                        onChange={e => setSearch(e.target.value)}
                    />
                </div>

                {/* Status pill tabs */}
                <div className="filter-tabs" role="group" aria-label="Status filter">
                    {STATUS_FILTERS.map(f => (
                        <button
                            key={f.id}
                            id={`filter-${f.id}`}
                            className={`filter-tab ${statusFilter === f.id ? 'active' : ''}`}
                            onClick={() => setStatus(f.id)}
                        >
                            {f.label}
                        </button>
                    ))}
                </div>

                {/* Experience level dropdown */}
                <div className="select-wrapper" title="Filter by experience level">
                    <BarChart2 size={14} className="select-icon" />
                    <select
                        id="exp-level-select"
                        value={expLevel}
                        onChange={e => setExpLevel(e.target.value)}
                        className={`filter-select ${expLevel ? 'filter-select--active' : ''}`}
                    >
                        {EXPERIENCE_OPTIONS.map(o => (
                            <option key={o.value} value={o.value}>{o.label}</option>
                        ))}
                    </select>
                    <ChevronDown size={13} className="select-chevron" />
                </div>

                {/* Location typeahead */}
                <div className="location-filter-wrap">
                    <div className="search-box location-box">
                        <MapPin size={14} className="search-icon" />
                        <input
                            id="location-filter"
                            type="text"
                            placeholder="Filter by location…"
                            value={locInput}
                            onChange={e => {
                                setLocInput(e.target.value)
                                setShowLocSuggest(true)
                            }}
                            onBlur={() => setTimeout(() => setShowLocSuggest(false), 150)}
                            onFocus={() => { if (locInput) setShowLocSuggest(true) }}
                            onKeyDown={e => {
                                if (e.key === 'Enter') applyLocation(locInput)
                                if (e.key === 'Escape') { setShowLocSuggest(false); applyLocation('') }
                            }}
                            className={locationQuery ? 'filter-select--active' : ''}
                        />
                        {locInput && (
                            <button
                                className="loc-clear-btn"
                                onMouseDown={() => applyLocation('')}
                                aria-label="Clear location"
                            >
                                <X size={12} />
                            </button>
                        )}
                    </div>
                    {/* Suggestions dropdown */}
                    <AnimatePresence>
                        {showLocSuggest && locationSuggestions.length > 0 && (
                            <motion.ul
                                className="loc-suggestions"
                                initial={{ opacity: 0, y: -4 }}
                                animate={{ opacity: 1, y: 0 }}
                                exit={{ opacity: 0, y: -4 }}
                                transition={{ duration: 0.12 }}
                            >
                                {locationSuggestions
                                    .filter(l => !locInput || l.toLowerCase().includes(locInput.toLowerCase()))
                                    .slice(0, 8)
                                    .map(l => (
                                        <li key={l}>
                                            <button onMouseDown={() => applyLocation(l)} className="loc-suggestion-item">
                                                <MapPin size={11} /> {l}
                                            </button>
                                        </li>
                                    ))
                                }
                            </motion.ul>
                        )}
                    </AnimatePresence>
                </div>

            </div>

            {/* ── Active filter tags ───────────────────────────────────── */}
            {(expLevel || locationQuery) && (
                <div className="active-filter-tags">
                    {expLevel && (
                        <span className="filter-tag">
                            {EXPERIENCE_OPTIONS.find(o => o.value === expLevel)?.label}
                            <button onClick={() => setExpLevel('')} aria-label="Remove"><X size={11} /></button>
                        </span>
                    )}
                    {locationQuery && (
                        <span className="filter-tag">
                            <MapPin size={11} /> {locationQuery}
                            <button onClick={() => { setLocation(''); setLocInput('') }} aria-label="Remove"><X size={11} /></button>
                        </span>
                    )}
                </div>
            )}

            {!loading && (
                <p className="matches-count">
                    {totalMatches} match{totalMatches !== 1 ? 'es' : ''}
                    {search && ` for "${search}"`}
                </p>
            )}

            {/* ── Match list ───────────────────────────────────────────── */}
            {loading ? (
                <div className="section-grid">
                    {[...Array(4)].map((_, i) => (
                        <div key={i} className="skeleton" style={{ height: 160 }} />
                    ))}
                </div>
            ) : matches.length === 0 ? (
                <div className="card empty-state">
                    <Zap size={40} />
                    <p>No matches found. Try running the pipeline or adjusting filters.</p>
                    {hasActiveFilters && (
                        <button className="btn btn-secondary" onClick={clearAllFilters}>
                            <X size={14} /> Clear all filters
                        </button>
                    )}
                </div>
            ) : (
                <>
                    <AnimatePresence>
                        <div className="section-grid">
                            {matches.map(m => (
                                <JobCard key={m.id} match={m} onUpdate={load} />
                            ))}
                        </div>
                    </AnimatePresence>

                    {/* ── Pagination Controls ────────────────────────────────── */}
                    <div className="pagination-controls" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '2rem' }}>
                        <div className="page-size-selector">
                            <span style={{ fontSize: '0.875rem', color: 'var(--color-text-muted)', marginRight: '0.5rem' }}>Show:</span>
                            <select
                                value={pageSize}
                                onChange={e => { setPageSize(Number(e.target.value)); setCurrentPage(1); }}
                                style={{ background: 'var(--color-surface-2)', color: 'var(--color-text)', border: '1px solid var(--color-border)', borderRadius: 'var(--radius-sm)', padding: '0.3rem 0.6rem', outline: 'none' }}
                            >
                                <option value={10}>10</option>
                                <option value={20}>20</option>
                                <option value={50}>50</option>
                            </select>
                        </div>
                        <div className="page-numbers" style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
                            <button
                                className="btn btn-secondary"
                                disabled={currentPage === 1}
                                onClick={() => setCurrentPage(p => p - 1)}
                                style={{ padding: '0.3rem 0.6rem', fontSize: '0.875rem' }}
                            >
                                Prev
                            </button>
                            <span style={{ fontSize: '0.875rem', color: 'var(--color-text-muted)' }}>Page {currentPage} of {totalPages || 1}</span>
                            <button
                                className="btn btn-secondary"
                                disabled={currentPage === totalPages || totalPages === 0}
                                onClick={() => setCurrentPage(p => p + 1)}
                                style={{ padding: '0.3rem 0.6rem', fontSize: '0.875rem' }}
                            >
                                Next
                            </button>
                        </div>
                    </div>
                </>
            )}
        </div>
    )
}
