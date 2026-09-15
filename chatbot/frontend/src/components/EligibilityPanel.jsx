const FIELD_LABELS = {
  age: 'Age',
  gender: 'Gender',
  state: 'State',
  income_annual: 'Annual income',
  category: 'Category',
  is_student: 'Student',
  is_employed: 'Employed',
  occupation: 'Occupation',
  disability: 'Disability',
  is_ex_serviceman: 'Ex-serviceman',
}

function formatValue(value) {
  if (value === null || value === undefined) return null
  if (typeof value === 'boolean') return value ? 'Yes' : 'No'
  return String(value)
}

export default function EligibilityPanel({ profile, result }) {
  const filledEntries = Object.entries(profile || {}).filter(
    ([, value]) => value !== null && value !== undefined
  )

  return (
    <aside className="w-full shrink-0 border-t border-border bg-surface sm:w-72 sm:border-l sm:border-t-0">
      <div className="flex items-center gap-2 bg-primary px-4 py-3">
        <span className="flex h-7 w-7 items-center justify-center rounded-full bg-white/20 text-sm">
          👤
        </span>
        <h3 className="text-sm font-bold text-white">Your Profile</h3>
      </div>

      <div className="p-4">
      {filledEntries.length === 0 ? (
        <div className="mt-4 flex flex-col items-center gap-2 rounded-lg border border-dashed border-border p-4 text-center">
          <span className="text-2xl">✅</span>
          <p className="text-xs text-text-secondary">
            Answer the chatbot's questions to build your eligibility profile.
          </p>
        </div>
      ) : (
        <dl className="mt-3 space-y-1.5">
          {filledEntries.map(([key, value]) => (
            <div
              key={key}
              className="flex items-center justify-between rounded-md bg-primary-light px-2.5 py-1.5 text-xs"
            >
              <dt className="text-text-secondary">{FIELD_LABELS[key] || key}</dt>
              <dd className="font-semibold text-text-primary">{formatValue(value)}</dd>
            </div>
          ))}
        </dl>
      )}

      {result && (
        <div
          className={`mt-4 rounded-xl p-3 ${
            result.eligible ? 'bg-success-light' : 'bg-danger-light'
          }`}
        >
          <p
            className={`text-base font-bold ${
              result.eligible ? 'text-success' : 'text-danger'
            }`}
          >
            {result.eligible ? '✅ Eligible' : '❌ Not eligible'}
          </p>
          {result.reasons && result.reasons.length > 0 && (
            <ul className="mt-2 list-disc space-y-1 pl-4 text-xs text-text-secondary">
              {result.reasons.map((reason, idx) => (
                <li key={idx}>{reason}</li>
              ))}
            </ul>
          )}
        </div>
      )}
      </div>
    </aside>
  )
}
