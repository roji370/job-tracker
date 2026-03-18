import React, { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
    MapPin, Building2, Clock, ExternalLink,
    Bookmark, BookmarkCheck, CheckCircle, Circle,
    ChevronDown, ChevronUp,
} from 'lucide-react'
import { scoreBadgeClass, truncate, formatDate } from '../hooks/useFetch'
import { toggleSave, toggleApplied } from '../utils/api'
import toast from 'react-hot-toast'
import './JobCard.css'

const BREAKDOWN_DIMS = [
    { key: 'role', label: 'Role' },
    { key: 'skills', label: 'Skills' },
    { key: 'experience', label: 'Experience' },
    { key: 'location', label: 'Location' },
    { key: 'tech_stack', label: 'Tech Stack' },
]

export default function JobCard({ match, onUpdate }) {
    const [expanded, setExpanded] = useState(false)
    const [saving, setSaving] = useState(false)
    const [applying, setApplying] = useState(false)
    const { job, match_score, explanation, score_breakdown, is_saved, is_applied, id } = match

    // Normalise explanation: API may return string (legacy) or string[]
    const explanationLines = Array.isArray(explanation)
        ? explanation
        : (explanation ? [explanation] : [])

    const handleSave = async (e) => {
        e.stopPropagation()
        setSaving(true)
        try {
            await toggleSave(id)
            toast.success(is_saved ? 'Removed from saved' : 'Job saved!')
            onUpdate && onUpdate()
        } finally {
            setSaving(false)
        }
    }

    const handleApply = async (e) => {
        e.stopPropagation()
        setApplying(true)
        try {
            await toggleApplied(id)
            toast.success(is_applied ? 'Marked as not applied' : '✅ Marked as applied!')
            onUpdate && onUpdate()
        } finally {
            setApplying(false)
        }
    }

    const score = Math.round(match_score)

    return (
        <motion.div
            layout
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -16 }}
            className={`job-card ${is_applied ? 'job-card--applied' : ''}`}
        >
            {/* Score bar */}
            <div className="job-card-score-bar">
                <div
                    className="job-card-score-fill"
                    style={{ width: `${score}%`, background: scoreGradient(score) }}
                />
            </div>

            <div className="job-card-inner">
                {/* Header */}
                <div className="job-card-header">
                    <div className="job-card-logo">
                        {job.company?.charAt(0) || 'A'}
                    </div>
                    <div className="job-card-meta">
                        <h3 className="job-card-title">{job.title}</h3>
                        <div className="job-card-tags">
                            {job.company && (
                                <span className="tag"><Building2 size={12} /> {job.company}</span>
                            )}
                            {job.location && (
                                <span className="tag"><MapPin size={12} /> {job.location}</span>
                            )}
                            {job.employment_type && (
                                <span className="tag"><Clock size={12} /> {job.employment_type}</span>
                            )}
                        </div>
                    </div>
                    <div className="job-card-score-badge">
                        <span className={`badge ${scoreBadgeClass(score)}`}>{score}%</span>
                    </div>
                </div>

                {/* Explanation bullets */}
                {explanationLines.length > 0 && (
                    <ul className="job-card-explanation">
                        {explanationLines.map((line, i) => (
                            <li key={i}>{line}</li>
                        ))}
                    </ul>
                )}

                {/* Score breakdown mini-bars (only when real data is present) */}
                {score_breakdown && Object.keys(score_breakdown).length > 0 && (
                    <div className="breakdown-grid">
                        {BREAKDOWN_DIMS.map(({ key, label }) => (
                            <div key={key} className="breakdown-dim">
                                <div className="breakdown-label">
                                    <span>{label}</span>
                                    <span className="breakdown-val">
                                        {Math.round(score_breakdown[key] ?? 0)}
                                    </span>
                                </div>
                                <div className="breakdown-bar-bg">
                                    <div
                                        className="breakdown-bar-fill"
                                        style={{
                                            width: `${score_breakdown[key] ?? 0}%`,
                                            background: scoreGradient(score_breakdown[key] ?? 0),
                                        }}
                                    />
                                </div>
                            </div>
                        ))}
                    </div>
                )}

                {/* Expandable description */}
                <AnimatePresence>
                    {expanded && (
                        <motion.div
                            initial={{ height: 0, opacity: 0 }}
                            animate={{ height: 'auto', opacity: 1 }}
                            exit={{ height: 0, opacity: 0 }}
                            transition={{ duration: 0.25 }}
                            className="job-card-details"
                        >
                            {job.description && (
                                <div className="job-detail-section">
                                    <h4>About the Role</h4>
                                    <p>{job.description}</p>
                                </div>
                            )}
                            {job.requirements && (
                                <div className="job-detail-section">
                                    <h4>Requirements</h4>
                                    <p>{job.requirements}</p>
                                </div>
                            )}
                            {job.posted_date && (
                                <p className="job-card-posted">Posted: {job.posted_date}</p>
                            )}
                        </motion.div>
                    )}
                </AnimatePresence>

                {/* Actions */}
                <div className="job-card-actions">
                    <button className="btn btn-ghost" onClick={() => setExpanded(!expanded)}>
                        {expanded ? <ChevronUp size={15} /> : <ChevronDown size={15} />}
                        {expanded ? 'Less' : 'More'}
                    </button>

                    <div className="job-card-actions-right">
                        <button
                            className={`btn ${is_saved ? 'btn-primary' : 'btn-secondary'}`}
                            onClick={handleSave}
                            disabled={saving}
                            id={`save-${id}`}
                        >
                            {is_saved ? <BookmarkCheck size={15} /> : <Bookmark size={15} />}
                            {is_saved ? 'Saved' : 'Save'}
                        </button>

                        <button
                            className={`btn ${is_applied ? 'btn-secondary' : 'btn-primary'}`}
                            onClick={handleApply}
                            disabled={applying}
                            id={`apply-${id}`}
                        >
                            {is_applied ? <CheckCircle size={15} /> : <Circle size={15} />}
                            {is_applied ? 'Applied' : 'Apply'}
                        </button>

                        {job.url && (
                            <a
                                href={job.url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="btn btn-secondary"
                                id={`view-${id}`}
                            >
                                <ExternalLink size={15} />
                                View
                            </a>
                        )}
                    </div>
                </div>
            </div>
        </motion.div>
    )
}

function scoreGradient(score) {
    if (score >= 70) return 'linear-gradient(90deg, #22c55e, #16a34a)'
    if (score >= 50) return 'linear-gradient(90deg, #f59e0b, #d97706)'
    return 'linear-gradient(90deg, #ef4444, #dc2626)'
}
