import axios from 'axios'
import toast from 'react-hot-toast'

const BASE_URL = import.meta.env.VITE_API_URL || ''
const API_KEY = import.meta.env.VITE_API_KEY || ''

// Fix #26: Default short timeout for normal requests.
// Long-running calls (pipeline sync) use their own timeout override.
const DEFAULT_TIMEOUT = 15_000   // 15 s — standard API calls
const UPLOAD_TIMEOUT = 60_000   // 60 s — resume file uploads
const PIPELINE_TIMEOUT = 120_000 // 2 min — sync pipeline trigger

const api = axios.create({
    baseURL: `${BASE_URL}/api`,
    timeout: DEFAULT_TIMEOUT,
    headers: {
        'Content-Type': 'application/json',
        ...(API_KEY && { 'X-API-Key': API_KEY }),
    },
})

// Response interceptor — unified error display
api.interceptors.response.use(
    (res) => res,
    (err) => {
        const msg =
            err.response?.data?.detail ||
            err.response?.data?.message ||
            err.message ||
            'An unexpected error occurred'
        if (err.response?.status !== 404) {
            toast.error(msg)
        }
        return Promise.reject(err)
    }
)

// ─── Resumes ────────────────────────────────────────────────
export const uploadResume = (file, onProgress) => {
    const formData = new FormData()
    formData.append('file', file)
    return api.post('/resumes/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
        timeout: UPLOAD_TIMEOUT, // Fix #26: longer timeout only for uploads
        onUploadProgress: (e) => onProgress && onProgress(Math.round((e.loaded / e.total) * 100)),
    })
}

export const listResumes = () => api.get('/resumes/')
export const getResume = (id) => api.get(`/resumes/${id}`)
export const activateResume = (id) => api.patch(`/resumes/${id}/activate`)
export const deleteResume = (id) => api.delete(`/resumes/${id}`)

// ─── Jobs ────────────────────────────────────────────────────
export const listJobs = (params = {}) => api.get('/jobs/', { params })
export const getJob = (id) => api.get(`/jobs/${id}`)
export const deactivateJob = (id) => api.patch(`/jobs/${id}/deactivate`)

// ─── Matches ─────────────────────────────────────────────────
// Supported params: min_score, saved_only, applied_only,
//                   experience_level (entry|mid|senior|lead|director),
//                   location (partial, case-insensitive), skip, limit
export const listMatches = (params = {}) => api.get('/matches/', { params })
export const getMatchStats = () => api.get('/matches/stats')
export const toggleSave = (id) => api.patch(`/matches/${id}/save`)
export const toggleApplied = (id) => api.patch(`/matches/${id}/apply`)

// ─── Pipeline ────────────────────────────────────────────────
// Fix #26: Use long timeout only for the synchronous pipeline run
// companySlugs: string[] | null — pass null/undefined to run all companies
export const triggerPipeline = (companySlugs = null) =>
    api.post(
        '/pipeline/run/sync',
        companySlugs ? { companies: companySlugs } : null,
        { timeout: PIPELINE_TIMEOUT }
    )
export const triggerPipelineAsync = (companySlugs = null) =>
    api.post('/pipeline/run', companySlugs ? { companies: companySlugs } : null)
export const getLastRun = () => api.get('/pipeline/last-run')
export const getPipelineHistory = () => api.get('/pipeline/history')
export const listCompanies = () => api.get('/pipeline/companies')

// ─── Notifications ───────────────────────────────────────────
export const getNotificationLogs = () => api.get('/notifications/logs')
export const triggerNotifications = () => api.post('/notifications/trigger')

// ─── Health ──────────────────────────────────────────────────
export const getHealth = () => api.get('/health')

export default api
