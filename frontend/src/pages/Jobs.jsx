import React, { useCallback, useEffect, useState } from 'react'
import { Search, ExternalLink, MapPin, Building2, Clock, RefreshCw } from 'lucide-react'
import { listJobs } from '../utils/api'
import { formatDate } from '../hooks/useFetch'
import './Jobs.css'

export default function Jobs() {
    const [jobs, setJobs] = useState([])
    const [loading, setLoading] = useState(true)
    const [search, setSearch] = useState('')

    const load = useCallback(async () => {
        setLoading(true)
        try {
            const res = await listJobs({ active_only: true, limit: 100 })
            setJobs(res.data)
        } finally {
            setLoading(false)
        }
    }, [])

    useEffect(() => { load() }, [load])

    const displayed = jobs.filter((j) => {
        if (!search) return true
        const q = search.toLowerCase()
        return (
            j.title?.toLowerCase().includes(q) ||
            j.company?.toLowerCase().includes(q) ||
            j.location?.toLowerCase().includes(q)
        )
    })

    return (
        <div className="page">
            <div className="page-header">
                <h1>All <span className="gradient-text">Jobs</span></h1>
                <p>Raw scraped job listings from Amazon Jobs</p>
            </div>

            <div className="jobs-toolbar">
                <div className="search-box" style={{ flex: 1 }}>
                    <Search size={16} className="search-icon" style={{ position: 'absolute', left: '0.75rem', top: '50%', transform: 'translateY(-50%)', color: 'var(--color-text-muted)', pointerEvents: 'none' }} />
                    <input
                        id="jobs-search"
                        type="text"
                        placeholder="Search jobs…"
                        value={search}
                        onChange={(e) => setSearch(e.target.value)}
                        style={{ paddingLeft: '2.25rem' }}
                    />
                </div>
                <button className="btn btn-ghost" onClick={load} id="jobs-refresh-btn">
                    <RefreshCw size={14} /> Refresh
                </button>
            </div>

            {!loading && (
                <p className="matches-count">{displayed.length} job{displayed.length !== 1 ? 's' : ''}</p>
            )}

            {loading ? (
                <div className="section-grid grid-2">
                    {[...Array(6)].map((_, i) => (
                        <div key={i} className="skeleton" style={{ height: 130 }} />
                    ))}
                </div>
            ) : displayed.length === 0 ? (
                <div className="card empty-state">
                    No jobs scraped yet. Run the pipeline from the Dashboard.
                </div>
            ) : (
                <div className="section-grid grid-2">
                    {displayed.map((job) => (
                        <div key={job.id} className="card job-list-card">
                            <div className="jlc-header">
                                <div className="jlc-logo">{job.company?.charAt(0) || 'J'}</div>
                                <div className="jlc-meta">
                                    <h3 className="jlc-title">{job.title}</h3>
                                    <div className="jlc-tags">
                                        <span className="tag"><Building2 size={11} /> {job.company}</span>
                                        {job.location && <span className="tag"><MapPin size={11} /> {job.location}</span>}
                                        {job.employment_type && <span className="tag"><Clock size={11} /> {job.employment_type}</span>}
                                    </div>
                                </div>
                            </div>
                            {job.description && (
                                <p className="jlc-desc">{job.description.slice(0, 160)}…</p>
                            )}
                            <div className="jlc-footer">
                                {job.posted_date && <span className="jlc-posted">📅 {job.posted_date}</span>}
                                {job.url && (
                                    <a href={job.url} target="_blank" rel="noopener noreferrer" className="btn btn-secondary" id={`job-view-${job.id}`}>
                                        <ExternalLink size={14} /> View
                                    </a>
                                )}
                            </div>
                        </div>
                    ))}
                </div>
            )}
        </div>
    )
}
