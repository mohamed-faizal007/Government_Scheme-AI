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
    <aside className="w-full shrink-0 border-t border-slate-200 bg-white p-4 sm:w-72 sm:border-l sm:border-t-0">
      <h3 className="text-sm font-semibold text-slate-700">Eligibility check</h3>

      {filledEntries.length === 0 ? (
        <p className="mt-2 text-xs text-slate-400">
          Answer the assistant's questions to build your profile.
        </p>
      ) : (
        <dl className="mt-3 space-y-2">
          {filledEntries.map(([key, value]) => (
            <div key={key} className="flex justify-between text-xs">
              <dt className="text-slate-500">{FIELD_LABELS[key] || key}</dt>
              <dd className="font-medium text-slate-800">{formatValue(value)}</dd>
            </div>
          ))}
        </dl>
      )}

      {result && (
        <div className="mt-4 rounded-md border border-slate-200 p-3">
          <p
            className={`text-sm font-semibold ${
              result.eligible ? 'text-green-600' : 'text-red-600'
            }`}
          >
            {result.eligible ? '✅ Eligible' : '❌ Not eligible'}
          </p>
          {result.reasons && result.reasons.length > 0 && (
            <ul className="mt-2 list-disc space-y-1 pl-4 text-xs text-slate-600">
              {result.reasons.map((reason, idx) => (
                <li key={idx}>{reason}</li>
              ))}
            </ul>
          )}
        </div>
      )}
    </aside>
  )
}
