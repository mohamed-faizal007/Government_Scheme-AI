import axios from 'axios'
import { useCallback, useEffect, useRef, useState } from 'react'
import ChatWindow from './components/ChatWindow'
import ConnectionBanner from './components/ConnectionBanner'
import EligibilityPanel from './components/EligibilityPanel'
import HeroChatWidget from './components/HeroChatWidget'
import InputBar from './components/InputBar'
import { useChatSocket } from './hooks/useChatSocket'
import { API_BASE, LANGUAGES } from './utils/api'
import { getSessionId, resetSessionId } from './utils/session'

let messageIdCounter = 0
function nextId() {
  messageIdCounter += 1
  return messageIdCounter
}

const INITIAL_WIDGET_MESSAGES = () => [
  {
    id: nextId(),
    role: 'assistant',
    text: '👋 Hello! I can help you find government schemes you qualify for. Ask me anything in English, Hindi, or Tamil.',
  },
  { id: nextId(), role: 'user', text: 'What schemes are available for farmers?' },
  {
    id: nextId(),
    role: 'assistant',
    text: 'I found schemes like Beej Swalamban Yojna (50% seed subsidy) and CM Krishi Rinn Yojana (zero interest loans). Want to check your eligibility?',
  },
]

const FAQS = [
  { lang: 'en', badge: 'EN', border: 'border-primary', question: 'What schemes are available for SC/ST category?' },
  { lang: 'en', badge: 'EN', border: 'border-primary', question: 'How do I check my eligibility for a housing scheme?' },
  { lang: 'en', badge: 'EN', border: 'border-primary', question: 'What documents do I need for a government scheme?' },
  { lang: 'hi', badge: 'हि', border: 'border-amber', question: 'किसानों के लिए कौन सी योजनाएं हैं?' },
  { lang: 'hi', badge: 'हि', border: 'border-amber', question: 'छात्रों के लिए छात्रवृत्ति कैसे प्राप्त करें?' },
  { lang: 'hi', badge: 'हि', border: 'border-amber', question: 'महिलाओं के लिए सरकारी योजनाएं क्या हैं?' },
  { lang: 'ta', badge: 'த', border: 'border-danger', question: 'விவசாயிகளுக்கான திட்டங்கள் என்ன?' },
  { lang: 'ta', badge: 'த', border: 'border-danger', question: 'மாணவர்களுக்கான உதவித்தொகை எவ்வாறு பெறுவது?' },
  { lang: 'ta', badge: 'த', border: 'border-danger', question: 'பெண்களுக்கான அரசு திட்டங்கள் என்ன?' },
]

const FAQ_BADGE_TEXT = {
  en: 'text-primary',
  hi: 'text-amber',
  ta: 'text-danger',
}

