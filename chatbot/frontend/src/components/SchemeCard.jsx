const BORDER_COLORS = ['border-l-primary', 'border-l-accent', 'border-l-success', 'border-l-amber']

export default function SchemeCard({ schemeName, benefitSummary, eligibilitySummary, sourceFile, index = 0 }) {
  const borderColor = BORDER_COLORS[index % BORDER_COLORS.length]

  return (
    <div
      className={`group cursor-default rounded-lg border border-border ${borderColor} border-l-4 bg-surface p-3 shadow-card transition-shadow hover:shadow-md`}
    >
      <div className="flex items-start justify-between gap-2">
        <h4 className="text-sm font-bold text-text-primary">{schemeName}</h4>
        <span className="text-text-secondary opacity-0 transition-opacity group-hover:opacity-100">→</span>
      </div>
      {eligibilitySummary && (
        <span className="mt-1.5 inline-block rounded-full bg-primary-light px-2 py-0.5 text-[11px] font-medium text-primary">
          {eligibilitySummary}
        </span>
      )}
      {benefitSummary && <p className="mt-1.5 text-xs text-text-secondary">{benefitSummary}</p>}
    </div>
  )
}
