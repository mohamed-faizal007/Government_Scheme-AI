import axios from 'axios'
import { useCallback, useEffect, useRef, useState } from 'react'
import ChatWindow from './components/ChatWindow'
import ConnectionBanner from './components/ConnectionBanner'
import EligibilityPanel from './components/EligibilityPanel'
import Header from './components/Header'
import HeroChatWidget from './components/HeroChatWidget'
import InputBar from './components/InputBar'
import { Faq, Footer, Hero, HowItWorks, Trust } from './components/Landing'
import { useChatSocket } from './hooks/useChatSocket'
import { useTheme } from './hooks/useTheme'
import { API_BASE } from './utils/api'
import { getSessionId, resetSessionId } from './utils/session'

let messageIdCounter = 0
function nextId() {
  messageIdCounter += 1
  return messageIdCounter
}

const NOT_CONNECTED_TEXT = 'Not connected to the server. Please wait for reconnection and try again.'
const DISCONNECTED_TEXT = 'The connection dropped before I could answer. Please try again.'

const INITIAL_WIDGET_MESSAGES = () => [
  {
    id: nextId(),
    role: 'assistant',
    noFeedback: true,
    text: 'Hello! I can help you find government schemes you may qualify for. Ask me anything in English, Hindi or Tamil.',
  },
]

function errorMessage(text, retryText) {
  return { id: nextId(), role: 'assistant', kind: 'error', text, retryText }
}

function summarizeUpload(data) {
  const filled = [...data.high_confidence_fills, ...data.needs_confirmation]
  if (filled.length === 0) return "I couldn't confidently extract any fields from that document."
  return `I read your document and updated: ${filled.join(', ')}.${
    data.needs_confirmation.length ? ` Please confirm: ${data.needs_confirmation.join(', ')}.` : ''
  }`
}

