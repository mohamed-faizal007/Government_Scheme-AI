import { useEffect, useRef, useState } from 'react'
import Icon from './Icons'

const PLACEHOLDER = 'Ask about any scheme…'

export default function InputBar({ onSend, onFileSelect, disabled, prefill, compact = false, inputId }) {
  const [text, setText] = useState('')
  const fileInputRef = useRef(null)
  const textareaRef = useRef(null)

  useEffect(() => {
    if (!prefill) return
    setText(prefill.text)
    textareaRef.current?.focus()
  }, [prefill?.id])

  // Grow with content up to the max-h set on the textarea.
  useEffect(() => {
    const el = textareaRef.current
    if (!el) return
    el.style.height = 'auto'
    el.style.height = `${el.scrollHeight}px`
  }, [text])

  const submit = () => {
    const trimmed = text.trim()
    if (!trimmed || disabled) return
    onSend(trimmed)
    setText('')
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey && !e.nativeEvent.isComposing) {
      e.preventDefault()
      submit()
    }
  }

  const handleFileChange = (e) => {
    const file = e.target.files?.[0]
    if (file) onFileSelect?.(file)
    e.target.value = ''
  }

  return (
    <div className="border-t border-line bg-surface p-3">
      <div className={`mx-auto flex items-end gap-2 ${compact ? '' : 'max-w-3xl'}`}>
        <button
          type="button"
          onClick={() => fileInputRef.current?.click()}
          disabled={disabled}
          aria-label="Upload a PDF document, such as an income certificate or Aadhaar"
          title="Upload income certificate or Aadhaar (PDF)"
          className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full border border-line text-ink-muted transition-colors hover:bg-brand-soft hover:text-ink disabled:opacity-50"
        >
          <Icon name="paperclip" />
        </button>
        <input
          ref={fileInputRef}
          type="file"
          accept="application/pdf"
          className="hidden"
          tabIndex={-1}
          aria-hidden="true"
          onChange={handleFileChange}
        />

        <div className="flex min-h-11 flex-1 items-center rounded-3xl border border-line bg-surface-2 px-4 py-2 transition-colors focus-within:border-ink-faint focus-within:ring-2 focus-within:ring-[var(--focus)]/30">
          <textarea
            id={inputId}
            ref={textareaRef}
            rows={1}
            value={text}
            onChange={(e) => setText(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={disabled}
            aria-label="Your question"
            placeholder={PLACEHOLDER}
            className="max-h-32 w-full resize-none bg-transparent text-[0.95rem] text-ink outline-none placeholder:text-ink-faint disabled:opacity-60"
          />
        </div>

        <button
          type="button"
          onClick={submit}
          disabled={disabled || !text.trim()}
          aria-label="Send message"
          className="flex h-11 shrink-0 items-center justify-center gap-1.5 rounded-full bg-accent px-4 text-sm font-semibold text-white transition-colors hover:bg-accent-hover disabled:opacity-50 sm:px-5"
        >
          <span className={compact ? 'sr-only' : 'hidden sm:inline'}>Send</span>
          <Icon name="send" className="h-4 w-4" />
        </button>
      </div>
    </div>
  )
}
