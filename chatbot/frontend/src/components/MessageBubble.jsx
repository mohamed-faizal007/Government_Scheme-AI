import { useState } from 'react'

const CONFIDENCE_BADGE = {
  high: { label: '✓ Verified', className: 'bg-success-light text-success' },
  medium: { label: '~ Inferred', className: 'bg-amber-light text-amber' },
  low: { label: '? Uncertain', className: 'bg-[#EDF2F7] text-text-secondary' },
}

function SourceCitations({ sources }) {
  const [open, setOpen] = useState(false)

  if (!sources || sources.length === 0) return null

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
            </li>
          ))}
        </ol>
      )}
    </div>
  )
}

export default function MessageBubble({ role, text, confidence, sources }) {
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
      </div>
    </div>
  )
}
