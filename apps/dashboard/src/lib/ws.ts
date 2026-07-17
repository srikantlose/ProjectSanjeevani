import { useStore } from '../store'
import type { WSMessage } from '../types/events'

const WS_URL = 'ws://localhost:8000/ws'
const BACKOFF_STEPS_MS = [1000, 2000, 4000, 10000]

export function connectWS(onMessage?: (msg: WSMessage) => void): () => void {
  let backoffIndex = 0
  let reconnectTimer: ReturnType<typeof setTimeout> | null = null
  let closed = false
  let ws: WebSocket | null = null

  function connect() {
    useStore.getState().setWsStatus('connecting')
    ws = new WebSocket(WS_URL)

    ws.onopen = () => {
      backoffIndex = 0
      useStore.getState().setWsStatus('open')
    }

    ws.onmessage = (event) => {
      const msg: WSMessage = JSON.parse(event.data)
      useStore.getState().applyMessage(msg)
      onMessage?.(msg)
    }

    ws.onclose = () => {
      useStore.getState().setWsStatus('closed')
      if (closed) return
      const delay = BACKOFF_STEPS_MS[Math.min(backoffIndex, BACKOFF_STEPS_MS.length - 1)]
      backoffIndex += 1
      reconnectTimer = setTimeout(connect, delay)
    }

    ws.onerror = () => {
      ws?.close()
    }
  }

  connect()

  // Cleanup, so a re-mounting effect (e.g. React StrictMode's dev-mode double
  // invoke) doesn't leak a second live connection -- every broadcast would
  // otherwise be applied twice, silently duplicating entries in any
  // array-shaped store field (hospitalAlerts).
  return () => {
    closed = true
    if (reconnectTimer !== null) clearTimeout(reconnectTimer)
    if (ws) {
      ws.onclose = null
      ws.close()
    }
  }
}
