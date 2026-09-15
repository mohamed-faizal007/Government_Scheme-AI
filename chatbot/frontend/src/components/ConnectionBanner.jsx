export default function ConnectionBanner({ connected }) {
  if (connected) return null
  return (
    <div className="bg-danger-light px-4 py-1.5 text-center text-xs font-medium text-danger">
      Reconnecting to server...
    </div>
  )
}
