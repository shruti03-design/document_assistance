import { useRef, useState } from 'react'
import { uploadDocument, type DocumentInfo } from '../api'

const ACCEPTED = '.pdf,.txt'

interface Props {
  documents: DocumentInfo[]
  loadError: string | null
  onUploaded: (document: DocumentInfo) => void
}

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

const STATUS_LABEL: Record<DocumentInfo['status'], string> = {
  uploaded: 'Queued',
  processing: 'Indexing…',
  ready: 'Ready',
  failed: 'Failed',
}

export default function DocumentPanel({ documents, loadError, onUploaded }: Props) {
  const inputRef = useRef<HTMLInputElement>(null)
  const [uploading, setUploading] = useState(false)
  const [uploadError, setUploadError] = useState<string | null>(null)
  const [dragOver, setDragOver] = useState(false)

  async function handleFiles(files: FileList | null) {
    if (!files || files.length === 0) return
    setUploading(true)
    setUploadError(null)
    try {
      for (const file of Array.from(files)) {
        onUploaded(await uploadDocument(file))
      }
    } catch (err) {
      setUploadError((err as Error).message)
    } finally {
      setUploading(false)
      if (inputRef.current) inputRef.current.value = ''
    }
  }

  return (
    <aside className="documents">
      <h2>Documents</h2>

      <div
        className={`dropzone${dragOver ? ' dropzone--active' : ''}`}
        role="button"
        tabIndex={0}
        onClick={() => inputRef.current?.click()}
        onKeyDown={(e) => (e.key === 'Enter' || e.key === ' ') && inputRef.current?.click()}
        onDragOver={(e) => {
          e.preventDefault()
          setDragOver(true)
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={(e) => {
          e.preventDefault()
          setDragOver(false)
          handleFiles(e.dataTransfer.files)
        }}
      >
        <input
          ref={inputRef}
          type="file"
          accept={ACCEPTED}
          multiple
          hidden
          onChange={(e) => handleFiles(e.target.files)}
        />
        {uploading ? 'Uploading…' : 'Drop PDF or TXT files here, or click to choose'}
      </div>

      {uploadError && <p className="error">{uploadError}</p>}
      {loadError && <p className="error">{loadError}</p>}

      {documents.length === 0 && !loadError ? (
        <p className="muted">No documents yet.</p>
      ) : (
        <ul className="document-list">
          {documents.map((doc) => (
            <li key={doc.id} className="document">
              <div className="document__name" title={doc.original_name}>
                {doc.original_name}
              </div>
              <div className="document__meta">
                <span className={`badge badge--${doc.status}`}>{STATUS_LABEL[doc.status]}</span>
                <span>{formatSize(doc.size_bytes)}</span>
                {doc.page_count !== null && (
                  <span>
                    {doc.page_count} page{doc.page_count === 1 ? '' : 's'}
                  </span>
                )}
              </div>
              {doc.status === 'failed' && doc.error && (
                <div className="document__error">{doc.error}</div>
              )}
            </li>
          ))}
        </ul>
      )}
    </aside>
  )
}
