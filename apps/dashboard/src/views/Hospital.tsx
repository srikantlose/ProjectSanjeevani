import { useEffect, useRef, useState } from 'react'
import { useStore } from '../store'

function Hospital() {
  const wsStatus = useStore((s) => s.wsStatus)
  const hospitalAlerts = useStore((s) => s.hospitalAlerts)
  const receivedAtRef = useRef<Record<string, number>>({})
  const [now, setNow] = useState(() => Date.now())

  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), 1000)
    return () => clearInterval(id)
  }, [])

  useEffect(() => {
    for (const alert of hospitalAlerts) {
      if (!(alert.dispatch_id in receivedAtRef.current)) {
        receivedAtRef.current[alert.dispatch_id] = Date.now()
      }
    }
  }, [hospitalAlerts])

  return (
    <div className="flex flex-col gap-4 p-4">
      <h1>Hospital Console</h1>
      <p>ws: {wsStatus}</p>
      <div className="flex flex-col gap-2">
        {hospitalAlerts.map((alert) => {
          const receivedAt = receivedAtRef.current[alert.dispatch_id] ?? now
          const remainingSeconds = Math.max(0, Math.round(alert.eta_seconds - (now - receivedAt) / 1000))
          return (
            <div key={alert.dispatch_id} className="border p-2">
              <p>hospital: {alert.hospital_name}</p>
              <p>severity: {alert.severity}</p>
              <p>incident type: {alert.incident_type}</p>
              <p>eta: {remainingSeconds}s</p>
            </div>
          )
        })}
      </div>
    </div>
  )
}

export default Hospital
