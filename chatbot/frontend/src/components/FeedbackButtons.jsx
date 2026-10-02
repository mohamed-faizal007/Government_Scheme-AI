import axios from 'axios'
import { useEffect, useRef, useState } from 'react'
import { API_BASE } from '../utils/api'

const OPTIONS = [
  { rating: 'positive', icon: '👍', label: 'Helpful' },
  { rating: 'negative', icon: '👎', label: 'Not helpful' },
]

export default function FeedbackButtons({ sessionId, messageIndex, query, intent }) {
  const [rating, setRating] = useState(null)
  const [thanks, setThanks] = useState(false)
  const timerRef = useRef(null)

  useEffect(() => () => clearTimeout(timerRef.current), [])

  const submit = async (value) => {
    if (rating) return
    setRating(value)
    setThanks(true)
    clearTimeout(timerRef.current)
    timerRef.current = setTimeout(() => setThanks(false), 2000)
    try {
      await axios.post(`${API_BASE}/feedback`, {
        session_id: sessionId,
        message_index: messageIndex,
        rating: value,
        query: query || '',
        intent: intent || '',
      })
    } catch {
      // Let the user try again if the request didn't go through.
      setRating(null)
      setThanks(false)
    }
  }

  return (
    <div className="relative mt-2 flex items-center gap-1.5">
      <span className="text-[11px] text-text-secondary">Was this helpful?</span>
      {OPTIONS.map((opt) => {
        const selected = rating === opt.rating
        return (
          <button
            key={opt.rating}
            type="button"
            aria-label={opt.label}
            aria-pressed={selected}
            disabled={rating !== null}
            onClick={() => submit(opt.rating)}
            className={`rounded-full border px-2 py-0.5 text-xs transition-colors ${
              selected
                ? 'border-primary bg-primary text-white'
                : 'border-border bg-bg hover:bg-primary-light disabled:opacity-40 disabled:hover:bg-bg'
            }`}
          >
            {opt.icon}
          </button>
        )
      })}
      {thanks && (
        <span
          role="status"
          className="absolute -top-7 left-0 whitespace-nowrap rounded-md bg-text-primary px-2 py-1 text-[11px] text-white shadow-card"
        >
          Thanks for your feedback!
        </span>
      )}
    </div>
  )
}
