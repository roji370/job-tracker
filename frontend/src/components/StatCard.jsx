import React from 'react'
import './StatCard.css'

/**
 * A stat summary card.
 * Props: icon (ReactNode), label, value, color, subtitle
 */
export default function StatCard({ icon, label, value, color = 'var(--color-primary)', subtitle }) {
    return (
        <div className="stat-card">
            <div className="stat-card-icon" style={{ background: `${color}22`, color }}>
                {icon}
            </div>
            <div className="stat-card-content">
                <div className="stat-card-value">{value ?? '—'}</div>
                <div className="stat-card-label">{label}</div>
                {subtitle && <div className="stat-card-subtitle">{subtitle}</div>}
            </div>
        </div>
    )
}
