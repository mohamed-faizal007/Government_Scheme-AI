const SECTION_LABELS = {
  description: 'Overview',
  overview: 'Overview',
  benefits: 'Benefits',
  eligibility: 'Eligibility',
  application: 'How to apply',
  documents: 'Documents',
  faq: 'FAQ',
}

export function sectionLabel(section) {
  if (!section) return ''
  const key = String(section).toLowerCase()
  if (SECTION_LABELS[key]) return SECTION_LABELS[key]
  const spaced = key.replace(/[_-]+/g, ' ')
  return spaced.charAt(0).toUpperCase() + spaced.slice(1)
}

