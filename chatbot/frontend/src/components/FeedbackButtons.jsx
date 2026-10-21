import axios from 'axios'
import { useEffect, useRef, useState } from 'react'
import { API_BASE } from '../utils/api'
import Icon from './Icons'

const OPTIONS = [
  { rating: 'positive', icon: 'thumbUp', label: 'Helpful' },
  { rating: 'negative', icon: 'thumbDown', label: 'Not helpful' },
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
    timerRef.current = setTimeout(() => setThanks(false), 2500)
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
    <div className="mt-3 flex items-center gap-2" role="group" aria-label="Rate this answer">
      <span className="text-xs text-ink-muted">Was this helpful?</span>
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
            className={`flex h-8 w-8 items-center justify-center rounded-full border transition-colors ${
              selected
                ? 'border-brand bg-brand text-white'
                : 'border-line bg-surface text-ink-muted hover:bg-brand-soft hover:text-ink disabled:opacity-40 disabled:hover:bg-surface'
            }`}
          >
            <Icon name={opt.icon} className="h-4 w-4" />
          </button>
        )
      })}
      <span role="status" className="text-xs font-medium text-success">
        {thanks ? 'Thanks for your feedback' : ''}
      </span>
    </div>
  )
}
