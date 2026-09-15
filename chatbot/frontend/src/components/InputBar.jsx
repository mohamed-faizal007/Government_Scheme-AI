import { useRef, useState } from 'react'

const PLACEHOLDERS = {
  en: 'Ask about any government scheme...',
  hi: 'किसी भी सरकारी योजना के बारे में पूछें...',
  ta: 'எந்த அரசு திட்டத்தைப் பற்றியும் கேளுங்கள்...',
}

export default function InputBar({ language, onSend, onFileSelect, disabled }) {
  const [text, setText] = useState('')
  const fileInputRef = useRef(null)

  const submit = () => {
    const trimmed = text.trim()
    if (!trimmed || disabled) return
    onSend(trimmed)
    setText('')
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      submit()
    }
  }

  const handleFileChange = (e) => {
    const file = e.target.files?.[0]
    if (file) onFileSelect(file)
    e.target.value = ''
  }

  return (
    <div className="border-t border-border bg-surface p-3">
      <div className="mx-auto flex max-w-3xl items-end gap-2">
        <div className="group relative shrink-0">
          <button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            disabled={disabled}
            className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full border border-primary text-primary transition-colors hover:bg-primary-light disabled:opacity-50"
          >
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="h-5 w-5">
              <path d="M21.44 11.05l-9.19 9.19a6 6 0 01-8.49-8.49l9.19-9.19a4 4 0 015.66 5.66l-9.2 9.19a2 2 0 01-2.83-2.83l8.49-8.48" />
            </svg>
          </button>
          <span className="pointer-events-none absolute bottom-full left-1/2 mb-2 w-max max-w-[200px] -translate-x-1/2 rounded-md bg-text-primary px-2 py-1 text-center text-[11px] text-white opacity-0 transition-opacity group-hover:opacity-100">
            Upload income certificate or Aadhaar
          </span>
        </div>
        <input
          ref={fileInputRef}
          type="file"
          accept="application/pdf"
          className="hidden"
          onChange={handleFileChange}
        />

        <div className="flex min-h-11 flex-1 items-center rounded-full border border-border bg-bg px-4 py-2 transition-colors focus-within:border-primary">
          <textarea
            rows={1}
            value={text}
            onChange={(e) => setText(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={disabled}
            placeholder={PLACEHOLDERS[language] || PLACEHOLDERS.en}
            className="max-h-32 w-full resize-none bg-transparent text-sm text-text-primary placeholder:text-text-secondary focus:outline-none disabled:opacity-50"
          />
        </div>

        <button
          type="button"
          onClick={submit}
          disabled={disabled || !text.trim()}
          className="h-11 shrink-0 rounded-full bg-accent px-5 text-sm font-semibold text-white shadow-card transition-colors hover:bg-accent-hover disabled:opacity-50"
        >
          Send
        </button>
      </div>
    </div>
  )
}
