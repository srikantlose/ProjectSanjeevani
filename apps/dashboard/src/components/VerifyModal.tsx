import { API_BASE, verifyIncident } from '../lib/api'
import type { Incident } from '../types/events'

function VerifyModal({ incident }: { incident: Incident }) {
  const handleDecision = async (decision: 'confirm' | 'reject') => {
    try {
      await verifyIncident(incident.id, decision)
    } catch (err) {
      console.error('verifyIncident failed', err)
    }
  }

  return (
    <dialog open className="flex flex-col gap-2">
      <h2>Verify Incident</h2>
      {incident.evidence.clip_url && (
        // eslint-disable-next-line jsx-a11y/media-has-caption
        <video controls src={`${API_BASE}${incident.evidence.clip_url}`} className="w-full" />
      )}
      <div className="flex gap-2">
        <button type="button" onClick={() => handleDecision('confirm')}>
          Confirm
        </button>
        <button type="button" onClick={() => handleDecision('reject')}>
          Reject
        </button>
      </div>
    </dialog>
  )
}

export default VerifyModal