export default function App() {
  const { theme, toggle: toggleTheme } = useTheme()
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
  const [widgetTyping, setWidgetTyping] = useState(false)
  const [widgetUploading, setWidgetUploading] = useState(false)
  const [widgetMinimized, setWidgetMinimized] = useState(false)
  const [widgetExpanded, setWidgetExpanded] = useState(false)

  // Requests are answered in the order they're sent over the single shared
  // socket, so a FIFO queue tells us which surface (main chat vs widget)
  // each incoming response belongs to.
  const pendingRef = useRef([])

  const handleIncoming = useCallback((data) => {
    const { target } = pendingRef.current.shift() || { target: 'main' }

    if (target === 'widget') {
      setWidgetTyping(false)
      if (data.error) {
        setWidgetMessages((prev) => [...prev, errorMessage(data.error)])
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
      setMessages((prev) => [...prev, errorMessage(data.error)])
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

  // A dropped socket never answers what was in flight, so surface each as a
  // retryable error instead of leaving the typing indicator spinning.
  const handleDisconnect = useCallback(() => {
    const dropped = pendingRef.current.splice(0)
    if (dropped.length === 0) return
    if (dropped.some((p) => p.target === 'main')) {
      const last = dropped.filter((p) => p.target === 'main').pop()
      setIsTyping(false)
      setMessages((prev) => [...prev, errorMessage(DISCONNECTED_TEXT, last.text)])
    }
    if (dropped.some((p) => p.target === 'widget')) {
      const last = dropped.filter((p) => p.target === 'widget').pop()
      setWidgetTyping(false)
      setWidgetMessages((prev) => [...prev, errorMessage(DISCONNECTED_TEXT, last.text)])
    }
  }, [])

  const { connected, sendMessage } = useChatSocket({
    sessionId,
    onMessage: handleIncoming,
    onDisconnect: handleDisconnect,
  })

  // Sends text on the main chat without adding a user bubble (used by send and retry).
  const dispatchMain = (text, source = 'typed') => {
    setIsTyping(true)
    pendingRef.current.push({ target: 'main', text })
    if (!sendMessage(text, language, source)) {
      pendingRef.current.pop()
      setIsTyping(false)
      setMessages((prev) => [...prev, errorMessage(NOT_CONNECTED_TEXT, text)])
    }
  }

  const dispatchWidget = (text, source = 'typed') => {
    setWidgetTyping(true)
    pendingRef.current.push({ target: 'widget', text })
    if (!sendMessage(text, language, source)) {
      pendingRef.current.pop()
      setWidgetTyping(false)
      setWidgetMessages((prev) => [...prev, errorMessage(NOT_CONNECTED_TEXT, text)])
    }
  }

  // source is "button" for UI-generated text (suggestions, "View details"): the backend then
  // answers in the pill language instead of detecting the language of text the user didn't type.
  const handleSend = (text, source = 'typed') => {
    setMessages((prev) => [...prev, { id: nextId(), role: 'user', text }])
    dispatchMain(text, source)
  }

  const sendWidgetMessage = (text, source = 'typed') => {
    const trimmed = (text || '').trim()
    if (!trimmed) return
    setWidgetMessages((prev) => [...prev, { id: nextId(), role: 'user', text: trimmed }])
    dispatchWidget(trimmed, source)
  }

  const handleRetry = (text, errorId) => {
    setMessages((prev) => prev.filter((m) => m.id !== errorId))
    dispatchMain(text)
  }

  const handleWidgetRetry = (text, errorId) => {
    setWidgetMessages((prev) => prev.filter((m) => m.id !== errorId))
    dispatchWidget(text)
  }

  const uploadDocument = async (file, { setList, setBusy, withMeta }) => {
    setBusy(true)
    setList((prev) => [...prev, { id: nextId(), role: 'user', text: `Uploaded: ${file.name}` }])
    try {
      const formData = new FormData()
      formData.append('file', file)
      formData.append('session_id', sessionId)
      const { data } = await axios.post(`${API_BASE}/document/upload`, formData)

      setProfile(data.profile || {})
      setList((prev) => [
        ...prev,
        { id: nextId(), role: 'assistant', text: summarizeUpload(data), confidence: withMeta ? 'medium' : undefined, sources: [] },
      ])
    } catch (err) {
      setList((prev) => [
        ...prev,
        errorMessage(`Sorry, I couldn't process that document (${err.response?.data?.detail || err.message}).`),
      ])
    } finally {
      setBusy(false)
    }
  }

  const handleFileSelect = (file) => uploadDocument(file, { setList: setMessages, setBusy: setUploading, withMeta: true })
  const handleWidgetFileSelect = (file) =>
    uploadDocument(file, { setList: setWidgetMessages, setBusy: setWidgetUploading, withMeta: false })

  const handleNewConversation = () => {
    setSessionId(resetSessionId())
    setMessages([])
    setProfile({})
    setEligibilityMode(false)
    setEligibilityResults([])
    setIsTyping(false)
    setMainChatOpen(false)
  }

  useEffect(() => {
    if (mainChatOpen) {
      document.getElementById('chat-input')?.querySelector('textarea')?.focus()
    }
  }, [mainChatOpen])

  const handleWidgetRefresh = () => {
    setWidgetMessages(INITIAL_WIDGET_MESSAGES())
    setWidgetTyping(false)
  }

  const handleFaqClick = (faq) => {
    setLanguage(faq.lang)
    const isDesktop = window.matchMedia('(min-width: 1024px)').matches

    if (isDesktop) {
      setWidgetMinimized(false)
      sendWidgetMessage(faq.question)
      requestAnimationFrame(() => {
        document.getElementById('hero-chat-widget')?.scrollIntoView({ behavior: 'smooth', block: 'center' })
      })
    } else {
      setMainChatOpen(true)
      setPrefill({ text: faq.question, id: nextId() })
    }
  }

  const inChat = messages.length > 0 || mainChatOpen

  return (
    <div className="w-full bg-bg">
      <a href="#main" className="skip-link">
        Skip to main content
      </a>
      <Header
        language={language}
        onLanguageChange={setLanguage}
        onNewConversation={handleNewConversation}
        theme={theme}
        onToggleTheme={toggleTheme}
      />

      <main id="main" className="pt-16">
        <ConnectionBanner connected={connected} />

        <div
          inert={inChat}
          aria-hidden={inChat}
          className={`overflow-hidden transition-[opacity,max-height] duration-300 ease-out ${
            inChat ? 'max-h-0 opacity-0' : 'max-h-[8000px] opacity-100'
          }`}
        >
          <Hero
            onStart={() => setMainChatOpen(true)}
            widget={
              <HeroChatWidget
                messages={widgetMessages}
                onSend={sendWidgetMessage}
                onRetry={handleWidgetRetry}
                typing={widgetTyping}
                uploading={widgetUploading}
                minimized={widgetMinimized}
                onMinimize={() => setWidgetMinimized(true)}
                onRestore={() => setWidgetMinimized(false)}
                expanded={widgetExpanded}
                onExpand={() => setWidgetExpanded(true)}
                onCollapseExpand={() => setWidgetExpanded(false)}
                onRefresh={handleWidgetRefresh}
                onFileSelect={handleWidgetFileSelect}
                connected={connected}
                sessionId={sessionId}
              />
            }
          />
          <HowItWorks />
          <Trust />
          <Faq onPick={handleFaqClick} />
          <Footer />
        </div>

        {inChat && (
          <div className="flex h-[calc(100dvh-4rem)] min-h-0 flex-col sm:flex-row">
            <h1 className="sr-only">SchemeBot chat</h1>
            <div className="flex min-h-0 flex-1 flex-col">
              <ChatWindow
                messages={messages}
                isTyping={isTyping}
                uploading={uploading}
                onExampleClick={(text) => handleSend(text, 'button')}
                onRetry={handleRetry}
                sessionId={sessionId}
              />
              <div id="chat-input">
                <InputBar
                  onSend={handleSend}
                  onFileSelect={handleFileSelect}
                  disabled={!connected || uploading}
                  prefill={prefill}
                />
              </div>
            </div>

            {eligibilityMode && <EligibilityPanel profile={profile} results={eligibilityResults} />}
          </div>
        )}
      </main>
    </div>
  )
}
