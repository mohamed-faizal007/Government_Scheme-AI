import axios from 'axios'
import { useEffect, useState } from 'react'
import { API_BASE } from '../utils/api'

const POLL_MS = 5 * 60 * 1000

function formatDate(iso) {
  const date = iso ? new Date(iso) : null
  if (!date || Number.isNaN(date.getTime())) return null
  return date.toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' })
}

// Shows when the scheme data was last refreshed. Hidden when the backend has
// no successful sync date; never claims a "live" connection.
export default function SyncStatusBadge() {
  const [lastSync, setLastSync] = useState(null)

  useEffect(() => {
    let cancelled = false
    const load = async () => {
      try {
        const { data } = await axios.get(`${API_BASE}/sync/status`)
        if (!cancelled) setLastSync(data.last_sync || null)
      } catch {
        if (!cancelled) setLastSync(null)
      }
    }
    load()
    const id = setInterval(load, POLL_MS)
    return () => {
      cancelled = true
      clearInterval(id)
    }
  }, [])

  const label = formatDate(lastSync)
  if (!label) return null

  return (
    <span
      title={`Last successful data update: ${new Date(lastSync).toLocaleString()}`}
      className="hidden whitespace-nowrap rounded-full bg-white/10 px-2.5 py-1 text-xs font-medium text-on-hero-muted md:inline-block"
    >
      Data last updated {label}
    </span>
  )
}
