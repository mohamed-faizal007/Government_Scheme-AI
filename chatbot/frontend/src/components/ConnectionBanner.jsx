import Icon from './Icons'

export default function ConnectionBanner({ connected }) {
  if (connected) return null
  return (
    <div
      role="status"
      className="flex items-center justify-center gap-2 bg-danger-soft px-4 py-2 text-center text-sm font-medium text-danger"
    >
      <Icon name="wifiOff" className="h-4 w-4 shrink-0" />
      Can't reach the server. Trying to reconnect…
    </div>
  )
}
