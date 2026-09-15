import axios from 'axios'
import { useCallback, useMemo, useState } from 'react'
import ChatWindow from './components/ChatWindow'
import ConnectionBanner from './components/ConnectionBanner'
import EligibilityPanel from './components/EligibilityPanel'
import InputBar from './components/InputBar'
import { useChatSocket } from './hooks/useChatSocket'
import { API_BASE } from './utils/api'
import { getSessionId } from './utils/session'

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

  return (
    <div className="flex h-screen w-screen flex-col bg-slate-50">
      <header className="border-b border-slate-200 bg-white px-4 py-3">
        <h1 className="text-base font-semibold text-slate-800">Government Scheme Assistant</h1>
        <p className="text-xs text-slate-500">
          Ask about scheme eligibility, benefits, and required documents.
        </p>
      </header>

      <ConnectionBanner connected={connected} />

      <div className="flex min-h-0 flex-1 flex-col sm:flex-row">
        <div className="flex min-h-0 flex-1 flex-col">
          <ChatWindow messages={messages} isTyping={isTyping || uploading} />
          <InputBar
            language={language}
            onLanguageChange={setLanguage}
            onSend={handleSend}
            onFileSelect={handleFileSelect}
            disabled={!connected || uploading}
          />
        </div>

        {eligibilityMode && <EligibilityPanel profile={profile} result={latestEligibility} />}
      </div>
    </div>
  )
}
