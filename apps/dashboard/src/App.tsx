import { useEffect } from 'react'
import { Navigate, Route, Routes } from 'react-router-dom'
import { fetchIncidents } from './lib/api'
import { connectWS } from './lib/ws'
import { useStore } from './store'
import Control from './views/Control'
import Dispatch from './views/Dispatch'
import Hospital from './views/Hospital'
import Metrics from './views/Metrics'

function App() {
  const setIncidents = useStore((s) => s.setIncidents)

  useEffect(() => {
    fetchIncidents()
      .then(setIncidents)
      .catch((err) => console.error('fetchIncidents failed', err))
    connectWS()
  }, [setIncidents])

  return (
    <Routes>
      <Route path="/" element={<Navigate to="/control" replace />} />
      <Route path="/control" element={<Control />} />
      <Route path="/dispatch" element={<Dispatch />} />
      <Route path="/hospital" element={<Hospital />} />
      <Route path="/metrics" element={<Metrics />} />
    </Routes>
  )
}

export default App
