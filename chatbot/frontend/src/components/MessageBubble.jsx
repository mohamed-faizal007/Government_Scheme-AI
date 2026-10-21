import { useState } from 'react'
import { renderMarkdown } from '../utils/markdown'
import { sectionLabel } from '../utils/sections'
import FeedbackButtons from './FeedbackButtons'
import Icon, { LogoMark } from './Icons'

export const PORTAL_URL = 'https://www.myscheme.gov.in'

const CONFIDENCE = {
  high: {
    label: 'Directly stated',
    tone: 'bg-success-soft text-success',
    hint: 'The answer is stated directly in the scheme text we retrieved.',
  },
  medium: {
    label: 'Inferred',
    tone: 'bg-warning-soft text-warning',
    hint: 'The answer needed combining information across the retrieved scheme text. Check the cited scheme before acting on it.',
  },
  low: {
    label: 'Low confidence',
    tone: 'bg-brand-soft text-ink-muted',
    hint: 'The retrieved scheme text did not clearly cover this question.',
  },
}

export function Avatar() {
  return <LogoMark tone="dark" className="mt-0.5 h-8 w-8 shrink-0 rounded-lg" />
}

export function TypingIndicator() {
  return (
    <div className="flex items-start gap-2.5" role="status" aria-label="SchemeBot is typing">
      <Avatar />
      <div className="flex items-center gap-1.5 rounded-2xl rounded-tl-md border border-line bg-surface px-4 py-3.5 shadow-card">
        {[0, 1, 2].map((i) => (
          <span
            key={i}
            className="typing-dot h-1.5 w-1.5 rounded-full bg-ink-faint"
            style={{ animationDelay: `${i * 0.15}s` }}
          />
        ))}
      </div>
    </div>
  )
}

export function SkeletonBubble({ label = 'Reading your document' }) {
  return (
    <div className="flex items-start gap-2.5" role="status" aria-label={label}>
      <Avatar />
      <div className="w-full max-w-sm space-y-2 rounded-2xl rounded-tl-md border border-line bg-surface p-4 shadow-card">
        <div className="skeleton h-3 w-11/12" />
        <div className="skeleton h-3 w-9/12" />
        <div className="skeleton h-3 w-6/12" />
      </div>
    </div>
  )
}

function ConfidenceBadge({ confidence, intent }) {
  const meta = CONFIDENCE[confidence]
  if (!meta) return null
  const extra =
    intent === 'eligibility_check'
      ? ' For eligibility checks, "Inferred" means some conditions could not be verified automatically.'
      : ''
  return (
    <span className="group relative inline-flex">
      <span
        tabIndex={0}
        aria-describedby={`conf-${confidence}-tip`}
        className={`inline-flex cursor-help items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-medium ${meta.tone}`}
      >
        {meta.label}
        <Icon name="info" className="h-3 w-3 opacity-70" />
      </span>
      <span
        id={`conf-${confidence}-tip`}
        role="tooltip"
        className="pointer-events-none absolute bottom-full left-0 z-20 mb-2 hidden w-64 rounded-lg bg-ink px-3 py-2 text-xs leading-relaxed text-surface shadow-raised group-focus-within:block group-hover:block"
      >
        {meta.hint}
        {extra}
      </span>
    </span>
  )
}

function SourceChips({ sources }) {
  const [openName, setOpenName] = useState(null)
  if (!sources || sources.length === 0) return null

  const byScheme = new Map()
  for (const source of sources) {
    const entry = byScheme.get(source.scheme_name) || { name: source.scheme_name, sections: [], dataAsOf: null }
    if (source.section && !entry.sections.includes(source.section)) entry.sections.push(source.section)
    if (source.data_as_of) entry.dataAsOf = source.data_as_of
    byScheme.set(source.scheme_name, entry)
  }
  const entries = [...byScheme.values()]
  const open = entries.find((e) => e.name === openName)

  return (
    <div className="mt-3 border-t border-line pt-3">
      <p className="mb-1.5 flex items-center gap-1 text-xs font-medium text-ink-muted">
        <Icon name="quote" className="h-3.5 w-3.5" /> Sources
      </p>
      <ul className="flex flex-wrap gap-1.5">
        {entries.map((entry) => {
          const isOpen = entry.name === openName
          return (
            <li key={entry.name} className="max-w-full">
              <button
                type="button"
                aria-expanded={isOpen}
                onClick={() => setOpenName(isOpen ? null : entry.name)}
                className={`flex max-w-full items-center gap-1 rounded-full border px-2.5 py-1 text-left text-xs font-medium transition-colors ${
                  isOpen
                    ? 'border-brand bg-brand text-white'
                    : 'border-line bg-surface-2 text-ink hover:border-ink-faint'
                }`}
              >
                <span className="truncate">{entry.name}</span>
                <Icon name="chevronDown" className={`h-3 w-3 shrink-0 transition-transform ${isOpen ? 'rotate-180' : ''}`} />
              </button>
            </li>
          )
        })}
      </ul>
      {open && (
        <div className="mt-2 rounded-lg bg-surface-2 px-3 py-2 text-xs text-ink-muted">
          <p className="font-semibold text-ink">{open.name}</p>
          {open.sections.length > 0 && <p>Section: {open.sections.map(sectionLabel).join(', ')}</p>}
          {open.dataAsOf && <p>{open.dataAsOf}</p>}
        </div>
      )}
    </div>
  )
}

