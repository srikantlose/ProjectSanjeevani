import MapView from '../components/MapView'
import { useStore } from '../store'

function Dispatch() {
  const wsStatus = useStore((s) => s.wsStatus)

  return (
    <div className="flex flex-col gap-4 p-4">
      <h1>Dispatch</h1>
      <p>ws: {wsStatus}</p>
      <MapView />
    </div>
  )
}

export default Dispatch
