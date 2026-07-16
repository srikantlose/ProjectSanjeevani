import { useStore } from '../store'
import type { Incident } from '../types/events'

function IncidentCard({ incident }: { incident: Incident }) {
  return (
    <div className="flex flex-col gap-1 p-2">
      <p>{incident.id}</p>
      <p>{incident.camera_id}</p>
      <p>severity: {incident.severity}</p>
      <p>{incident.reasons[0] ?? ''}</p>
      <p>status: {incident.status}</p>
    </div>
  )
}

function IncidentFeed() {
  const incidents = useStore((s) => s.incidents)
  const sorted = Object.values(incidents).sort((a, b) => (a.detected_at < b.detected_at ? 1 : -1))

  return (
    <div className="flex flex-col gap-2">
      {sorted.map((incident) => (
        <IncidentCard key={incident.id} incident={incident} />
      ))}
    </div>
  )
}

export default IncidentFeed
