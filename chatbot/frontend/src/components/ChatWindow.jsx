import { useEffect, useRef } from 'react'
import Icon from './Icons'
import MessageBubble, { SkeletonBubble, TypingIndicator } from './MessageBubble'
import SchemeCard from './SchemeCard'

const SUGGESTIONS = [
  { icon: 'sprout', title: 'Schemes for farmers', question: 'What schemes are available for farmers?' },
  { icon: 'home', title: 'Housing subsidy', question: 'Am I eligible for a housing subsidy?' },
  { icon: 'file', title: 'SC/ST documents', question: 'What documents do I need for SC/ST schemes?' },
]

const MAX_CARDS = 4

function SuggestionList({ onPick, compact }) {
  return (
    <ul className={`grid w-full gap-2 ${compact ? 'grid-cols-1' : 'grid-cols-1 sm:grid-cols-3'}`}>
      {SUGGESTIONS.map((item) => (
        <li key={item.title}>
          <button
            type="button"
            onClick={() => onPick?.(item.question)}
            className="flex h-full w-full items-start gap-2.5 rounded-xl border border-line bg-surface p-3 text-left shadow-card transition-colors hover:border-ink-faint hover:bg-surface-2"
          >
            <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-brand-soft text-ink">
              <Icon name={item.icon} className="h-4 w-4" />
            </span>
            <span className="min-w-0">
              <span className="block text-sm font-semibold text-ink">{item.title}</span>
              <span className="block text-xs text-ink-muted">{item.question}</span>
            </span>
          </button>
        </li>
      ))}
    </ul>
  )
}

function SchemeCards({ sources, onViewDetails }) {
  const byScheme = new Map()
  for (const source of sources || []) {
    const entry = byScheme.get(source.scheme_name) || { name: source.scheme_name, sections: [] }
    if (source.section && !entry.sections.includes(source.section)) entry.sections.push(source.section)
    byScheme.set(source.scheme_name, entry)
  }
  const entries = [...byScheme.values()].slice(0, MAX_CARDS)
  if (entries.length === 0) return null

  return (
    <div className="ml-[2.625rem] mt-2">
      <p className="mb-1.5 text-xs font-medium text-ink-muted">Schemes mentioned</p>
      <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
        {entries.map((entry) => (
          <SchemeCard
            key={entry.name}
            schemeName={entry.name}
            sections={entry.sections}
            onViewDetails={onViewDetails ? () => onViewDetails(`Tell me more about ${entry.name}`) : undefined}
          />
        ))}
      </div>
    </div>
  )
}

function precedingUserText(messages, index) {
  for (let i = index - 1; i >= 0; i--) {
    if (messages[i].role === 'user') return messages[i].text
  }
  return ''
}

export default function ChatWindow({
  messages,
  isTyping,
  uploading = false,
  onExampleClick,
  onRetry,
  sessionId,
  compact = false,
  indexOffset = 0,
  label = 'Conversation',
}) {
  const scrollRef = useRef(null)

  useEffect(() => {
    const el = scrollRef.current
    if (el) el.scrollTo({ top: el.scrollHeight, behavior: 'smooth' })
  }, [messages, isTyping, uploading])

  const hasUserMessage = messages.some((m) => m.role === 'user')

  return (
    <div ref={scrollRef} className={`min-h-0 flex-1 overflow-y-auto ${compact ? 'px-3 py-4' : 'px-4 py-6'}`}>
      <div className={`mx-auto flex min-h-full w-full flex-col gap-4 ${compact ? '' : 'max-w-3xl'}`}>
        {messages.length === 0 && !isTyping && (
          <div className="my-auto flex flex-col items-center gap-5 py-8 text-center">
            <div>
              <h2 className="text-xl font-bold text-ink">What would you like to know?</h2>
              <p className="mt-1 text-sm text-ink-muted">
                Ask about eligibility, benefits or documents for any scheme, in English, Hindi or Tamil.
              </p>
            </div>
            <SuggestionList onPick={onExampleClick} />
          </div>
        )}

        <div role="log" aria-live="polite" aria-relevant="additions" aria-label={label} className="flex flex-col gap-4">
          {messages.map((msg, index) => (
            <div key={msg.id} className="flex flex-col">
              <MessageBubble
                message={msg}
                sessionId={sessionId}
                messageIndex={indexOffset + index}
                query={precedingUserText(messages, index)}
                compact={compact}
                onRetry={msg.retryText && onRetry ? () => onRetry(msg.retryText, msg.id) : undefined}
              />
              {index === messages.length - 1 && msg.quickReplies?.length > 0 && !isTyping && (
                <div className="flex flex-wrap gap-2 pl-[2.625rem] pt-2" role="group" aria-label="Quick replies">
                  {msg.quickReplies.map((chip) => (
                    <button
                      key={chip.value}
                      type="button"
                      onClick={() => onExampleClick?.(chip.value)}
                      className="rounded-full border border-line bg-surface px-3 py-1.5 text-sm font-medium text-ink shadow-card transition-colors hover:border-ink-faint hover:bg-surface-2"
                    >
                      {chip.label}
                    </button>
                  ))}
                </div>
              )}
              {!compact &&
                msg.role === 'assistant' &&
                (msg.intent === 'scheme_search' || msg.intent === 'comparison') &&
                msg.confidence !== 'low' && <SchemeCards sources={msg.sources} onViewDetails={onExampleClick} />}
            </div>
          ))}
        </div>

        {messages.length > 0 && !hasUserMessage && !isTyping && (
          <div className="pl-[2.625rem]">
            <p className="mb-2 text-xs font-medium text-ink-muted">Try asking</p>
            <SuggestionList onPick={onExampleClick} compact />
          </div>
        )}

        {isTyping && <TypingIndicator />}
        {uploading && !isTyping && <SkeletonBubble />}
      </div>
    </div>
  )
}