export default function App() {
  const [sessionId, setSessionId] = useState(() => getSessionId())
  const [language, setLanguage] = useState('en')
  const [messages, setMessages] = useState([])
  const [isTyping, setIsTyping] = useState(false)
  const [profile, setProfile] = useState({})
  const [eligibilityResults, setEligibilityResults] = useState([])
  const [eligibilityMode, setEligibilityMode] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [mainChatOpen, setMainChatOpen] = useState(false)
  const [prefill, setPrefill] = useState(null)

  const [widgetMessages, setWidgetMessages] = useState(INITIAL_WIDGET_MESSAGES)
  const [widgetInput, setWidgetInput] = useState('')
  const [widgetTyping, setWidgetTyping] = useState(false)
  const [widgetMinimized, setWidgetMinimized] = useState(false)
  const [widgetExpanded, setWidgetExpanded] = useState(false)

  // Requests are answered in the order they're sent over the single shared
  // socket, so a FIFO queue tells us which surface (main chat vs widget)
  // each incoming response belongs to.
  const pendingTargetRef = useRef([])

  const handleIncoming = useCallback((data) => {
    const target = pendingTargetRef.current.shift() || 'main'

    if (target === 'widget') {
      setWidgetTyping(false)
      if (data.error) {
        setWidgetMessages((prev) => [...prev, { id: nextId(), role: 'assistant', text: data.error }])
        return
      }
      setWidgetMessages((prev) => [
        ...prev,
        {
          id: nextId(),
          role: 'assistant',
          text: data.answer,
          confidence: data.confidence,
          sources: data.sources || [],
          intent: data.intent,
        },
      ])
      return
    }

    setIsTyping(false)

    if (data.error) {
      setMessages((prev) => [
        ...prev,
        { id: nextId(), role: 'assistant', text: data.error, confidence: 'low', sources: [] },
      ])
      return
    }

    setMessages((prev) => [
      ...prev,
      {
        id: nextId(),
        role: 'assistant',
        text: data.answer,
        confidence: data.confidence,
        sources: data.sources || [],
        intent: data.intent,
      },
    ])
    setProfile(data.profile || {})
    if (data.eligibility_results && data.eligibility_results.length > 0) {
      setEligibilityResults(data.eligibility_results)
    }
    if (data.intent === 'eligibility_check') {
      setEligibilityMode(true)
    }
  }, [])

  const { connected, sendMessage } = useChatSocket({ sessionId, onMessage: handleIncoming })

  const handleSend = (text) => {
    setMessages((prev) => [...prev, { id: nextId(), role: 'user', text }])
    setIsTyping(true)
    pendingTargetRef.current.push('main')
    const sent = sendMessage(text, language)
    if (!sent) {
      pendingTargetRef.current.pop()
      setIsTyping(false)
      setMessages((prev) => [
        ...prev,
        {
          id: nextId(),
          role: 'assistant',
          text: 'Not connected to the server. Please wait for reconnection and try again.',
          confidence: 'low',
          sources: [],
        },
      ])
    }
  }

  const sendWidgetMessage = (text) => {
    const trimmed = (text || '').trim()
    if (!trimmed) return
    setWidgetMessages((prev) => [...prev, { id: nextId(), role: 'user', text: trimmed }])
    setWidgetInput('')
    setWidgetTyping(true)
    pendingTargetRef.current.push('widget')
    const sent = sendMessage(trimmed, language)
    if (!sent) {
      pendingTargetRef.current.pop()
      setWidgetTyping(false)
      setWidgetMessages((prev) => [
        ...prev,
        { id: nextId(), role: 'assistant', text: 'Not connected to the server. Please wait for reconnection and try again.' },
      ])
    }
  }

  const handleFileSelect = async (file) => {
    setUploading(true)
    setMessages((prev) => [
      ...prev,
      { id: nextId(), role: 'user', text: `📎 Uploaded: ${file.name}` },
    ])
    try {
      const formData = new FormData()
      formData.append('file', file)
      formData.append('session_id', sessionId)
      const { data } = await axios.post(`${API_BASE}/document/upload`, formData)

      setProfile(data.profile || {})
      const filled = [...data.high_confidence_fills, ...data.needs_confirmation]
      const summary =
        filled.length > 0
          ? `I read your document and updated: ${filled.join(', ')}.${
              data.needs_confirmation.length
                ? ` Please confirm: ${data.needs_confirmation.join(', ')}.`
                : ''
            }`
          : "I couldn't confidently extract any fields from that document."
      setMessages((prev) => [
        ...prev,
        { id: nextId(), role: 'assistant', text: summary, confidence: 'medium', sources: [] },
      ])
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        {
          id: nextId(),
          role: 'assistant',
          text: `Sorry, I couldn't process that document (${err.response?.data?.detail || err.message}).`,
          confidence: 'low',
          sources: [],
        },
      ])
    } finally {
      setUploading(false)
    }
  }

  const handleWidgetFileSelect = async (file) => {
    setWidgetMessages((prev) => [...prev, { id: nextId(), role: 'user', text: `📎 Uploaded: ${file.name}` }])
    try {
      const formData = new FormData()
      formData.append('file', file)
      formData.append('session_id', sessionId)
      const { data } = await axios.post(`${API_BASE}/document/upload`, formData)

      setProfile(data.profile || {})
      const filled = [...data.high_confidence_fills, ...data.needs_confirmation]
      const summary =
        filled.length > 0
          ? `I read your document and updated: ${filled.join(', ')}.${
              data.needs_confirmation.length
                ? ` Please confirm: ${data.needs_confirmation.join(', ')}.`
                : ''
            }`
          : "I couldn't confidently extract any fields from that document."
      setWidgetMessages((prev) => [...prev, { id: nextId(), role: 'assistant', text: summary }])
    } catch (err) {
      setWidgetMessages((prev) => [
        ...prev,
        { id: nextId(), role: 'assistant', text: `Sorry, I couldn't process that document (${err.response?.data?.detail || err.message}).` },
      ])
    }
  }

  const handleNewConversation = () => {
    setSessionId(resetSessionId())
    setMessages([])
    setProfile({})
    setEligibilityMode(false)
    setEligibilityResults([])
    setIsTyping(false)
    setMainChatOpen(false)
  }

  const handleStartAsking = () => {
    setMainChatOpen(true)
  }

  useEffect(() => {
    if (mainChatOpen) {
      document.getElementById('chat-input')?.querySelector('textarea')?.focus()
    }
  }, [mainChatOpen])

  const handleWidgetRefresh = () => {
    setWidgetMessages(INITIAL_WIDGET_MESSAGES())
    setWidgetInput('')
    setWidgetTyping(false)
  }

  const handleFaqClick = (faq) => {
    setLanguage(faq.lang)
    const isDesktop = typeof window !== 'undefined' && window.matchMedia('(min-width: 1024px)').matches

    if (isDesktop) {
      setWidgetMinimized(false)
      sendWidgetMessage(faq.question)
      requestAnimationFrame(() => {
        document.getElementById('hero-chat-widget')?.scrollIntoView({ behavior: 'smooth', block: 'center' })
      })
    } else {
      setMainChatOpen(true)
      setPrefill({ text: faq.question, id: nextId() })
      requestAnimationFrame(() => {
        document.getElementById('chat-input')?.scrollIntoView({ behavior: 'smooth', block: 'center' })
      })
    }
  }

  const latestEligibility = eligibilityResults[0]
    ? { eligible: eligibilityResults[0].eligible, reasons: eligibilityResults[0].reasons }
    : null

  const inChat = messages.length > 0 || mainChatOpen

  return (
    <div className="w-full bg-bg">
      <header className="fixed inset-x-0 top-0 z-40 flex h-16 items-center justify-between border-b border-primary-hover bg-primary px-4 py-3">
        <div className="flex items-center gap-3">
          <span className="text-2xl">🏛️</span>
          <span className="font-display text-base font-bold text-white">SchemeBot</span>
          <button
            type="button"
            onClick={handleNewConversation}
            className="rounded-full border border-white/40 px-3 py-1 text-xs font-medium text-white transition-colors hover:bg-white/10"
          >
            New Conversation
          </button>
        </div>
        <div className="flex gap-1">
          {LANGUAGES.map((lang) => (
            <button
              key={lang.code}
              type="button"
              onClick={() => setLanguage(lang.code)}
              className={`rounded-full px-3 py-1 text-xs font-medium transition-colors ${
                language === lang.code
                  ? 'bg-accent text-white'
                  : 'bg-white/20 text-white hover:bg-white/30'
              }`}
            >
              {lang.label}
            </button>
          ))}
        </div>
      </header>

      <div className="pt-16">
        <ConnectionBanner connected={connected} />

        <div
          className={`landing-transition overflow-hidden ${
            inChat ? 'max-h-0 opacity-0' : 'max-h-[6000px] opacity-100'
          }`}
        >
        <section className="hero-section relative flex min-h-[600px] items-center px-4 py-12 sm:py-16">
          <div className="hero-grid-overlay" />
          <div className="hero-blob hero-blob-1" />
          <div className="hero-blob hero-blob-2" />
          <div className="hero-blob hero-blob-3" />
          <div className="hero-blob hero-blob-4" />

          <div className="relative mx-auto grid max-w-6xl grid-cols-1 items-center gap-12 lg:grid-cols-2">
            {/* Left column */}
            <div className="flex flex-col items-start gap-6 text-left">
              <span className="inline-flex items-center gap-1.5 rounded-full bg-amber-light px-3 py-1.5 text-xs font-semibold text-amber sm:text-sm">
                🇮🇳 Powered by AI · 2,066 Schemes
              </span>

              <h1 className="font-display text-3xl font-extrabold leading-tight text-white sm:text-5xl">
                Find Government
                <br />
                Schemes You
                <br />
                <span className="text-accent">Qualify For</span>
              </h1>

              <p className="max-w-xl text-base text-white/80 sm:text-lg">
                Ask in English, Hindi, or Tamil. Get instant answers about eligibility, benefits, and
                documents — powered by 2,066 real government scheme PDFs.
              </p>

              <div className="flex w-full max-w-md flex-wrap items-start gap-6 py-2 sm:gap-10">
                <div>
                  <div className="text-2xl font-extrabold text-amber sm:text-3xl">2,066+</div>
                  <div className="text-xs text-white/60 sm:text-sm">Schemes</div>
                </div>
                <div>
                  <div className="text-2xl font-extrabold text-amber sm:text-3xl">3</div>
                  <div className="text-xs text-white/60 sm:text-sm">Languages</div>
                </div>
                <div>
                  <div className="text-2xl font-extrabold text-amber sm:text-3xl">Instant</div>
                  <div className="text-xs text-white/60 sm:text-sm">Answers</div>
                </div>
              </div>

              <div className="flex flex-wrap gap-3">
                <button
                  type="button"
                  onClick={handleStartAsking}
                  className="rounded-full bg-accent px-6 py-3 text-sm font-semibold text-white shadow-card transition-colors hover:bg-accent-hover sm:text-base"
                >
                  Start Asking →
                </button>
                <button
                  type="button"
                  onClick={() =>
                    document.getElementById('how-it-works')?.scrollIntoView({ behavior: 'smooth' })
                  }
                  className="rounded-full border border-white/40 px-6 py-3 text-sm font-semibold text-white transition-colors hover:bg-white/10 sm:text-base"
                >
                  See How It Works
                </button>
              </div>
            </div>

            {/* Right column: floating chat widget */}
            <HeroChatWidget
              messages={widgetMessages}
              input={widgetInput}
              onInputChange={setWidgetInput}
              onSend={sendWidgetMessage}
              typing={widgetTyping}
              minimized={widgetMinimized}
              onMinimize={() => setWidgetMinimized(true)}
              onRestore={() => setWidgetMinimized(false)}
              expanded={widgetExpanded}
              onExpand={() => setWidgetExpanded(true)}
              onCollapseExpand={() => setWidgetExpanded(false)}
              onRefresh={handleWidgetRefresh}
              onFileSelect={handleWidgetFileSelect}
              language={language}
              connected={connected}
            />
          </div>
        </section>

        <section id="how-it-works" className="bg-white px-4 py-16">
          <div className="mx-auto max-w-6xl">
            <h2 className="mb-10 text-center font-display text-2xl font-extrabold text-text-primary sm:text-3xl">
              How It Works
            </h2>
            <div className="grid grid-cols-1 gap-6 sm:grid-cols-3">
              {[
                {
                  icon: '🔍',
                  title: 'Smart Scheme Search',
                  desc: 'Search across 2,066 government schemes in English, Hindi, or Tamil. Get cited, grounded answers — never hallucinated.',
                },
                {
                  icon: '✅',
                  title: 'Eligibility Check',
                  desc: 'Answer a few questions and get a deterministic eligibility result. Our rules engine — not an AI — makes the decision.',
                },
                {
                  icon: '📄',
                  title: 'Document Verification',
                  desc: 'Upload your income certificate or Aadhaar card. We extract your details and auto-fill your eligibility profile.',
                },
              ].map((card) => (
                <div
                  key={card.title}
                  className="feature-card rounded-xl bg-surface px-6 py-8 text-center shadow-card"
                >
                  <div className="mb-4 text-4xl">{card.icon}</div>
                  <h3 className="mb-2 font-display text-lg font-bold text-text-primary">{card.title}</h3>
                  <p className="text-sm text-text-secondary">{card.desc}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section className="px-4 py-16" style={{ backgroundColor: '#F8FAFF' }}>
          <div className="mx-auto max-w-5xl">
            <h2 className="text-center font-display text-2xl font-extrabold text-primary sm:text-3xl">
              Frequently Asked Questions
            </h2>
            <p className="mt-2 text-center text-sm text-text-secondary sm:text-base">
              Click any question to get an instant answer
            </p>

            <div className="mt-10 grid grid-cols-1 gap-4 sm:grid-cols-3">
              {FAQS.map((faq) => (
                <button
                  key={faq.question}
                  type="button"
                  onClick={() => handleFaqClick(faq)}
                  className={`group flex items-center justify-between gap-3 rounded-xl border-l-[3px] ${faq.border} bg-white px-4 py-4 text-left shadow-card transition-colors hover:border-l-4`}
                >
                  <div className="min-w-0 flex-1">
                    <span
                      className={`mb-1 inline-block rounded-full bg-bg px-2 py-0.5 text-[10px] font-bold ${FAQ_BADGE_TEXT[faq.lang]}`}
                    >
                      {faq.badge}
                    </span>
                    <p className="text-sm font-medium text-slate-800">{faq.question}</p>
                  </div>
                  <span className="shrink-0 text-slate-400 transition-transform group-hover:translate-x-1">→</span>
                </button>
              ))}
            </div>
          </div>
        </section>

        <footer className="flex flex-col items-center justify-between gap-2 bg-primary-hover px-4 py-5 text-xs text-white/70 sm:flex-row sm:px-8">
          <span>SchemeBot © 2026 — Built on 2,066 real government scheme PDFs</span>
          <span>Data from MyScheme.gov.in</span>
        </footer>
        </div>

        {inChat && (
          <div className="flex h-[calc(100vh-4rem)] min-h-0 flex-col sm:flex-row">
            <div className="flex min-h-0 flex-1 flex-col">
              <ChatWindow messages={messages} isTyping={isTyping || uploading} onExampleClick={handleSend} />
              <div id="chat-input">
                <InputBar
                  language={language}
                  onSend={handleSend}
                  onFileSelect={handleFileSelect}
                  disabled={!connected || uploading}
                  prefill={prefill}
                />
              </div>
            </div>

            {eligibilityMode && <EligibilityPanel profile={profile} result={latestEligibility} />}
          </div>
        )}
      </div>
    </div>
  )
}
