import { useEffect, useState } from 'react'
import { fetchMetricsSummary } from '../lib/api'
import { useStore } from '../store'

function Metrics() {
  const wsStatus = useStore((s) => s.wsStatus)
  const [summary, setSummary] = useState<Record<string, unknown> | null>(null)

  useEffect(() => {
    fetchMetricsSummary()
      .then(setSummary)
      .catch((err) => console.error('fetchMetricsSummary failed', err))
  }, [])

  const noRuns = summary?.status === 'no_runs'

  return (
    <div className="flex flex-col gap-4 p-4">
      <h1>Metrics</h1>
      <p>ws: {wsStatus}</p>
      {!summary && <p>loading...</p>}
      {summary && noRuns && <p>no evaluation runs yet</p>}
      {summary && !noRuns && (
        <table>
          <tbody>
            {Object.entries(summary).map(([key, value]) => (
              <tr key={key}>
                <td>{key}</td>
                <td>{typeof value === 'object' ? JSON.stringify(value) : String(value)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}

export default Metrics
