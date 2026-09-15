export default function SchemeCard({ schemeName, benefitSummary, eligibilitySummary, sourceFile }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-3 shadow-sm">
      <h4 className="text-sm font-semibold text-slate-800">{schemeName}</h4>
      {benefitSummary && <p className="mt-1 text-xs text-slate-600">{benefitSummary}</p>}
      {eligibilitySummary && (
        <p className="mt-1 text-xs text-slate-500">Eligibility: {eligibilitySummary}</p>
      )}
      {sourceFile && <p className="mt-2 text-[11px] text-slate-400">{sourceFile}</p>}
    </div>
  )
}
