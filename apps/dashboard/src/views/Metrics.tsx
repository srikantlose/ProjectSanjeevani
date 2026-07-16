import { useStore } from '../store'

function Metrics() {
  const wsStatus = useStore((s) => s.wsStatus)

  return (
    <div>
      <h1>Metrics</h1>
      <p>ws: {wsStatus}</p>
    </div>
  )
}

export default Metrics
