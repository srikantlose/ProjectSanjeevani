import { useStore } from '../store'
import type { Incident } from '../types/events'

interface IncidentCardProps {
  incident: Incident
  onSelect: (id: string) => void
}

function IncidentCard({ incident, onSelect }: IncidentCardProps) {
  return (
    <div className="flex flex-col gap-1 p-2">
      <button type="button" onClick={() => onSelect(incident.id)}>
        {incident.id}
      </button>
      <p>{incident.camera_id}</p>
      <p>severity: {incident.severity}</p>
      <p>{incident.reasons[0] ?? ''}</p>
      <p>status: {incident.status}</p>
    </div>
  )
}

interface IncidentFeedProps {
  onSelect: (id: string) => void
}

function IncidentFeed({ onSelect }: IncidentFeedProps) {
  const incidents = useStore((s) => s.incidents)
  const sorted = Object.values(incidents).sort((a, b) => (a.detected_at < b.detected_at ? 1 : -1))

  return (
    <div className="flex flex-col gap-2">
      {sorted.map((incident) => (
        <IncidentCard key={incident.id} incident={incident} onSelect={onSelect} />
      ))}
    </div>
  )
}

export default IncidentFeed
