import { useEffect, useRef } from 'react'
import ChatWindow from './ChatWindow'
import InputBar from './InputBar'

function CompactTypingIndicator() {
  return (
    <div className="flex items-center gap-1 rounded-2xl rounded-tl-sm border-l-2 border-accent bg-white px-3 py-2">
      <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-primary/60 [animation-delay:-0.3s]" />
      <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-primary/60 [animation-delay:-0.15s]" />
      <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-primary/60" />
    </div>
  )
}

function WidgetHeader({ onRefresh, onExpandToggle, onMinimize, onClose, expanded }) {
  return (
    <div className="flex items-center justify-between border-b border-white/10 px-4 py-3">
      <div className="flex items-center gap-2">
        <span className="text-lg">🏛️</span>
        <span className="font-display text-sm font-bold text-white">SchemeBot</span>
        <span className="ml-1 flex items-center gap-1 text-xs text-green-400">
          <span className="h-1.5 w-1.5 rounded-full bg-green-400" /> Online
        </span>
      </div>
      <div className="flex items-center gap-3 text-white/60">
        <button
          type="button"
          onClick={onRefresh}
          aria-label="New chat"
          className="transition-colors hover:text-white"
        >
          ↺
        </button>
        {expanded ? (
          <button
            type="button"
            onClick={onClose}
            aria-label="Close fullscreen"
            className="transition-colors hover:text-white"
          >
            ✕
          </button>
        ) : (
          <>
            <button
              type="button"
              onClick={onExpandToggle}
              aria-label="Expand"
              className="transition-colors hover:text-white"
            >
              ⛶
            </button>
            <button
              type="button"
              onClick={onMinimize}
              aria-label="Minimize"
              className="transition-colors hover:text-white"
            >
              —
            </button>
          </>
        )}
      </div>
    </div>
  )
}

export default function HeroChatWidget({
  messages,
  input,
  onInputChange,
  onSend,
  typing,
  minimized,
  onMinimize,
  onRestore,
  expanded,
  onExpand,
  onCollapseExpand,
  onRefresh,
  onFileSelect,
  language,
  connected,
}) {
  const messagesContainerRef = useRef(null)
  const inputRef = useRef(null)

  useEffect(() => {
    const container = messagesContainerRef.current
    if (!container) return
    container.scrollTop = container.scrollHeight
  }, [messages, typing])

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      onSend(input)
    }
  }

  if (minimized) {
    return (
      <button
        type="button"
        onClick={onRestore}
        aria-label="Open chat"
        className="fixed bottom-6 right-6 z-40 hidden h-14 w-14 items-center justify-center rounded-full text-2xl text-white shadow-2xl transition-transform hover:scale-105 lg:flex"
        style={{ backgroundColor: '#E94560' }}
      >
        🏛️
      </button>
    )
  }

  if (expanded) {
    return (
      <div className="fixed inset-0 z-50 hidden lg:block">
        <div className="absolute inset-0 bg-black/60" onClick={onCollapseExpand} />
        <div
          className="relative mx-auto flex h-full w-full max-w-3xl flex-col overflow-hidden shadow-2xl"
          style={{ backgroundColor: '#16213E' }}
        >
          <WidgetHeader
            expanded
            onRefresh={onRefresh}
            onClose={onCollapseExpand}
          />
          <div className="flex min-h-0 flex-1 flex-col bg-white">
            <ChatWindow messages={messages} isTyping={typing} onExampleClick={onSend} />
            <InputBar
              language={language}
              onSend={onSend}
              onFileSelect={onFileSelect}
              disabled={!connected}
            />
          </div>
        </div>
      </div>
    )
  }

  return (
    <div id="hero-chat-widget" className="hidden self-center lg:block">
      <div
        className="mx-auto flex h-[480px] w-[380px] flex-col overflow-hidden rounded-2xl border border-white/10 shadow-2xl"
        style={{ backgroundColor: '#16213E' }}
      >
        <WidgetHeader
          onRefresh={onRefresh}
          onExpandToggle={onExpand}
          onMinimize={onMinimize}
        />

        {/* Messages */}
        <div
          ref={messagesContainerRef}
          className="flex-1 space-y-3 overflow-y-auto px-4 py-4"
          style={{ backgroundColor: '#0D1B2A' }}
        >
          {messages.map((msg) =>
            msg.role === 'user' ? (
              <div
                key={msg.id}
                className="ml-auto max-w-[85%] rounded-2xl rounded-tr-sm px-3 py-2 text-xs text-white"
                style={{ backgroundColor: '#E94560' }}
              >
                {msg.text}
              </div>
            ) : (
              <div
                key={msg.id}
                className="max-w-[85%] rounded-2xl rounded-tl-sm border-l-2 border-accent bg-white px-3 py-2 text-xs text-text-primary"
              >
                {msg.text}
              </div>
            )
          )}
          {typing && <CompactTypingIndicator />}
        </div>

        {/* Input bar */}
        <div className="border-t border-white/10 p-3">
          <div className="flex items-center gap-2 rounded-full border border-white/20 bg-white/10 px-3 py-2">
            <button type="button" aria-label="Attach file" className="text-white/60 transition-colors hover:text-white">
              📎
            </button>
            <input
              ref={inputRef}
              type="text"
              value={input}
              onChange={(e) => onInputChange(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={!connected}
              placeholder="Ask about any scheme..."
              className="min-w-0 flex-1 bg-transparent text-xs text-white placeholder:text-white/60 focus:outline-none disabled:opacity-50"
            />
            <button
              type="button"
              onClick={() => onSend(input)}
              disabled={!connected || !input.trim()}
              aria-label="Send"
              className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-white transition-colors disabled:opacity-50"
              style={{ backgroundColor: '#E94560' }}
            >
              →
            </button>
          </div>
          <p className="mt-2 text-center text-xs text-white/40">Press Enter or click →</p>
        </div>
      </div>
    </div>
  )
}
