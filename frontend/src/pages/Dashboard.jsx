import React, { useCallback, useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import {
    Zap, Briefcase, BookmarkCheck, CheckCircle,
    Play, RefreshCw, AlertCircle,
} from 'lucide-react'
import {
    AreaChart, Area, XAxis, YAxis, CartesianGrid,
    Tooltip, ResponsiveContainer,
} from 'recharts'
import StatCard from '../components/StatCard'
import JobCard from '../components/JobCard'
import { getMatchStats, listMatches, triggerPipeline, getLastRun } from '../utils/api'
import toast from 'react-hot-toast'
import './Dashboard.css'

const stagger = {
    container: { hidden: {}, visible: { transition: { staggerChildren: 0.08 } } },
    item: { hidden: { opacity: 0, y: 20 }, visible: { opacity: 1, y: 0 } },
}

export default function Dashboard() {
    const [stats, setStats] = useState(null)
    const [topMatches, setTopMatches] = useState([])
    const [lastRun, setLastRun] = useState(null)
    const [running, setRunning] = useState(false)
    const [loading, setLoading] = useState(true)

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

    const handleRunPipeline = async () => {
        setRunning(true)
        toast.loading('Running pipeline…', { id: 'pipeline' })
        try {
            const res = await triggerPipeline()
            toast.success(
                `Pipeline done! ${res.data.jobs_scraped} jobs scraped, ${res.data.matches_created} new matches.`,
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
                    onClick={handleRunPipeline}
                    disabled={running}
                    id="run-pipeline-btn"
                >
                    {running
                        ? <><div className="spinner" />Running…</>
                        : <><Play size={16} />Run Pipeline</>
                    }
                </button>
            </div>

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
                            <button className="btn btn-secondary" onClick={handleRunPipeline}>
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
