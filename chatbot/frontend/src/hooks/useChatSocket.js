import { useCallback, useEffect, useRef, useState } from 'react'
import { WS_URL } from '../utils/api'

const RECONNECT_DELAY_MS = 2000

export function useChatSocket({ sessionId, onMessage }) {
  const [connected, setConnected] = useState(false)
  const socketRef = useRef(null)
  const reconnectTimerRef = useRef(null)
  const onMessageRef = useRef(onMessage)
  onMessageRef.current = onMessage

  const connect = useCallback(() => {
    const ws = new WebSocket(WS_URL)
    socketRef.current = ws

    ws.onopen = () => setConnected(true)

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        onMessageRef.current(data)
      } catch {
        // ignore malformed frames
      }
    }

    ws.onclose = () => {
      setConnected(false)
      reconnectTimerRef.current = setTimeout(connect, RECONNECT_DELAY_MS)
    }

    ws.onerror = () => {
      ws.close()
    }
  }, [])

  useEffect(() => {
    connect()
    return () => {
      clearTimeout(reconnectTimerRef.current)
      socketRef.current?.close()
    }
  }, [connect])

  const sendMessage = useCallback(
    (message, language) => {
      const ws = socketRef.current
      if (!ws || ws.readyState !== WebSocket.OPEN) return false
      ws.send(JSON.stringify({ message, session_id: sessionId, language }))
      return true
    },
    [sessionId]
  )

  return { connected, sendMessage }
}
