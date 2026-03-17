import React from 'react'
import { Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import { Home, SearchX } from 'lucide-react'

export default function NotFound() {
    return (
        <motion.div
            className="not-found-page"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4 }}
        >
            <div className="not-found-inner">
                <div className="not-found-icon">
                    <SearchX size={64} strokeWidth={1.25} />
                </div>
                <h1 className="not-found-code">404</h1>
                <h2 className="not-found-title">Page Not Found</h2>
                <p className="not-found-desc">
                    The page you're looking for doesn't exist or has been moved.
                </p>
                <Link to="/" className="not-found-btn">
                    <Home size={18} />
                    Back to Dashboard
                </Link>
            </div>

            <style>{`
                .not-found-page {
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    min-height: 80vh;
                    text-align: center;
                }
                .not-found-inner {
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    gap: 1rem;
                    padding: 2rem;
                }
                .not-found-icon {
                    color: var(--color-primary, #6366f1);
                    opacity: 0.7;
                    margin-bottom: 0.5rem;
                }
                .not-found-code {
                    font-size: 6rem;
                    font-weight: 800;
                    line-height: 1;
                    background: linear-gradient(135deg, #6366f1, #8b5cf6);
                    -webkit-background-clip: text;
                    -webkit-text-fill-color: transparent;
                    background-clip: text;
                    margin: 0;
                }
                .not-found-title {
                    font-size: 1.5rem;
                    font-weight: 600;
                    color: var(--color-text, #f1f5f9);
                    margin: 0;
                }
                .not-found-desc {
                    color: var(--color-muted, #94a3b8);
                    max-width: 340px;
                    margin: 0;
                }
                .not-found-btn {
                    display: inline-flex;
                    align-items: center;
                    gap: 0.5rem;
                    margin-top: 0.5rem;
                    padding: 0.625rem 1.25rem;
                    background: linear-gradient(135deg, #6366f1, #8b5cf6);
                    color: #fff;
                    border-radius: 10px;
                    text-decoration: none;
                    font-weight: 500;
                    font-size: 0.9rem;
                    transition: opacity 0.2s;
                }
                .not-found-btn:hover { opacity: 0.85; }
            `}</style>
        </motion.div>
    )
}
