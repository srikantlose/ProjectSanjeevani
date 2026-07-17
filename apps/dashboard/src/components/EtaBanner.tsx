import { useStore } from '../store'
import type { Incident } from '../types/events'

interface Props {
  incident?: Incident
}

function EtaBanner({ incident }: Props) {
  const ambulances = useStore((s) => s.ambulances)
  const dispatch = incident?.dispatch

  if (!dispatch) return <p>eta: --</p>

  const live = ambulances[dispatch.ambulance_id]
  const state = live?.state ?? 'TO_SCENE'
  const etaSeconds = live?.eta_seconds ?? dispatch.eta_seconds

  return (
    <p>
      ambulance {dispatch.ambulance_id}: {state}, eta {Math.round(etaSeconds)}s to {dispatch.hospital_name}
    </p>
  )
}

export default EtaBanner
