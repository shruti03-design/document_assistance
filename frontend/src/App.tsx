import { useCallback, useEffect, useState } from 'react'
import { listDocuments, type DocumentInfo } from './api'
import ChatPanel from './components/ChatPanel'
import DocumentPanel from './components/DocumentPanel'

const POLL_INTERVAL_MS = 2000

export default function App() {
  const [documents, setDocuments] = useState<DocumentInfo[]>([])
  const [loadError, setLoadError] = useState<string | null>(null)

  const refresh = useCallback(async () => {
    try {
      setDocuments(await listDocuments())
      setLoadError(null)
    } catch (err) {
      setLoadError((err as Error).message)
    }
  }, [])

  // Initial load
  useEffect(() => {
    let cancelled = false
    listDocuments()
      .then((docs) => !cancelled && setDocuments(docs))
      .catch((err: Error) => !cancelled && setLoadError(err.message))
    return () => {
      cancelled = true
    }
  }, [])

  // Indexing runs in the background on the server, so poll until every document settles
  const indexing = documents.some((d) => d.status === 'uploaded' || d.status === 'processing')
  useEffect(() => {
    if (!indexing) return
    const timer = setInterval(refresh, POLL_INTERVAL_MS)
    return () => clearInterval(timer)
  }, [indexing, refresh])

  function handleUploaded(document: DocumentInfo) {
    setDocuments((prev) => [document, ...prev.filter((d) => d.id !== document.id)])
  }

  return (
    <div className="app">
      <header className="header">
        <h1>Document Assistant</h1>
      </header>
      <div className="layout">
        <DocumentPanel documents={documents} loadError={loadError} onUploaded={handleUploaded} />
        <ChatPanel hasReadyDocuments={documents.some((d) => d.status === 'ready')} />
      </div>
    </div>
  )
}
