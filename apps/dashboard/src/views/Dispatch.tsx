import EtaBanner from '../components/EtaBanner'
import MapView from '../components/MapView'
import Stopwatch from '../components/Stopwatch'
import { useStore } from '../store'

function Dispatch() {
  const wsStatus = useStore((s) => s.wsStatus)
  const incidents = useStore((s) => s.incidents)

  const activeIncident = Object.values(incidents).sort(
    (a, b) => Date.parse(b.detected_at) - Date.parse(a.detected_at),
  )[0]

  return (
    <div className="flex flex-col gap-4 p-4">
      <h1>Dispatch</h1>
      <p>ws: {wsStatus}</p>
      <Stopwatch incident={activeIncident} />
      <EtaBanner incident={activeIncident} />
      <MapView />
    </div>
  )
}

export default Dispatch
