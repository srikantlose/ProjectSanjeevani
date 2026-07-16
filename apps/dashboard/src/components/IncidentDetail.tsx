import { useStore } from '../store'
import VerifyModal from './VerifyModal'
import WhyPanel from './WhyPanel'

function IncidentDetail({ incidentId }: { incidentId: string }) {
  const incident = useStore((s) => s.incidents[incidentId])
  if (!incident) return null

  return (
    <div className="flex flex-col gap-4 p-2">
      <WhyPanel incident={incident} />
      {incident.status === 'PENDING_VERIFICATION' && <VerifyModal incident={incident} />}
    </div>
  )
}

export default IncidentDetail
