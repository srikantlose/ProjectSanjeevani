import { useStore } from '../store'

function Dispatch() {
  const wsStatus = useStore((s) => s.wsStatus)

  return (
    <div>
      <h1>Dispatch</h1>
      <p>ws: {wsStatus}</p>
    </div>
  )
}

export default Dispatch
