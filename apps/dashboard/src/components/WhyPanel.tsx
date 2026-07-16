import type { Incident } from '../types/events'

function WhyPanel({ incident }: { incident: Incident }) {
  return (
    <div className="flex flex-col gap-2">
      <h2>Why</h2>
      {Object.entries(incident.signals).map(([name, score]) => (
        <div key={name} className="flex items-center gap-2">
          <span>{name}</span>
          <progress max={1} value={score} />
          <span>{score.toFixed(2)}</span>
        </div>
      ))}
      <ul>
        {incident.reasons.map((reason) => (
          <li key={reason}>{reason}</li>
        ))}
      </ul>
    </div>
  )
}

export default WhyPanel
