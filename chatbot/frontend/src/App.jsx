import axios from 'axios'
import { useCallback, useMemo, useState } from 'react'
import ChatWindow from './components/ChatWindow'
import ConnectionBanner from './components/ConnectionBanner'
import EligibilityPanel from './components/EligibilityPanel'
import InputBar from './components/InputBar'
import { useChatSocket } from './hooks/useChatSocket'
import { API_BASE, LANGUAGES } from './utils/api'
import { getSessionId } from './utils/session'

const FEATURE_PILLS = [
  { icon: '🔍', label: 'Scheme Search' },
  { icon: '✅', label: 'Eligibility Check' },
  { icon: '📄', label: 'Document Verify' },
]

let messageIdCounter = 0
function nextId() {
  messageIdCounter += 1
  return messageIdCounter
}

export default function App() {
  const sessionId = useMemo(() => getSessionId(), [])
  const [language, setLanguage] = useState('en')
  const [messages, setMessages] = useState([])
  const [isTyping, setIsTyping] = useState(false)
  const [profile, setProfile] = useState({})
  const [eligibilityResults, setEligibilityResults] = useState([])
  const [eligibilityMode, setEligibilityMode] = useState(false)
  const [uploading, setUploading] = useState(false)

  const handleIncoming = useCallback((data) => {
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
    const sent = sendMessage(text, language)
    if (!sent) {
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

  const latestEligibility = eligibilityResults[0]
    ? { eligible: eligibilityResults[0].eligible, reasons: eligibilityResults[0].reasons }
    : null

  const inChat = messages.length > 0

  return (
    <div className="flex h-screen w-screen flex-col bg-bg">
      <header className="flex items-center justify-between border-b border-primary-hover bg-primary px-4 py-3">
        <div className="flex items-center gap-2">
          <span className="text-2xl">🏛️</span>
          <span className="font-display text-base font-bold text-white">SchemeBot</span>
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

      <ConnectionBanner connected={connected} />

      <div
        className={`landing-transition overflow-hidden ${
          inChat ? 'max-h-0 opacity-0' : 'max-h-[600px] opacity-100'
        }`}
      >
        <div className="bg-gradient-to-b from-primary to-[#1a1a2e] px-4 py-12">
          <div className="mx-auto flex max-w-3xl flex-col items-center gap-5 text-center">
            <span className="text-5xl">🏛️</span>
            <h1 className="font-display text-3xl font-extrabold text-white sm:text-4xl">
              Find Government Schemes You Qualify For
            </h1>
            <p className="text-sm text-white/80 sm:text-base">
              Ask in English, Hindi, or Tamil — get instant, cited answers.
            </p>

            <div className="flex flex-wrap justify-center gap-2">
              {FEATURE_PILLS.map((pill) => (
                <span
                  key={pill.label}
                  className="flex items-center gap-1.5 rounded-full border border-white/30 bg-white/15 px-3 py-1.5 text-sm font-medium text-white"
                >
                  <span>{pill.icon}</span>
                  {pill.label}
                </span>
              ))}
            </div>

            <button
              type="button"
              onClick={() => document.getElementById('chat-input')?.querySelector('textarea')?.focus()}
              className="mt-2 rounded-full bg-accent px-6 py-2.5 text-sm font-semibold text-white shadow-card transition-colors hover:bg-accent-hover"
            >
              Start Asking →
            </button>
          </div>
        </div>

        <div className="mx-auto max-w-3xl px-4 py-6">
          <div className="grid w-full grid-cols-1 gap-2 sm:grid-cols-3">
            {[
              'What schemes are available for farmers?',
              'Am I eligible for a housing subsidy?',
              'What documents do I need for SC/ST schemes?',
            ].map((prompt) => (
              <button
                key={prompt}
                type="button"
                onClick={() => handleSend(prompt)}
                className="rounded-lg border-l-4 border-primary bg-surface px-3 py-2 text-left text-xs text-text-primary shadow-card transition-shadow hover:shadow-md"
              >
                {prompt}
              </button>
            ))}
          </div>
        </div>
      </div>

      <div className="flex min-h-0 flex-1 flex-col sm:flex-row">
        <div className="flex min-h-0 flex-1 flex-col">
          <ChatWindow messages={messages} isTyping={isTyping || uploading} onExampleClick={handleSend} />
          <div id="chat-input">
            <InputBar
              language={language}
              onSend={handleSend}
              onFileSelect={handleFileSelect}
              disabled={!connected || uploading}
            />
          </div>
        </div>

        {eligibilityMode && <EligibilityPanel profile={profile} result={latestEligibility} />}
      </div>
    </div>
  )
}
