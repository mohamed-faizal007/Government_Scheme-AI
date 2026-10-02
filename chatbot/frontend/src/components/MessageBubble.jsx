import { useState } from 'react'
import FeedbackButtons from './FeedbackButtons'

const CONFIDENCE_BADGE = {
  high: { label: '✓ Verified', className: 'bg-success-light text-success' },
  medium: { label: '~ Inferred', className: 'bg-amber-light text-amber' },
  low: { label: '? Uncertain', className: 'bg-[#EDF2F7] text-text-secondary' },
}

function formatSyncDate(iso) {
  const date = iso ? new Date(iso) : null
  if (!date || Number.isNaN(date.getTime())) return null
  return date.toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' })
}

function SourceCitations({ sources }) {
  const [open, setOpen] = useState(false)

  if (!sources || sources.length === 0) return null

  const latestSync = sources
    .map((s) => s.last_synced)
    .filter(Boolean)
    .sort()
    .pop()
  const latestSyncLabel = formatSyncDate(latestSync)

  return (
    <div className="mt-2 border-t border-border pt-2">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="text-xs font-medium text-text-secondary hover:text-primary"
      >
        {open ? '▾' : '▸'} References ({sources.length})
      </button>
      {open && (
        <ol className="mt-1.5 list-decimal space-y-1 pl-4">
          {sources.map((source, idx) => (
            <li key={idx} className="text-xs text-text-secondary">
              <span className="font-semibold text-text-primary">{source.scheme_name}</span>
              {source.section ? <span> — {source.section}</span> : null}
              {source.data_as_of ? (
                <div className="text-[11px] text-gray-400">{source.data_as_of}</div>
              ) : null}
            </li>
          ))}
        </ol>
      )}
      {open && latestSyncLabel && (
        <div className="mt-1.5 text-[11px] text-gray-400">🔄 Last synced: {latestSyncLabel}</div>
      )}
    </div>
  )
}

export default function MessageBubble({ role, text, confidence, sources, sessionId, messageIndex, query, intent }) {
  const isUser = role === 'user'
  const badge = confidence ? CONFIDENCE_BADGE[confidence] : null

  return (
    <div className={`flex items-start gap-2 ${isUser ? 'justify-end' : 'justify-start'}`}>
      {!isUser && (
        <div className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary-light text-base">
          🏛️
        </div>
      )}
      <div
        className={`max-w-[80%] px-4 py-2.5 sm:max-w-[70%] ${
          isUser
            ? 'rounded-2xl bg-primary text-white shadow-card'
            : 'rounded-2xl border-l-[3px] border-accent bg-surface text-text-primary shadow-card'
        }`}
      >
        <p className="whitespace-pre-wrap text-sm leading-relaxed">{text}</p>
        {!isUser && badge && (
          <div className="mt-2">
            <span className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-medium ${badge.className}`}>
              {badge.label}
            </span>
          </div>
        )}
        {!isUser && <SourceCitations sources={sources} />}
        {!isUser && (
          <FeedbackButtons sessionId={sessionId} messageIndex={messageIndex} query={query} intent={intent} />
        )}
      </div>
    </div>
  )
}
