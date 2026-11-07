import { useEffect, useRef, useState, type FormEvent } from 'react'
import { askQuestion, type Source } from '../api'

interface Message {
  id: number
  role: 'user' | 'assistant'
  text: string
  sources?: Source[]
  isError?: boolean
}

interface Props {
  hasReadyDocuments: boolean
}

let nextId = 1

export default function ChatPanel({ hasReadyDocuments }: Props) {
  const [messages, setMessages] = useState<Message[]>([])
  const [question, setQuestion] = useState('')
  const [asking, setAsking] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, asking])

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    const text = question.trim()
    if (!text || asking) return

    setMessages((prev) => [...prev, { id: nextId++, role: 'user', text }])
    setQuestion('')
    setAsking(true)
    try {
      const result = await askQuestion(text)
      setMessages((prev) => [
        ...prev,
        { id: nextId++, role: 'assistant', text: result.answer, sources: result.sources },
      ])
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        { id: nextId++, role: 'assistant', text: (err as Error).message, isError: true },
      ])
    } finally {
      setAsking(false)
    }
  }

  return (
    <main className="chat">
      <div className="messages">
        {messages.length === 0 && (
          <div className="empty-state">
            <h2>Ask about your documents</h2>
            <p className="muted">
              {hasReadyDocuments
                ? 'Answers are based only on the documents you have uploaded.'
                : 'Upload a PDF or TXT file to get started.'}
            </p>
          </div>
        )}

        {messages.map((m) => (
          <div key={m.id} className={`message message--${m.role}${m.isError ? ' message--error' : ''}`}>
            <div className="message__text">{m.text}</div>
            {m.sources && m.sources.length > 0 && (
              <details className="sources">
                <summary>
                  {m.sources.length} source{m.sources.length === 1 ? '' : 's'}
                </summary>
                <ol>
                  {m.sources.map((s) => (
                    <li key={s.chunk_id}>
                      <div className="source__title">
                        {s.document_name}, page {s.page_number}
                        <span className="muted"> · relevance {s.score.toFixed(2)}</span>
                      </div>
                      <p className="source__text">{s.text}</p>
                    </li>
                  ))}
                </ol>
              </details>
            )}
          </div>
        ))}

        {asking && <div className="message message--assistant message--pending">Thinking…</div>}
        <div ref={bottomRef} />
      </div>

      <form className="ask-form" onSubmit={handleSubmit}>
        <textarea
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) handleSubmit(e)
          }}
          placeholder="Ask a question… (Enter to send, Shift+Enter for a new line)"
          rows={2}
          maxLength={2000}
          disabled={asking}
        />
        <button type="submit" disabled={asking || !question.trim()}>
          Ask
        </button>
      </form>
    </main>
  )
}
