import { useEffect, useRef, useState } from 'react'
import ChatWindow from './ChatWindow'
import Icon, { LogoMark } from './Icons'
import InputBar from './InputBar'

// Widget feedback shares a session with the main chat, so offset its message
// indexes to keep each (session, message_index) feedback record distinct.
export const WIDGET_FEEDBACK_OFFSET = 10000

function useIsDesktop() {
  const query = '(min-width: 1024px)'
  const [matches, setMatches] = useState(() => window.matchMedia(query).matches)
  useEffect(() => {
    const media = window.matchMedia(query)
    const onChange = () => setMatches(media.matches)
    media.addEventListener('change', onChange)
    return () => media.removeEventListener('change', onChange)
  }, [])
  return matches
}

function IconButton({ label, icon, onClick }) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-label={label}
      title={label}
      className="flex h-8 w-8 items-center justify-center rounded-lg text-on-hero-muted transition-colors hover:bg-white/10 hover:text-white"
    >
      <Icon name={icon} className="h-4 w-4" />
    </button>
  )
}

function WidgetHeader({ connected, children }) {
  return (
    <div className="flex items-center justify-between gap-2 bg-brand px-3.5 py-3">
      <div className="flex min-w-0 items-center gap-2.5">
        <LogoMark className="h-8 w-8 shrink-0 rounded-lg" />
        <div className="min-w-0 leading-tight">
          <h2 className="text-sm font-bold text-white">SchemeBot</h2>
          <p className="flex items-center gap-1.5 text-xs text-on-hero-muted" role="status">
            <span className={`h-1.5 w-1.5 rounded-full ${connected ? 'bg-emerald-400' : 'bg-amber-400'}`} />
            {connected ? 'Connected' : 'Reconnecting…'}
          </p>
        </div>
      </div>
      <div className="flex items-center gap-0.5">{children}</div>
    </div>
  )
}

export default function HeroChatWidget({
  messages,
  onSend,
  onRetry,
  typing,
  minimized,
  onMinimize,
  onRestore,
  expanded,
  onExpand,
  onCollapseExpand,
  onRefresh,
  onFileSelect,
  connected,
  sessionId,
  uploading,
}) {
  const isDesktop = useIsDesktop()
  const [mobileOpen, setMobileOpen] = useState(false)
  const containerRef = useRef(null)

  const fullscreen = isDesktop ? expanded : mobileOpen
  const closeFullscreen = isDesktop ? onCollapseExpand : () => setMobileOpen(false)

  useEffect(() => {
    if (!fullscreen) return undefined
    const onKey = (e) => {
      if (e.key === 'Escape') closeFullscreen()
    }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  })

  useEffect(() => {
    if (fullscreen) containerRef.current?.querySelector('textarea')?.focus()
  }, [fullscreen])

  // Lock page scroll behind the full-screen chat.
  useEffect(() => {
    if (!fullscreen) return undefined
    const previous = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    return () => {
      document.body.style.overflow = previous
    }
  }, [fullscreen])

  if (!isDesktop && !mobileOpen) {
    return (
      <button
        type="button"
        onClick={() => setMobileOpen(true)}
        className="fixed bottom-4 right-4 z-40 flex items-center gap-2 rounded-full bg-accent px-4 py-3 text-sm font-semibold text-white shadow-float transition-colors hover:bg-accent-hover"
      >
        <Icon name="chat" className="h-5 w-5" /> Ask SchemeBot
      </button>
    )
  }

  if (isDesktop && minimized) {
    return (
      <button
        type="button"
        onClick={onRestore}
        aria-label="Open chat"
        className="fixed bottom-6 right-6 z-40 flex h-14 w-14 items-center justify-center rounded-full bg-accent text-white shadow-float transition-transform hover:scale-105"
      >
        <Icon name="chat" className="h-6 w-6" />
      </button>
    )
  }

  const body = (
    <>
      <WidgetHeader connected={connected}>
        <IconButton label="Start a new chat" icon="refresh" onClick={onRefresh} />
        {fullscreen ? (
          <IconButton label="Close full-screen chat" icon="close" onClick={closeFullscreen} />
        ) : (
          <>
            <IconButton label="Expand chat" icon="expand" onClick={onExpand} />
            <IconButton label="Minimize chat" icon="minimize" onClick={onMinimize} />
          </>
        )}
      </WidgetHeader>
      <div className="flex min-h-0 flex-1 flex-col bg-bg">
        <ChatWindow
          messages={messages}
          isTyping={typing}
          uploading={uploading}
          onExampleClick={onSend}
          onRetry={onRetry}
          sessionId={sessionId}
          compact={!fullscreen}
          indexOffset={WIDGET_FEEDBACK_OFFSET}
          label="Quick chat"
        />
        <InputBar compact={!fullscreen} onSend={onSend} onFileSelect={onFileSelect} disabled={!connected} />
      </div>
    </>
  )

  if (fullscreen) {
    return (
      <div className="fixed inset-0 z-50 flex lg:items-stretch lg:justify-center">
        <button
          type="button"
          tabIndex={-1}
          aria-hidden="true"
          onClick={closeFullscreen}
          className="absolute inset-0 hidden cursor-default bg-black/60 lg:block"
        />
        <div
          ref={containerRef}
          id="hero-chat-widget"
          role="dialog"
          aria-modal="true"
          aria-label="SchemeBot chat"
          className="relative flex h-full w-full flex-col overflow-hidden bg-bg shadow-float lg:max-w-3xl"
        >
          {body}
        </div>
      </div>
    )
  }

  return (
    <div
      ref={containerRef}
      id="hero-chat-widget"
      role="region"
      aria-label="SchemeBot quick chat"
      className="mx-auto flex h-[540px] w-full max-w-[440px] flex-col overflow-hidden rounded-2xl border border-white/15 bg-bg shadow-float"
    >
      {body}
    </div>
  )
}
