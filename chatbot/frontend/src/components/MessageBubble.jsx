import { useState } from 'react'

const CONFIDENCE_BADGE = {
  high: { icon: '🟢', label: 'High confidence' },
  medium: { icon: '🟡', label: 'Medium confidence' },
  low: { icon: '🔴', label: 'Low confidence' },
}

function SourceCitations({ sources }) {
  const [open, setOpen] = useState(false)

  if (!sources || sources.length === 0) return null

  return (
    <div className="mt-2 border-t border-slate-200 pt-2">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="text-xs font-medium text-slate-500 hover:text-slate-700"
      >
        {open ? '▾' : '▸'} Sources ({sources.length})
      </button>
      {open && (
        <ul className="mt-1 space-y-1">
          {sources.map((source, idx) => (
            <li key={idx} className="text-xs text-slate-500">
              {source.scheme_name}
              {source.section ? ` › ${source.section}` : ''}
              {source.source_file ? ` (${source.source_file})` : ''}
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

export default function MessageBubble({ role, text, confidence, sources }) {
  const isUser = role === 'user'
  const badge = confidence ? CONFIDENCE_BADGE[confidence] : null

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
      <div
        className={`max-w-[80%] rounded-lg px-4 py-2 shadow-sm sm:max-w-[70%] ${
          isUser
            ? 'bg-blue-600 text-white'
            : 'border border-slate-200 bg-white text-slate-800'
        }`}
      >
        <p className="whitespace-pre-wrap text-sm leading-relaxed">{text}</p>
        {!isUser && badge && (
          <div className="mt-1 flex items-center gap-1 text-xs text-slate-500">
            <span>{badge.icon}</span>
            <span>{badge.label}</span>
          </div>
        )}
        {!isUser && <SourceCitations sources={sources} />}
      </div>
    </div>
  )
}
