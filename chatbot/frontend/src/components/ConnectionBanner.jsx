export default function ConnectionBanner({ connected }) {
  if (connected) return null
  return (
    <div className="bg-amber-100 px-4 py-1.5 text-center text-xs font-medium text-amber-800">
      Reconnecting to server...
    </div>
  )
}
