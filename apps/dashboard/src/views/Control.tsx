import { useStore } from '../store'

function Control() {
  const wsStatus = useStore((s) => s.wsStatus)

  return (
    <div>
      <h1>Control Room</h1>
      <p>ws: {wsStatus}</p>
    </div>
  )
}

export default Control
