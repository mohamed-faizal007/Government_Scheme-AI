import { sectionLabel } from '../utils/sections'
import Icon from './Icons'

export default function SchemeCard({ schemeName, benefitSummary, sections = [], onViewDetails }) {
  return (
    <article className="flex flex-col gap-2 rounded-xl border border-line bg-surface p-3.5 shadow-card">
      <h4 className="text-sm font-semibold leading-snug text-ink">{schemeName}</h4>
      {benefitSummary && <p className="text-xs text-ink-muted">{benefitSummary}</p>}
      {sections.length > 0 && (
        <ul className="flex flex-wrap gap-1.5" aria-label="Sections available">
          {sections.map((section) => (
            <li
              key={section}
              className="rounded-full bg-brand-soft px-2 py-0.5 text-xs font-medium text-ink-muted"
            >
              {sectionLabel(section)}
            </li>
          ))}
        </ul>
      )}
      {onViewDetails && (
        <button
          type="button"
          onClick={onViewDetails}
          className="mt-auto inline-flex items-center gap-1 self-start rounded-md text-xs font-semibold text-info hover:underline"
        >
          View details
          <Icon name="arrowRight" className="h-3.5 w-3.5" />
          <span className="sr-only"> for {schemeName}</span>
        </button>
      )}
    </article>
  )
}
