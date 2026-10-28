import Icon, { LogoMark } from './Icons'
import { PORTAL_URL } from './MessageBubble'

export const SCHEME_COUNT = '2,066'

const FAQ_GROUPS = [
  {
    lang: 'en',
    title: 'English',
    questions: [
      'What schemes are available for SC/ST category?',
      'How do I check my eligibility for a housing scheme?',
      'What documents do I need for a government scheme?',
    ],
  },
  {
    lang: 'hi',
    title: 'हिन्दी',
    questions: [
      'किसानों के लिए कौन सी योजनाएं हैं?',
      'छात्रों के लिए छात्रवृत्ति कैसे प्राप्त करें?',
      'महिलाओं के लिए सरकारी योजनाएं क्या हैं?',
    ],
  },
  {
    lang: 'ta',
    title: 'தமிழ்',
    questions: [
      'விவசாயிகளுக்கான திட்டங்கள் என்ன?',
      'மாணவர்களுக்கான உதவித்தொகை எவ்வாறு பெறுவது?',
      'பெண்களுக்கான அரசு திட்டங்கள் என்ன?',
    ],
  },
]

const STEPS = [
  {
    icon: 'search',
    title: 'Ask',
    text: `Ask about any of ${SCHEME_COUNT} schemes in English, Hindi or Tamil and get an answer with its sources.`,
  },
  {
    icon: 'checkCircle',
    title: 'Check eligibility',
    text: 'Answer five short questions. Fixed rules compare your details with each scheme’s conditions.',
  },
  {
    icon: 'file',
    title: 'Verify documents',
    text: 'Upload a PDF such as an income certificate to fill in your details, then confirm what was read.',
  },
]

const TRUST = [
  {
    icon: 'quote',
    title: 'Answers cite their sources',
    text: 'Every answer lists the schemes it was drawn from. Open a source to see the scheme and section.',
  },
  {
    icon: 'shield',
    title: 'Eligibility is decided by rules, not by AI',
    text: 'The AI searches and explains. A fixed rules engine decides whether you meet each condition, and lists any it could not check.',
  },
  {
    icon: 'file',
    title: 'Your documents are not stored',
    text: 'Uploaded PDFs are deleted as soon as they are read. Only the extracted details (with just the last 4 digits of any ID number) stay in your session, in memory. An AI service reads the document text to pull out those details.',
  },
]

export function Hero({ onStart, widget }) {
  return (
    <section className="hero-bg px-4 py-10 sm:px-6 sm:py-14 lg:py-16">
      <div className="mx-auto grid w-full max-w-6xl grid-cols-1 items-center gap-10 lg:grid-cols-[1fr_440px]">
        <div className="flex flex-col items-start gap-5">
          <span className="inline-flex items-center gap-2 rounded-full bg-white/10 px-3 py-1 text-xs font-medium text-on-hero-muted sm:text-sm">
            <Icon name="database" className="h-4 w-4" />
            {SCHEME_COUNT} schemes from MyScheme.gov.in
          </span>
          <h1 className="text-[2rem] font-extrabold leading-[1.15] text-white sm:text-5xl">
            Find the government schemes you <span className="text-[#ff8fa0]">qualify for</span>
          </h1>
          <p className="max-w-xl text-base text-on-hero-muted sm:text-lg">
            Ask in English, Hindi or Tamil. Get answers that cite the scheme they came from, and check your
            eligibility with fixed rules.
          </p>
          <div className="flex flex-wrap items-center gap-x-6 gap-y-3 pt-1">
            <button
              type="button"
              onClick={onStart}
              className="inline-flex items-center gap-2 rounded-full bg-accent px-6 py-3 text-base font-semibold text-white shadow-raised transition-colors hover:bg-accent-hover"
            >
              Start asking <Icon name="arrowRight" className="h-4 w-4" />
            </button>
            <a href="#how-it-works" className="text-sm font-medium text-on-hero-muted underline-offset-4 hover:text-white hover:underline">
              How it works
            </a>
          </div>
          <p className="text-sm text-on-hero-muted">
            <strong className="font-semibold text-white">{SCHEME_COUNT}</strong> schemes ·{' '}
            <strong className="font-semibold text-white">3</strong> languages
          </p>
        </div>
        {widget}
      </div>
    </section>
  )
}

