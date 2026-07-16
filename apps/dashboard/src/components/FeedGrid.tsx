import { API_BASE } from '../lib/api'

interface FeedGridProps {
  filenames: string[]
}

function FeedGrid({ filenames }: FeedGridProps) {
  return (
    <div className="flex flex-wrap gap-2">
      {filenames.map((filename) => (
        // eslint-disable-next-line jsx-a11y/media-has-caption
        <video key={filename} src={`${API_BASE}/scenario_media/${filename}`} autoPlay muted loop className="w-1/2" />
      ))}
    </div>
  )
}

export default FeedGrid
