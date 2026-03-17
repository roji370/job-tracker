import React, { useCallback, useEffect, useState } from 'react'
import { Bell, MessageSquare, Mail, CheckCircle, XCircle, RefreshCw, Send } from 'lucide-react'
import { getNotificationLogs, triggerNotifications } from '../utils/api'
import toast from 'react-hot-toast'
import './Notifications.css'

const CHANNEL_ICON = {
    whatsapp: <MessageSquare size={15} />,
    email: <Mail size={15} />,
}

const STATUS_BADGE = {
    sent: <span className="badge badge-success"><CheckCircle size={10} /> Sent</span>,
    failed: <span className="badge badge-error"><XCircle size={10} /> Failed</span>,
    error: <span className="badge badge-error"><XCircle size={10} /> Error</span>,
    pending: <span className="badge badge-warning">Pending</span>,
    skipped: <span className="badge badge-muted">Skipped</span>,
}

export default function Notifications() {
    const [logs, setLogs] = useState([])
    const [loading, setLoading] = useState(true)
    const [triggering, setTriggering] = useState(false)

    const load = useCallback(async () => {
        setLoading(true)
        try {
            const res = await getNotificationLogs()
            setLogs(res.data)
        } finally {
            setLoading(false)
        }
    }, [])

    useEffect(() => { load() }, [load])

    const handleTrigger = async () => {
        setTriggering(true)
        toast.loading('Sending notifications…', { id: 'notif' })
        try {
            const res = await triggerNotifications()
            const d = res.data
            toast.success(
                `Notified ${d.matches_notified} match(es). WhatsApp: ${d.whatsapp?.status}, Email: ${d.email?.status}`,
                { id: 'notif', duration: 6000 }
            )
            load()
        } catch {
            toast.error('Failed to send notifications.', { id: 'notif' })
        } finally {
            setTriggering(false)
        }
    }

    return (
        <div className="page">
            <div className="page-header notif-header">
                <div>
                    <h1><span className="gradient-text">Notification</span> History</h1>
                    <p>WhatsApp &amp; email alerts for high-score job matches</p>
                </div>
                <div style={{ display: 'flex', gap: '0.75rem' }}>
                    <button className="btn btn-ghost" onClick={load} id="notif-refresh-btn">
                        <RefreshCw size={14} /> Refresh
                    </button>
                    <button
                        className="btn btn-primary"
                        onClick={handleTrigger}
                        disabled={triggering}
                        id="trigger-notifications-btn"
                    >
                        {triggering ? <><div className="spinner" />Sending…</> : <><Send size={15} />Send Now</>}
                    </button>
                </div>
            </div>

            {/* Info banner */}
            <div className="card notif-info">
                <Bell size={18} style={{ color: 'var(--color-primary-light)' }} />
                <p>
                    Notifications are sent automatically every <strong>6 hours</strong> for matches ≥ 70%  score.
                    You can also trigger them manually above.
                </p>
            </div>

            {/* Logs table */}
            {loading ? (
                <div className="section-grid">
                    {[...Array(4)].map((_, i) => <div key={i} className="skeleton" style={{ height: 60 }} />)}
                </div>
            ) : logs.length === 0 ? (
                <div className="card empty-state">
                    <Bell size={36} />
                    <p>No notifications sent yet. Run the pipeline or click "Send Now".</p>
                </div>
            ) : (
                <div className="card notif-table-card">
                    <table className="notif-table">
                        <thead>
                            <tr>
                                <th>Channel</th>
                                <th>Recipient</th>
                                <th>Subject</th>
                                <th>Status</th>
                                <th>Error</th>
                                <th>Time</th>
                            </tr>
                        </thead>
                        <tbody>
                            {logs.map((log) => (
                                <tr key={log.id}>
                                    <td>
                                        <span className="channel-badge">
                                            {CHANNEL_ICON[log.channel] || <Bell size={14} />}
                                            {log.channel}
                                        </span>
                                    </td>
                                    <td className="notif-recipient">{log.recipient}</td>
                                    <td className="notif-subject">{log.subject || '—'}</td>
                                    <td>{STATUS_BADGE[log.status] || <span className="badge badge-muted">{log.status}</span>}</td>
                                    <td className="notif-error">{log.error_message || '—'}</td>
                                    <td className="notif-time">{new Date(log.created_at).toLocaleString()}</td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            )}
        </div>
    )
}
