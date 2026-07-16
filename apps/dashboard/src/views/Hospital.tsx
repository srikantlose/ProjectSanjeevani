import { useStore } from '../store'

function Hospital() {
  const wsStatus = useStore((s) => s.wsStatus)

  return (
    <div>
      <h1>Hospital Console</h1>
      <p>ws: {wsStatus}</p>
    </div>
  )
}

export default Hospital
