import { useEffect, useRef } from 'react'
import MessageBubble from './MessageBubble'
import SchemeCard from './SchemeCard'

function TypingIndicator() {
  return (
    <div className="flex justify-start">
      <div className="flex items-center gap-1 rounded-lg border border-slate-200 bg-white px-4 py-3 shadow-sm">
        <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-slate-400 [animation-delay:-0.3s]" />
        <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-slate-400 [animation-delay:-0.15s]" />
        <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-slate-400" />
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
    <div className="ml-1 grid grid-cols-1 gap-2 sm:grid-cols-2">
      {unique.map((source, idx) => (
        <SchemeCard
          key={idx}
          schemeName={source.scheme_name}
          eligibilitySummary={source.section}
          sourceFile={source.source_file}
        />
      ))}
    </div>
  )
}

export default function ChatWindow({ messages, isTyping }) {
  const bottomRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isTyping])

  return (
    <div className="flex-1 space-y-3 overflow-y-auto p-4">
      {messages.length === 0 && !isTyping && (
        <div className="flex h-full items-center justify-center text-center text-sm text-slate-400">
          Ask about eligibility, benefits, or documents for any government scheme.
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
