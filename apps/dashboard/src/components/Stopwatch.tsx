import { useEffect, useState } from 'react'
import type { Incident } from '../types/events'

const FROZEN_STATUSES = new Set(['DISPATCHED', 'RESOLVED'])

interface Props {
  incident?: Incident
}

function Stopwatch({ incident }: Props) {
  const [now, setNow] = useState(() => Date.now())

  useEffect(() => {
    if (!incident || FROZEN_STATUSES.has(incident.status)) {
      setNow(Date.now())
      return
    }
    const id = setInterval(() => setNow(Date.now()), 1000)
    return () => clearInterval(id)
  }, [incident?.status])

  if (!incident) return <p>stopwatch: --</p>

  const elapsedSeconds = Math.max(0, Math.floor((now - Date.parse(incident.detected_at)) / 1000))
  const frozen = FROZEN_STATUSES.has(incident.status)

  return (
    <p>
      stopwatch: {elapsedSeconds}s{frozen ? ' (frozen)' : ''}
    </p>
  )
}

export default Stopwatch
