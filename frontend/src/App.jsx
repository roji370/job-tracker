import React from 'react'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { Toaster } from 'react-hot-toast'
import Sidebar from './components/Sidebar'
import Dashboard from './pages/Dashboard'
import Matches from './pages/Matches'
import Jobs from './pages/Jobs'
import Resume from './pages/Resume'
import Notifications from './pages/Notifications'
import NotFound from './pages/NotFound'
import './App.css'

export default function App() {
    return (
        <BrowserRouter>
            <div className="app-layout">
                <Sidebar />
                <main className="app-main">
                    <div className="app-content">
                        <Routes>
                            <Route path="/" element={<Dashboard />} />
                            <Route path="/matches" element={<Matches />} />
                            <Route path="/jobs" element={<Jobs />} />
                            <Route path="/resume" element={<Resume />} />
                            <Route path="/notifications" element={<Notifications />} />
                            {/* Fix #27: Catch-all 404 route */}
                            <Route path="*" element={<NotFound />} />
                        </Routes>
                    </div>
                </main>
            </div>
            <Toaster
                position="top-right"
                toastOptions={{
                    style: {
                        background: '#111224',
                        color: '#f1f5f9',
                        border: '1px solid rgba(99,102,241,0.3)',
                        borderRadius: '10px',
                        fontSize: '0.875rem',
                    },
                    success: { iconTheme: { primary: '#22c55e', secondary: '#111224' } },
                    error: { iconTheme: { primary: '#ef4444', secondary: '#111224' } },
                }}
            />
        </BrowserRouter>
    )
}
