import { useState } from 'react'
import Icon from './Icons'

// The five details the eligibility check asks for, in the order it asks.
const REQUIRED_FIELDS = [
  { key: 'age', label: 'Age' },
  { key: 'state', label: 'State' },
  { key: 'income_annual', label: 'Annual income' },
  { key: 'category', label: 'Category' },
  { key: 'gender', label: 'Gender' },
]

const OPTIONAL_LABELS = {
  is_student: 'Student',
  is_employed: 'Employed',
  occupation: 'Occupation',
  disability: 'Disability',
  is_ex_serviceman: 'Ex-serviceman',
}

const isFilled = (value) => value !== null && value !== undefined

function formatValue(value) {
  if (typeof value === 'boolean') return value ? 'Yes' : 'No'
  return String(value)
}

// reasons mixes failed and unverifiable conditions; when eligible is true it
// holds only conditions the rules engine could not check.
function resultState(result) {
  const reasons = result.reasons || []
  if (!result.eligible) return 'not_eligible'
  return reasons.length > 0 ? 'needs_verification' : 'eligible'
}

const STATES = {
  eligible: {
    title: 'Eligible',
    icon: 'checkCircle',
    box: 'border-success/30 bg-success-soft',
    text: 'text-success',
    note: 'You meet every condition we could check.',
  },
  not_eligible: {
    title: 'Not eligible',
    icon: 'xCircle',
    box: 'border-danger/30 bg-danger-soft',
    text: 'text-danger',
    note: 'Based on the details you gave, these conditions are not met:',
    listLabel: null,
  },
  needs_verification: {
    title: 'Needs verification',
    icon: 'alertCircle',
    box: 'border-warning/30 bg-warning-soft',
    text: 'text-warning',
    note: 'You meet the conditions we could check, but some need a human to confirm.',
    listLabel: 'We could not check these',
  },
}

function ResultCard({ result }) {
  const state = STATES[resultState(result)]
  const reasons = result.reasons || []
  return (
    <div className={`rounded-xl border p-3 ${state.box}`}>
      {result.scheme_name && <p className="text-xs font-medium text-ink-muted">{result.scheme_name}</p>}
      <p className={`mt-0.5 flex items-center gap-1.5 text-base font-bold ${state.text}`}>
        <Icon name={state.icon} className="h-5 w-5" /> {state.title}
      </p>
      <p className="mt-1 text-xs text-ink-muted">{state.note}</p>
      {reasons.length > 0 && (
        <div className="mt-2">
          {state.listLabel && <p className="text-xs font-semibold text-ink">{state.listLabel}</p>}
          <ul className="mt-1 list-disc space-y-1 pl-4 text-xs text-ink-muted">
            {reasons.map((reason, idx) => (
              <li key={idx}>{reason}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}

export default function EligibilityPanel({ profile, results = [] }) {
  const [open, setOpen] = useState(false)
  const data = profile || {}
  const filledCount = REQUIRED_FIELDS.filter(({ key }) => isFilled(data[key])).length
  const extras = Object.entries(OPTIONAL_LABELS).filter(([key]) => isFilled(data[key]))
  const percent = (filledCount / REQUIRED_FIELDS.length) * 100

  return (
    <aside
      aria-label="Your eligibility profile"
      className="w-full shrink-0 border-t border-line bg-surface sm:w-80 sm:overflow-y-auto sm:border-l sm:border-t-0"
    >
      <button
        type="button"
        aria-expanded={open}
        aria-controls="profile-body"
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center justify-between gap-2 px-4 py-3 text-left sm:pointer-events-none"
      >
        <span className="flex items-center gap-2 text-sm font-bold text-ink">
          <Icon name="user" className="h-4 w-4" /> Your profile
        </span>
        <span className="flex items-center gap-2 text-xs font-medium text-ink-muted">
          {filledCount} of {REQUIRED_FIELDS.length} details
          <Icon name="chevronDown" className={`h-4 w-4 transition-transform sm:hidden ${open ? 'rotate-180' : ''}`} />
        </span>
      </button>

      <div id="profile-body" className={`px-4 pb-4 ${open ? 'block' : 'hidden'} sm:block`}>
        <div
          role="progressbar"
          aria-valuemin={0}
          aria-valuemax={REQUIRED_FIELDS.length}
          aria-valuenow={filledCount}
          aria-label="Profile details completed"
          className="h-1.5 overflow-hidden rounded-full bg-line"
        >
          <div className="h-full rounded-full bg-success transition-[width] duration-300" style={{ width: `${percent}%` }} />
        </div>

        <dl className="mt-3 space-y-1.5">
          {REQUIRED_FIELDS.map(({ key, label }) => {
            const filled = isFilled(data[key])
            return (
              <div
                key={key}
                className={`flex items-center justify-between gap-3 rounded-lg px-3 py-2 text-xs ${
                  filled ? 'bg-brand-soft' : 'border border-dashed border-line'
                }`}
              >
                <dt className="text-ink-muted">{label}</dt>
                <dd className={filled ? 'font-semibold text-ink' : 'text-ink-faint'}>
                  {filled ? formatValue(data[key]) : 'Not provided yet'}
                </dd>
              </div>
            )
          })}
          {extras.map(([key, label]) => (
            <div key={key} className="flex items-center justify-between gap-3 rounded-lg bg-brand-soft px-3 py-2 text-xs">
              <dt className="text-ink-muted">{label}</dt>
              <dd className="font-semibold text-ink">{formatValue(data[key])}</dd>
            </div>
          ))}
        </dl>

        {filledCount < REQUIRED_FIELDS.length && (
          <p className="mt-3 text-xs text-ink-muted">Answer the assistant's questions to complete your profile.</p>
        )}

        <div className="mt-4 space-y-3" aria-live="polite">
          {results.length > 0 && <h3 className="text-sm font-bold text-ink">Eligibility result</h3>}
          {results.map((result, idx) => (
            <ResultCard key={`${result.scheme_name}-${idx}`} result={result} />
          ))}
          {results.length > 0 && (
            <p className="text-xs text-ink-faint">
              Decided by fixed rules on the details above, not by AI. Always confirm on the official scheme page.
            </p>
          )}
        </div>
      </div>
    </aside>
  )
}
