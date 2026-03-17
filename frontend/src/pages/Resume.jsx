import React, { useCallback, useEffect, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { FileText, Trash2, CheckCircle, Upload, Tag } from 'lucide-react'
import UploadZone from '../components/UploadZone'
import { listResumes, uploadResume, activateResume, deleteResume } from '../utils/api'
import toast from 'react-hot-toast'
import './Resume.css'

export default function Resume() {
    const [resumes, setResumes] = useState([])
    const [uploading, setUploading] = useState(false)
    const [progress, setProgress] = useState(0)
    const [loading, setLoading] = useState(true)

    const load = useCallback(async () => {
        setLoading(true)
        try {
            const res = await listResumes()
            setResumes(res.data)
        } finally {
            setLoading(false)
        }
    }, [])

    useEffect(() => { load() }, [load])

    const handleFile = async (file) => {
        setUploading(true)
        setProgress(0)
        try {
            await uploadResume(file, setProgress)
            toast.success('Resume uploaded and parsed successfully!')
            load()
        } catch {
            // toasted by interceptor
        } finally {
            setUploading(false)
            setProgress(0)
        }
    }

    const handleActivate = async (id) => {
        try {
            await activateResume(id)
            toast.success('Resume set as active.')
            load()
        } catch { }
    }

    const handleDelete = async (id) => {
        if (!window.confirm('Delete this resume?')) return
        try {
            await deleteResume(id)
            toast.success('Resume deleted.')
            load()
        } catch { }
    }

    return (
        <div className="page">
            <div className="page-header">
                <h1>Your <span className="gradient-text">Resume</span></h1>
                <p>Upload your resume — AI will extract skills and match you to jobs</p>
            </div>

            {/* Upload Zone */}
            <div className="card resume-upload-card">
                <h2 className="section-label"><Upload size={16} /> Upload Resume</h2>
                <UploadZone onFile={handleFile} uploading={uploading} progress={progress} />
                <p className="resume-hint">
                    The active resume is used for all AI matching. Upload a new one to switch.
                </p>
            </div>

            {/* Resume List */}
            <div>
                <h2 className="section-label" style={{ marginBottom: '1rem' }}>
                    <FileText size={16} /> Uploaded Resumes
                </h2>

                {loading ? (
                    <div className="section-grid">
                        {[...Array(2)].map((_, i) => <div key={i} className="skeleton" style={{ height: 100 }} />)}
                    </div>
                ) : resumes.length === 0 ? (
                    <div className="card empty-state">
                        <FileText size={36} />
                        <p>No resumes uploaded yet. Drop one above to get started.</p>
                    </div>
                ) : (
                    <AnimatePresence>
                        <div className="section-grid">
                            {resumes.map((r) => (
                                <motion.div
                                    key={r.id}
                                    layout
                                    initial={{ opacity: 0, y: 12 }}
                                    animate={{ opacity: 1, y: 0 }}
                                    exit={{ opacity: 0 }}
                                    className={`card resume-card ${r.is_active ? 'resume-card--active' : ''}`}
                                >
                                    <div className="resume-card-header">
                                        <div className="resume-card-icon">
                                            <FileText size={20} />
                                        </div>
                                        <div className="resume-card-info">
                                            <div className="resume-card-name">{r.original_filename}</div>
                                            <div className="resume-card-date">
                                                {r.is_active
                                                    ? <span className="badge badge-success"><CheckCircle size={10} /> Active</span>
                                                    : <span className="badge badge-muted">Inactive</span>
                                                }
                                            </div>
                                        </div>
                                        <div className="resume-card-actions">
                                            {!r.is_active && (
                                                <button
                                                    className="btn btn-secondary"
                                                    onClick={() => handleActivate(r.id)}
                                                    id={`activate-${r.id}`}
                                                >
                                                    Set Active
                                                </button>
                                            )}
                                            <button
                                                className="btn btn-danger"
                                                onClick={() => handleDelete(r.id)}
                                                id={`delete-resume-${r.id}`}
                                            >
                                                <Trash2 size={14} />
                                            </button>
                                        </div>
                                    </div>

                                    {/* Skills */}
                                    {r.skills?.length > 0 && (
                                        <div className="resume-skills">
                                            <span className="skills-label"><Tag size={12} /> Skills detected:</span>
                                            <div className="skills-cloud">
                                                {r.skills.map((s) => (
                                                    <span key={s} className="skill-chip">{s}</span>
                                                ))}
                                            </div>
                                        </div>
                                    )}
                                </motion.div>
                            ))}
                        </div>
                    </AnimatePresence>
                )}
            </div>
        </div>
    )
}
