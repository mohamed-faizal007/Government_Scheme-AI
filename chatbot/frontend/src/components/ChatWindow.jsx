import { useEffect, useRef } from 'react'
import MessageBubble from './MessageBubble'
import SchemeCard from './SchemeCard'

const EXAMPLE_PROMPTS = [
  {
    icon: '🌾',
    title: 'Schemes for farmers',
    description: 'What schemes are available for farmers?',
  },
  {
    icon: '🏠',
    title: 'Housing subsidy',
    description: 'Am I eligible for a housing subsidy?',
  },
  {
    icon: '📄',
    title: 'SC/ST documents',
    description: 'What documents do I need for SC/ST schemes?',
  },
]

function TypingIndicator() {
  return (
    <div className="flex items-start gap-2">
      <div className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary-light text-base">
        🏛️
      </div>
      <div className="flex items-center gap-1 rounded-2xl border-l-[3px] border-accent bg-surface px-4 py-3 shadow-card">
        <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-primary/60 [animation-delay:-0.3s]" />
        <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-primary/60 [animation-delay:-0.15s]" />
        <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-primary/60" />
      </div>
    </div>
  )
}

function SchemeCards({ sources }) {
  const unique = []
  const seen = new Set()
  for (const source of sources || []) {
    if (seen.has(source.scheme_name)) continue
    seen.add(source.scheme_name)
    unique.push(source)
  }
  if (unique.length === 0) return null

  return (
    <div className="ml-10 grid grid-cols-1 gap-2 sm:grid-cols-2">
      {unique.map((source, idx) => (
        <SchemeCard
          key={idx}
          index={idx}
          schemeName={source.scheme_name}
          eligibilitySummary={source.section}
          sourceFile={source.source_file}
        />
      ))}
    </div>
  )
}

export default function ChatWindow({ messages, isTyping, onExampleClick }) {
  const bottomRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isTyping])

  return (
    <div className="flex-1 space-y-3 overflow-y-auto p-4">
      {messages.length === 0 && !isTyping && (
        <div className="flex h-full flex-col items-center justify-center gap-4 px-4 text-center">
          <p className="text-sm text-text-secondary">
            Ask about eligibility, benefits, or documents for any government scheme.
          </p>
          <div className="grid w-full max-w-2xl grid-cols-1 gap-3 sm:grid-cols-3">
            {EXAMPLE_PROMPTS.map((prompt) => (
              <button
                key={prompt.title}
                type="button"
                onClick={() => onExampleClick?.(prompt.description)}
                className="flex flex-col items-start gap-1 rounded-xl border border-border bg-surface p-3 text-left shadow-card transition-shadow hover:shadow-md"
              >
                <span className="text-xl">{prompt.icon}</span>
                <span className="text-sm font-semibold text-text-primary">{prompt.title}</span>
                <span className="text-xs text-text-secondary">{prompt.description}</span>
              </button>
            ))}
          </div>
        </div>
      )}

      {messages.map((msg) => (
        <div key={msg.id} className="space-y-2">
          <MessageBubble
            role={msg.role}
            text={msg.text}
            confidence={msg.confidence}
            sources={msg.sources}
          />
          {msg.role === 'assistant' &&
            (msg.intent === 'scheme_search' || msg.intent === 'comparison') && (
              <SchemeCards sources={msg.sources} />
            )}
        </div>
      ))}

      {isTyping && <TypingIndicator />}
      <div ref={bottomRef} />
    </div>
  )
}
