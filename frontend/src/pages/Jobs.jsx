import React, { useCallback, useEffect, useState } from 'react'
import { Search, ExternalLink, MapPin, Building2, Clock, RefreshCw } from 'lucide-react'
import { listJobs } from '../utils/api'
import { formatDate } from '../hooks/useFetch'
import './Jobs.css'

export default function Jobs() {
    const [jobs, setJobs] = useState([])
    const [totalJobs, setTotalJobs] = useState(0)
    const [loading, setLoading] = useState(true)
    const [search, setSearch] = useState('')

    // Pagination
    const [currentPage, setCurrentPage] = useState(1)
    const [pageSize, setPageSize] = useState(20)

    const load = useCallback(async () => {
        setLoading(true)
        try {
            const params = { active_only: true, skip: (currentPage - 1) * pageSize, limit: pageSize }
            if (search) params.search = search
            const res = await listJobs(params)

            const isArray = Array.isArray(res.data)
            setJobs(isArray ? res.data : (res.data.items || []))
            setTotalJobs(isArray ? res.data.length : (res.data.total || 0))
        } finally {
            setLoading(false)
        }
    }, [currentPage, pageSize, search])

    useEffect(() => { load() }, [load])

    // Reset pagination when search changes
    useEffect(() => {
        setCurrentPage(1)
    }, [search])

    const totalPages = Math.ceil(totalJobs / pageSize)

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
                <p className="matches-count">{totalJobs} job{totalJobs !== 1 ? 's' : ''}</p>
            )}

            {loading ? (
                <div className="section-grid grid-2">
                    {[...Array(6)].map((_, i) => (
                        <div key={i} className="skeleton" style={{ height: 130 }} />
                    ))}
                </div>
            ) : jobs.length === 0 ? (
                <div className="card empty-state">
                    No jobs scraped yet. Run the pipeline from the Dashboard.
                </div>
            ) : (
                <>
                    <div className="section-grid grid-2">
                        {jobs.map((job) => (
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

                    {/* Pagination Controls */}
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