export function HowItWorks() {
  return (
    <section id="how-it-works" className="bg-surface px-4 py-14 sm:px-6 sm:py-16">
      <div className="mx-auto max-w-6xl">
        <h2 className="text-center text-2xl font-extrabold text-ink sm:text-3xl">How it works</h2>
        <ol className="mt-10 grid grid-cols-1 gap-5 md:grid-cols-3">
          {STEPS.map((step, i) => (
            <li key={step.title} className="rounded-[var(--radius-card)] border border-line bg-surface-2 p-6">
              <div className="flex items-center gap-3">
                <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-brand text-white">
                  <Icon name={step.icon} className="h-5 w-5" />
                </span>
                <span className="text-sm font-semibold text-ink-muted">Step {i + 1}</span>
              </div>
              <h3 className="mt-4 text-lg font-bold text-ink">{step.title}</h3>
              <p className="mt-1.5 text-sm text-ink-muted">{step.text}</p>
            </li>
          ))}
        </ol>
      </div>
    </section>
  )
}

export function Trust() {
  return (
    <section className="bg-bg px-4 py-14 sm:px-6 sm:py-16" aria-labelledby="trust-heading">
      <div className="mx-auto max-w-6xl">
        <h2 id="trust-heading" className="text-center text-2xl font-extrabold text-ink sm:text-3xl">
          Why you can trust the answers
        </h2>
        <div className="mt-10 grid grid-cols-1 gap-5 md:grid-cols-3">
          {TRUST.map((item) => (
            <div key={item.title} className="rounded-[var(--radius-card)] border border-line bg-surface p-6 shadow-card">
              <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-success-soft text-success">
                <Icon name={item.icon} className="h-5 w-5" />
              </span>
              <h3 className="mt-4 text-base font-bold text-ink">{item.title}</h3>
              <p className="mt-1.5 text-sm text-ink-muted">{item.text}</p>
            </div>
          ))}
        </div>
        <p className="mx-auto mt-6 max-w-3xl text-center text-sm text-ink-muted">
          Your questions, and the scheme text retrieved for them, are processed by external AI services (Google Gemini
          and Groq) to write the answers. Uploaded documents are read by an AI service to extract fields, then deleted;
          only the last 4 digits of an ID number are kept.
        </p>
      </div>
    </section>
  )
}

export function Faq({ onPick }) {
  return (
    <section className="bg-surface px-4 py-14 sm:px-6 sm:py-16" aria-labelledby="faq-heading">
      <div className="mx-auto max-w-6xl">
        <h2 id="faq-heading" className="text-center text-2xl font-extrabold text-ink sm:text-3xl">
          Common questions
        </h2>
        <p className="mt-2 text-center text-sm text-ink-muted sm:text-base">Pick one to get an answer in that language.</p>
        <div className="mt-10 grid grid-cols-1 gap-8 md:grid-cols-3 md:gap-5">
          {FAQ_GROUPS.map((group) => (
            <div key={group.lang}>
              <h3 lang={group.lang} className="mb-3 h-6 text-sm font-bold leading-6 text-ink-muted">
                {group.title}
              </h3>
              <ul className="space-y-3">
                {group.questions.map((question) => (
                  <li key={question}>
                    <button
                      type="button"
                      lang={group.lang}
                      onClick={() => onPick({ lang: group.lang, question })}
                      className="group flex w-full items-center justify-between gap-3 rounded-xl border border-line bg-surface-2 px-4 py-3.5 text-left text-sm font-medium text-ink shadow-card transition-colors hover:border-ink-faint hover:bg-surface"
                    >
                      <span>{question}</span>
                      <Icon
                        name="arrowRight"
                        className="h-4 w-4 shrink-0 text-ink-faint transition-transform group-hover:translate-x-0.5 group-hover:text-ink"
                      />
                    </button>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}

export function Footer() {
  return (
    <footer className="bg-brand px-4 py-10 text-on-hero-muted sm:px-6">
      <div className="mx-auto flex max-w-6xl flex-col gap-6 md:flex-row md:items-start md:justify-between">
        <div className="max-w-xl">
          <div className="flex items-center gap-2.5">
            <LogoMark className="h-8 w-8 rounded-lg" />
            <span className="text-base font-bold text-white">SchemeBot</span>
          </div>
          <p className="mt-3 text-sm">
            Answers are drawn from scheme data published on{' '}
            <a href={PORTAL_URL} target="_blank" rel="noopener noreferrer" className="font-medium text-white underline underline-offset-2">
              MyScheme.gov.in
            </a>{' '}
            ({SCHEME_COUNT} schemes).
          </p>
          <p className="mt-2 text-sm">
            SchemeBot is not an official government service. Information may be incomplete or out of date, so
            confirm details on the official portal before you apply.
          </p>
        </div>
        <a
          href={PORTAL_URL}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-2 self-start rounded-full border border-white/30 px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-white/10"
        >
          Official portal: myscheme.gov.in <Icon name="external" className="h-4 w-4" />
        </a>
      </div>
    </footer>
  )
}
