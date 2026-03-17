import React, { useCallback } from 'react'
import { useDropzone } from 'react-dropzone'
import { UploadCloud, FileText, X } from 'lucide-react'
import './UploadZone.css'

/**
 * Drag-and-drop file upload zone.
 * Props:
 *   onFile(file) — called with the File object
 *   accept       — mime type object (default: PDF/DOCX/TXT)
 *   uploading    — show loading state
 *   progress     — 0-100 upload progress
 */
export default function UploadZone({ onFile, uploading = false, progress = 0 }) {
    const onDrop = useCallback(
        (accepted) => { if (accepted.length) onFile(accepted[0]) },
        [onFile]
    )

    const { getRootProps, getInputProps, isDragActive, acceptedFiles } = useDropzone({
        onDrop,
        multiple: false,
        accept: {
            'application/pdf': ['.pdf'],
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
            'text/plain': ['.txt'],
        },
        disabled: uploading,
    })

    const file = acceptedFiles[0]

    return (
        <div className={`upload-zone ${isDragActive ? 'drag-active' : ''} ${uploading ? 'uploading' : ''}`} {...getRootProps()}>
            <input {...getInputProps()} id="resume-upload-input" />

            {uploading ? (
                <div className="upload-progress">
                    <div className="upload-spinner" />
                    <p className="upload-progress-label">Uploading & parsing… {progress}%</p>
                    <div className="upload-progress-bar">
                        <div className="upload-progress-fill" style={{ width: `${progress}%` }} />
                    </div>
                </div>
            ) : file ? (
                <div className="upload-file-chosen">
                    <FileText size={32} className="upload-icon-file" />
                    <p className="upload-filename">{file.name}</p>
                    <p className="upload-filesize">{(file.size / 1024).toFixed(1)} KB — ready to upload</p>
                </div>
            ) : (
                <div className="upload-idle">
                    <div className={`upload-icon-wrap ${isDragActive ? 'bouncing' : ''}`}>
                        <UploadCloud size={36} />
                    </div>
                    <p className="upload-main-text">
                        {isDragActive ? 'Drop your resume here' : 'Drag & drop your resume'}
                    </p>
                    <p className="upload-sub-text">
                        or <span className="upload-browse">browse files</span> — PDF, DOCX, TXT (max 10 MB)
                    </p>
                </div>
            )}
        </div>
    )
}
