import React, { useCallback, useEffect, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
    Zap, Briefcase, BookmarkCheck, CheckCircle,
    Play, RefreshCw, AlertCircle, X, Building2, ChevronDown,
} from 'lucide-react'
import {
    AreaChart, Area, XAxis, YAxis, CartesianGrid,
    Tooltip, ResponsiveContainer,
} from 'recharts'
import StatCard from '../components/StatCard'
import JobCard from '../components/JobCard'
import { getMatchStats, listMatches, triggerPipelineAsync, getLastRun, listCompanies } from '../utils/api'
import toast from 'react-hot-toast'
import './Dashboard.css'

const stagger = {
    container: { hidden: {}, visible: { transition: { staggerChildren: 0.08 } } },
    item: { hidden: { opacity: 0, y: 20 }, visible: { opacity: 1, y: 0 } },
}

const ATS_COLORS = {
    greenhouse: '#24a148',
    lever: '#3b82f6',
}

export default function Dashboard() {
    const [stats, setStats] = useState(null)
    const [topMatches, setTopMatches] = useState([])
    const [lastRun, setLastRun] = useState(null)
    const [running, setRunning] = useState(false)
    const [loading, setLoading] = useState(true)

    // Company picker modal state
    const [showPicker, setShowPicker] = useState(false)
    const [companies, setCompanies] = useState([])
    const [selectedSlugs, setSelectedSlugs] = useState([]) // empty = all
    const [companiesLoading, setCompaniesLoading] = useState(false)

    const load = useCallback(async () => {
        try {
            const [statsRes, matchesRes, lastRunRes] = await Promise.all([
                getMatchStats(),
                listMatches({ min_score: 60, limit: 6 }),
                getLastRun(),
            ])
            setStats(statsRes.data)
            setTopMatches(matchesRes.data)
            setLastRun(lastRunRes.data)
        } catch {
            // errors toasted by API interceptor
        } finally {
            setLoading(false)
        }
    }, [])

    useEffect(() => { load() }, [load])

    // Prevent body scroll when picker is open
    useEffect(() => {
        if (showPicker) {
            document.body.style.overflow = 'hidden'
        } else {
            document.body.style.overflow = ''
        }
        return () => {
            document.body.style.overflow = ''
        }
    }, [showPicker])

    const openPicker = async () => {
        setShowPicker(true)
        if (companies.length === 0) {
            setCompaniesLoading(true)
            try {
                const res = await listCompanies()
                setCompanies(res.data)
            } catch {
                toast.error('Could not load company list.')
            } finally {
                setCompaniesLoading(false)
            }
        }
    }

    const toggleSlug = (slug) => {
        setSelectedSlugs(prev =>
            prev.includes(slug) ? prev.filter(s => s !== slug) : [...prev, slug]
        )
    }

    const selectAll = () => setSelectedSlugs([])
    const isAllSelected = selectedSlugs.length === 0

    const handleRunPipeline = async () => {
        setShowPicker(false)
        setRunning(true)
        const slugs = selectedSlugs.length > 0 ? selectedSlugs : null
        const label = slugs
            ? slugs.map(s => companies.find(c => c.slug === s)?.name || s).join(', ')
            : 'all companies'
        toast.loading(`Running pipeline for ${label}…`, { id: 'pipeline' })
        try {
            const res = await triggerPipelineAsync(slugs)
            toast.success(
                `Pipeline started in background. Check last run for results soon.`,
                { id: 'pipeline', duration: 5000 }
            )
            load()
        } catch {
            toast.error('Pipeline failed.', { id: 'pipeline' })
        } finally {
            setRunning(false)
        }
    }

    // Build chart data from last 7 "sessions" (mocked from lastRun data)
    const chartData = lastRun && lastRun.jobs_scraped
        ? [
            { name: 'Previous', jobs: Math.max(0, (lastRun.jobs_scraped || 0) - 4), matches: Math.max(0, (lastRun.matches_created || 0) - 2) },
            { name: 'This Run', jobs: lastRun.jobs_scraped || 0, matches: lastRun.matches_created || 0 },
        ]
        : [
            { name: 'Run 1', jobs: 12, matches: 5 },
            { name: 'Run 2', jobs: 18, matches: 9 },
            { name: 'Run 3', jobs: 20, matches: 14 },
            { name: 'Latest', jobs: 15, matches: 10 },
        ]

    return (
        <div className="page">
            {/* Page Header */}
            <div className="page-header dashboard-header">
                <div>
                    <h1>Dashboard <span className="gradient-text">Overview</span></h1>
                    <p>AI-powered job matching at a glance</p>
                </div>
                <button
                    className={`btn btn-primary ${running ? 'btn-loading' : ''}`}
                    onClick={openPicker}
                    disabled={running}
                    id="run-pipeline-btn"
                >
                    {running
                        ? <><div className="spinner" />Running…</>
                        : <><Play size={16} />Run Pipeline<ChevronDown size={14} /></>
                    }
                </button>
            </div>

            {/* Company Picker Modal */}
            <AnimatePresence>
                {showPicker && (
                    <motion.div
                        className="modal-backdrop"
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        onClick={() => setShowPicker(false)}
                    >
                        <motion.div
                            className="modal-box company-picker-modal"
                            initial={{ opacity: 0, scale: 0.92, y: 20 }}
                            animate={{ opacity: 1, scale: 1, y: 0 }}
                            exit={{ opacity: 0, scale: 0.92, y: 20 }}
                            transition={{ type: 'spring', damping: 22, stiffness: 300 }}
                            onClick={e => e.stopPropagation()}
                        >
                            {/* Modal header */}
                            <div className="modal-header">
                                <div className="modal-title-group">
                                    <Building2 size={20} className="modal-title-icon" />
                                    <div>
                                        <h2 className="modal-title">Select Companies</h2>
                                        <p className="modal-subtitle">Choose which companies to scrape, or run all at once.</p>
                                    </div>
                                </div>
                                <button className="btn-icon" onClick={() => setShowPicker(false)} aria-label="Close">
                                    <X size={18} />
                                </button>
                            </div>

                            {/* All companies chip */}
                            <div className="company-picker-all">
                                <button
                                    className={`chip chip-all ${isAllSelected ? 'chip-active' : ''}`}
                                    onClick={selectAll}
                                    id="picker-all-btn"
                                >
                                    ✦ All companies
                                </button>
                            </div>

                            {/* Company grid */}
                            {companiesLoading ? (
                                <div className="company-picker-grid">
                                    {[...Array(6)].map((_, i) => (
                                        <div key={i} className="skeleton" style={{ height: 52, borderRadius: 12 }} />
                                    ))}
                                </div>
                            ) : (
                                <div className="company-picker-grid">
                                    {companies.map(c => {
                                        const active = selectedSlugs.includes(c.slug)
                                        return (
                                            <button
                                                key={c.slug}
                                                id={`picker-${c.slug}`}
                                                className={`company-chip ${active ? 'company-chip-active' : ''}`}
                                                onClick={() => toggleSlug(c.slug)}
                                            >
                                                <span className="company-chip-name">{c.name}</span>
                                                <span
                                                    className="company-chip-badge"
                                                    style={{ background: ATS_COLORS[c.ats] || '#6366f1' }}
                                                >
                                                    {c.ats}
                                                </span>
                                            </button>
                                        )
                                    })}
                                </div>
                            )}

                            {/* Footer */}
                            <div className="modal-footer">
                                <span className="picker-selection-label">
                                    {isAllSelected
                                        ? `Running all ${companies.length} companies`
                                        : `${selectedSlugs.length} of ${companies.length} selected`}
                                </span>
                                <div className="modal-footer-actions">
                                    <button className="btn btn-ghost" onClick={() => setShowPicker(false)}>Cancel</button>
                                    <button
                                        className="btn btn-primary"
                                        onClick={handleRunPipeline}
                                        id="picker-run-btn"
                                    >
                                        <Play size={14} />
                                        Run{isAllSelected ? ' All' : ` (${selectedSlugs.length})`}
                                    </button>
                                </div>
                            </div>
                        </motion.div>
                    </motion.div>
                )}
            </AnimatePresence>

            {/* Stats */}
            {loading ? (
                <div className="section-grid grid-4">
                    {[...Array(4)].map((_, i) => (
                        <div key={i} className="skeleton" style={{ height: 90 }} />
                    ))}
                </div>
            ) : (
                <motion.div
                    variants={stagger.container}
                    initial="hidden"
                    animate="visible"
                    className="section-grid grid-4"
                >
                    <motion.div variants={stagger.item}>
                        <StatCard
                            icon={<Zap size={22} />}
                            label="Total Matches"
                            value={stats?.total_matches ?? 0}
                            color="var(--color-primary)"
                        />
                    </motion.div>
                    <motion.div variants={stagger.item}>
                        <StatCard
                            icon={<Briefcase size={22} />}
                            label="High Score (≥70%)"
                            value={stats?.high_score_matches ?? 0}
                            color="var(--color-success)"
                            subtitle="Strong matches"
                        />
                    </motion.div>
                    <motion.div variants={stagger.item}>
                        <StatCard
                            icon={<BookmarkCheck size={22} />}
                            label="Saved Jobs"
                            value={stats?.saved_jobs ?? 0}
                            color="var(--color-warning)"
                        />
                    </motion.div>
                    <motion.div variants={stagger.item}>
                        <StatCard
                            icon={<CheckCircle size={22} />}
                            label="Applied"
                            value={stats?.applied_jobs ?? 0}
                            color="var(--color-accent)"
                        />
                    </motion.div>
                </motion.div>
            )}

            {/* Chart + Last Run */}
            <div className="dashboard-mid">
                {/* Activity Chart */}
                <div className="card dashboard-chart-card">
                    <h2 className="section-title">Pipeline Activity</h2>
                    <ResponsiveContainer width="100%" height={200}>
                        <AreaChart data={chartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                            <defs>
                                <linearGradient id="gradJobs" x1="0" y1="0" x2="0" y2="1">
                                    <stop offset="5%" stopColor="#6366f1" stopOpacity={0.35} />
                                    <stop offset="95%" stopColor="#6366f1" stopOpacity={0} />
                                </linearGradient>
                                <linearGradient id="gradMatches" x1="0" y1="0" x2="0" y2="1">
                                    <stop offset="5%" stopColor="#22d3ee" stopOpacity={0.35} />
                                    <stop offset="95%" stopColor="#22d3ee" stopOpacity={0} />
                                </linearGradient>
                            </defs>
                            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                            <XAxis dataKey="name" tick={{ fill: '#64748b', fontSize: 12 }} axisLine={false} tickLine={false} />
                            <YAxis tick={{ fill: '#64748b', fontSize: 12 }} axisLine={false} tickLine={false} />
                            <Tooltip
                                contentStyle={{ background: '#111224', border: '1px solid rgba(99,102,241,0.25)', borderRadius: 10 }}
                                labelStyle={{ color: '#f1f5f9' }}
                                itemStyle={{ color: '#94a3b8' }}
                            />
                            <Area type="monotone" dataKey="jobs" stroke="#6366f1" strokeWidth={2} fill="url(#gradJobs)" name="Jobs Scraped" />
                            <Area type="monotone" dataKey="matches" stroke="#22d3ee" strokeWidth={2} fill="url(#gradMatches)" name="Matches Created" />
                        </AreaChart>
                    </ResponsiveContainer>
                </div>

                {/* Last Run Info */}
                <div className="card dashboard-lastrun-card">
                    <h2 className="section-title">Last Pipeline Run</h2>
                    {lastRun && lastRun.jobs_scraped !== undefined ? (
                        <div className="lastrun-stats">
                            <div className="lastrun-row">
                                <span>Jobs Scraped</span>
                                <span className="lastrun-val">{lastRun.jobs_scraped}</span>
                            </div>
                            <div className="lastrun-row">
                                <span>New Matches</span>
                                <span className="lastrun-val">{lastRun.matches_created}</span>
                            </div>
                            <div className="lastrun-row">
                                <span>Notifications Sent</span>
                                <span className="lastrun-val">{lastRun.notifications_sent}</span>
                            </div>
                            <div className="lastrun-row">
                                <span>Errors</span>
                                <span className={`lastrun-val ${lastRun.errors?.length ? 'text-error' : ''}`}>
                                    {lastRun.errors?.length ?? 0}
                                </span>
                            </div>
                            {lastRun.finished_at && (
                                <p className="lastrun-time">Finished: {new Date(lastRun.finished_at).toLocaleString()}</p>
                            )}
                        </div>
                    ) : (
                        <div className="lastrun-empty">
                            <AlertCircle size={28} className="text-muted" />
                            <p>No pipeline run yet.</p>
                            <button className="btn btn-secondary" onClick={openPicker}>
                                <Play size={14} /> Run now
                            </button>
                        </div>
                    )}
                </div>
            </div>

            {/* Top Matches */}
            <div>
                <div className="section-header">
                    <h2 className="section-title">Top Job Matches</h2>
                    <button className="btn btn-ghost" onClick={load} id="refresh-matches-btn">
                        <RefreshCw size={14} /> Refresh
                    </button>
                </div>
                {loading ? (
                    <div className="section-grid">
                        {[...Array(3)].map((_, i) => <div key={i} className="skeleton" style={{ height: 160 }} />)}
                    </div>
                ) : topMatches.length === 0 ? (
                    <div className="card empty-state">
                        <Briefcase size={40} className="text-muted" />
                        <p>No matches yet. Run the pipeline to get started!</p>
                    </div>
                ) : (
                    <motion.div
                        variants={stagger.container}
                        initial="hidden"
                        animate="visible"
                        className="section-grid"
                    >
                        {topMatches.map((m) => (
                            <motion.div key={m.id} variants={stagger.item}>
                                <JobCard match={m} onUpdate={load} />
                            </motion.div>
                        ))}
                    </motion.div>
                )}
            </div>
        </div>
    )
}
