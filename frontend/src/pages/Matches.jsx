import React, { useCallback, useEffect, useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { Search, Filter, RefreshCw, Zap, Bookmark, CheckCircle } from 'lucide-react'
import JobCard from '../components/JobCard'
import { listMatches } from '../utils/api'
import './Matches.css'

const FILTERS = [
    { id: 'all', label: 'All Matches' },
    { id: 'high', label: '≥70% Match' },
    { id: 'saved', label: 'Saved' },
    { id: 'applied', label: 'Applied' },
]

export default function Matches() {
    const [matches, setMatches] = useState([])
    const [loading, setLoading] = useState(true)
    const [search, setSearch] = useState('')
    const [filter, setFilter] = useState('all')

    const load = useCallback(async () => {
        setLoading(true)
        try {
            const params = {}
            if (filter === 'high') params.min_score = 70
            if (filter === 'saved') params.saved_only = true
            if (filter === 'applied') params.applied_only = true
            const res = await listMatches(params)
            setMatches(res.data)
        } finally {
            setLoading(false)
        }
    }, [filter])

    useEffect(() => { load() }, [load])

    const displayed = matches.filter((m) => {
        if (!search) return true
        const q = search.toLowerCase()
        return (
            m.job?.title?.toLowerCase().includes(q) ||
            m.job?.company?.toLowerCase().includes(q) ||
            m.job?.location?.toLowerCase().includes(q)
        )
    })

    return (
        <div className="page">
            <div className="page-header">
                <h1>Job <span className="gradient-text">Matches</span></h1>
                <p>AI-scored matches between your resume and scraped jobs</p>
            </div>

            {/* Toolbar */}
            <div className="matches-toolbar">
                <div className="search-box">
                    <Search size={16} className="search-icon" />
                    <input
                        id="matches-search"
                        type="text"
                        placeholder="Search by title, company, location…"
                        value={search}
                        onChange={(e) => setSearch(e.target.value)}
                    />
                </div>

                <div className="filter-tabs">
                    {FILTERS.map((f) => (
                        <button
                            key={f.id}
                            id={`filter-${f.id}`}
                            className={`filter-tab ${filter === f.id ? 'active' : ''}`}
                            onClick={() => setFilter(f.id)}
                        >
                            {f.label}
                        </button>
                    ))}
                </div>

                <button className="btn btn-ghost" onClick={load} id="matches-refresh-btn">
                    <RefreshCw size={14} /> Refresh
                </button>
            </div>

            {/* Results count */}
            {!loading && (
                <p className="matches-count">
                    {displayed.length} match{displayed.length !== 1 ? 'es' : ''}
                    {search && ` for "${search}"`}
                </p>
            )}

            {/* Match list */}
            {loading ? (
                <div className="section-grid">
                    {[...Array(4)].map((_, i) => (
                        <div key={i} className="skeleton" style={{ height: 160 }} />
                    ))}
                </div>
            ) : displayed.length === 0 ? (
                <div className="card empty-state">
                    <Zap size={40} />
                    <p>No matches found. Try running the pipeline or changing filters.</p>
                </div>
            ) : (
                <AnimatePresence>
                    <div className="section-grid">
                        {displayed.map((m) => (
                            <JobCard key={m.id} match={m} onUpdate={load} />
                        ))}
                    </div>
                </AnimatePresence>
            )}
        </div>
    )
}
