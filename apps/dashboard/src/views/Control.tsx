import FeedGrid from '../components/FeedGrid'
import IncidentFeed from '../components/IncidentFeed'
import { useStore } from '../store'

// Finalized in E8-T2 once the real scenario clips exist in data/processed/.
const SCENARIO_FILENAMES = ['scenario1_junction.mp4', 'scenario2_highway.mp4']

function Control() {
  const wsStatus = useStore((s) => s.wsStatus)

  return (
    <div className="flex flex-col gap-4 p-4">
      <h1>Control Room</h1>
      <p>ws: {wsStatus}</p>
      <FeedGrid filenames={SCENARIO_FILENAMES} />
      <IncidentFeed />
    </div>
  )
}

export default Control
