import axios from 'axios'
import { useEffect, useState } from 'react'
import { API_BASE } from '../utils/api'

const POLL_MS = 5 * 60 * 1000
const HOUR_MS = 60 * 60 * 1000

const STATES = {
  live: { dot: 'bg-green-400', label: 'Live' },
  syncing: { dot: 'bg-yellow-400', label: 'Syncing...' },
  stale: { dot: 'bg-amber', label: 'Stale' },
  offline: { dot: 'bg-gray-400', label: 'Offline' },
}

function deriveState(status) {
  if (!status) return 'offline'
  if (status.sync_in_progress) return 'syncing'
  const last = status.last_sync ? Date.parse(status.last_sync) : NaN
  if (Number.isNaN(last)) return 'offline'
  const age = Date.now() - last
  if (age <= 24 * HOUR_MS) return 'live'
  if (age <= 48 * HOUR_MS) return 'stale'
  return 'offline'
}

export default function SyncStatusBadge() {
  const [status, setStatus] = useState(null)

  useEffect(() => {
    let cancelled = false
    const load = async () => {
      try {
        const { data } = await axios.get(`${API_BASE}/sync/status`)
        if (!cancelled) setStatus(data)
      } catch {
        if (!cancelled) setStatus(null)
      }
    }
    load()
    const id = setInterval(load, POLL_MS)
    return () => {
      cancelled = true
      clearInterval(id)
    }
  }, [])

  const state = STATES[deriveState(status)]
  const title = status?.last_sync
    ? `Last sync: ${new Date(status.last_sync).toLocaleString()}`
    : 'No successful sync yet'

  return (
    <span title={title} className="flex items-center gap-1.5 text-xs font-medium text-white/90">
      <span className={`h-2 w-2 rounded-full ${state.dot}`} />
      {state.label}
    </span>
  )
}