function ErrorCard({ text, onRetry }) {
  return (
    <div className="rounded-2xl rounded-tl-md border border-danger/30 bg-danger-soft px-4 py-3 text-danger shadow-card" role="alert">
      <p className="flex items-start gap-2 text-sm font-medium">
        <Icon name="wifiOff" className="mt-0.5 h-4 w-4 shrink-0" />
        <span>{text}</span>
      </p>
      {onRetry && (
        <button
          type="button"
          onClick={onRetry}
          className="mt-2.5 inline-flex items-center gap-1.5 rounded-full bg-danger px-3.5 py-1.5 text-xs font-semibold text-danger-soft hover:opacity-90"
        >
          <Icon name="refresh" className="h-3.5 w-3.5" /> Retry
        </button>
      )}
    </div>
  )
}

function RefusalCard({ text }) {
  return (
    <div className="rounded-2xl rounded-tl-md border border-line bg-surface-2 px-4 py-3 shadow-card">
      <p className="flex items-center gap-2 text-sm font-semibold text-ink">
        <Icon name="info" className="h-4 w-4 text-ink-muted" /> I can't answer that
      </p>
      <p className="mt-1.5 text-sm text-ink-muted">{text}</p>
      <p className="mt-1 text-xs text-ink-faint">SchemeBot only answers from scheme data it can cite.</p>
      <a
        href={PORTAL_URL}
        target="_blank"
        rel="noopener noreferrer"
        className="mt-2.5 inline-flex items-center gap-1.5 text-sm font-semibold text-info hover:underline"
      >
        Browse myscheme.gov.in <Icon name="external" className="h-3.5 w-3.5" />
      </a>
    </div>
  )
}

export default function MessageBubble({
  message,
  sessionId,
  messageIndex,
  query,
  compact = false,
  onRetry,
}) {
  const { role, text, confidence, sources, intent, kind, noFeedback } = message
  const isUser = role === 'user'
  const size = compact ? 'text-[0.9rem]' : 'text-[0.95rem]'

  if (isUser) {
    return (
      <div className="msg-in flex justify-end">
        <div className={`max-w-[85%] whitespace-pre-wrap rounded-2xl rounded-tr-md bg-brand px-4 py-2.5 text-white shadow-card sm:max-w-[34rem] ${size}`}>
          {text}
        </div>
      </div>
    )
  }

  // Out-of-scope, or a search the backend declined (low confidence, nothing cited).
  const declinedSearch =
    (intent === 'scheme_search' || intent === 'comparison') &&
    confidence === 'low' &&
    (!sources || sources.length === 0)
  const refused = !kind && (intent === 'out_of_scope' || declinedSearch)
  const showBadge =
    !kind && !refused && confidence && ((sources && sources.length > 0) || intent === 'scheme_search' || intent === 'comparison')

  let body
  if (kind === 'error') {
    body = <ErrorCard text={text} onRetry={onRetry} />
  } else if (refused) {
    body = <RefusalCard text={text} />
  } else {
    body = (
      <div className="rounded-2xl rounded-tl-md border border-line bg-surface px-4 py-3 text-ink shadow-card">
        <div className={`prose-chat ${size}`}>{renderMarkdown(text)}</div>
        {showBadge && (
          <div className="mt-3">
            <ConfidenceBadge confidence={confidence} intent={intent} />
          </div>
        )}
        <SourceChips sources={sources} />
      </div>
    )
  }

  return (
    <div className="msg-in flex items-start gap-2.5">
      <Avatar />
      <div className="min-w-0 max-w-[calc(100%-2.75rem)] sm:max-w-[40rem]">
        {body}
        {!kind && !noFeedback && (
          <FeedbackButtons sessionId={sessionId} messageIndex={messageIndex} query={query} intent={intent} />
        )}
      </div>
    </div>
  )
}
