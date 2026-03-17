import React from 'react'
import { NavLink } from 'react-router-dom'
import {
    LayoutDashboard,
    Briefcase,
    FileText,
    Bell,
    Zap,
    ChevronRight,
} from 'lucide-react'
import './Sidebar.css'

const NAV = [
    { to: '/', icon: LayoutDashboard, label: 'Dashboard' },
    { to: '/matches', icon: Zap, label: 'Matches' },
    { to: '/jobs', icon: Briefcase, label: 'Jobs' },
    { to: '/resume', icon: FileText, label: 'Resume' },
    { to: '/notifications', icon: Bell, label: 'Notifications' },
]

export default function Sidebar() {
    return (
        <aside className="sidebar">
            <div className="sidebar-logo">
                <div className="sidebar-logo-icon">
                    <Zap size={22} />
                </div>
                <span className="sidebar-logo-text">JobTracker</span>
            </div>

            <nav className="sidebar-nav">
                {NAV.map(({ to, icon: Icon, label }) => (
                    <NavLink
                        key={to}
                        to={to}
                        end={to === '/'}
                        className={({ isActive }) =>
                            ['sidebar-link', isActive ? 'active' : ''].filter(Boolean).join(' ')
                        }
                    >
                        <Icon size={18} className="sidebar-link-icon" />
                        <span>{label}</span>
                        <ChevronRight size={14} className="sidebar-link-chevron" />
                    </NavLink>
                ))}
            </nav>

            <div className="sidebar-footer">
                <div className="sidebar-footer-badge">
                    <span className="pulse-dot" />
                    <span>Scheduler Active</span>
                </div>
            </div>
        </aside>
    )
}
