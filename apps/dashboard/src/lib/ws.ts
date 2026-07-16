import { useStore } from '../store'
import type { WSMessage } from '../types/events'

const WS_URL = 'ws://localhost:8000/ws'
const BACKOFF_STEPS_MS = [1000, 2000, 4000, 10000]

export function connectWS(onMessage?: (msg: WSMessage) => void): void {
  let backoffIndex = 0

  function connect() {
    useStore.getState().setWsStatus('connecting')
    const ws = new WebSocket(WS_URL)

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
      const delay = BACKOFF_STEPS_MS[Math.min(backoffIndex, BACKOFF_STEPS_MS.length - 1)]
      backoffIndex += 1
      setTimeout(connect, delay)
    }

    ws.onerror = () => {
      ws.close()
    }
  }

  connect()
}
