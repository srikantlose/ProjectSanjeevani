import maplibregl from 'maplibre-gl'
import 'maplibre-gl/dist/maplibre-gl.css'
import { useEffect, useRef, useState } from 'react'
import { API_BASE, fetchHospitals, type HospitalRecord } from '../lib/api'
import { useStore } from '../store'

const CENTER: [number, number] = [77.6, 12.97]
const ZOOM = 12
const TWEEN_DURATION_MS = 1000

function MapView() {
  const mapContainerRef = useRef<HTMLDivElement>(null)
  const mapRef = useRef<maplibregl.Map | null>(null)
  const ambulanceMarkerRef = useRef<maplibregl.Marker | null>(null)
  const incidentMarkerRef = useRef<maplibregl.Marker | null>(null)
  const hospitalMarkerRef = useRef<maplibregl.Marker | null>(null)
  const tweenFrameRef = useRef<number | null>(null)

  const incidents = useStore((s) => s.incidents)
  const ambulances = useStore((s) => s.ambulances)
  const [hospitals, setHospitals] = useState<HospitalRecord[]>([])

  const dispatchedIncident = Object.values(incidents).find((i) => i.dispatch)

  useEffect(() => {
    fetchHospitals()
      .then(setHospitals)
      .catch((err) => console.error('fetchHospitals failed', err))
  }, [])

  // Map + route line layer setup (runs once).
  useEffect(() => {
    if (!mapContainerRef.current) return

    const map = new maplibregl.Map({
      container: mapContainerRef.current,
      style: {
        version: 8,
        sources: {
          osm: {
            type: 'raster',
            tiles: [`${API_BASE}/tiles/{z}/{x}/{y}.png`],
            tileSize: 256,
            attribution: '© OpenStreetMap contributors',
          },
        },
        layers: [{ id: 'osm', type: 'raster', source: 'osm' }],
      },
      center: CENTER,
      zoom: ZOOM,
    })
    mapRef.current = map

    map.on('load', () => {
      map.addSource('route', { type: 'geojson', data: { type: 'FeatureCollection', features: [] } })
      map.addLayer({ id: 'route-line', type: 'line', source: 'route', paint: { 'line-width': 4 } })
    })

    return () => {
      map.remove()
      mapRef.current = null
    }
  }, [])

  // Route line + incident/hospital markers, redrawn whenever the dispatched incident changes.
  useEffect(() => {
    const map = mapRef.current
    if (!map) return

    const route = dispatchedIncident?.dispatch?.route

    const draw = () => {
      const source = map.getSource('route') as maplibregl.GeoJSONSource | undefined
      source?.setData({
        type: 'FeatureCollection',
        features: route
          ? [{ type: 'Feature', properties: {}, geometry: { type: 'LineString', coordinates: route } }]
          : [],
      })

      if (dispatchedIncident) {
        const { lat, lon } = dispatchedIncident.location
        if (!incidentMarkerRef.current) {
          incidentMarkerRef.current = new maplibregl.Marker({ color: 'blue' }).setLngLat([lon, lat]).addTo(map)
        } else {
          incidentMarkerRef.current.setLngLat([lon, lat])
        }
      }

      const hospitalId = dispatchedIncident?.dispatch?.hospital_id
      const hospital = hospitals.find((h) => h.id === hospitalId)
      if (hospital) {
        if (!hospitalMarkerRef.current) {
          hospitalMarkerRef.current = new maplibregl.Marker({ color: 'green' })
            .setLngLat([hospital.lon, hospital.lat])
            .addTo(map)
        } else {
          hospitalMarkerRef.current.setLngLat([hospital.lon, hospital.lat])
        }
      }
    }

    if (map.isStyleLoaded()) draw()
    else map.once('load', draw)
  }, [dispatchedIncident, hospitals])

  // Tween the ambulance marker between position ticks.
  useEffect(() => {
    const map = mapRef.current
    const ambulanceId = dispatchedIncident?.dispatch?.ambulance_id
    const latest = ambulanceId ? ambulances[ambulanceId] : undefined
    if (!map || !latest) return

    if (!ambulanceMarkerRef.current) {
      ambulanceMarkerRef.current = new maplibregl.Marker({ color: 'red' }).setLngLat([latest.lon, latest.lat]).addTo(map)
      return
    }

    const marker = ambulanceMarkerRef.current
    const start = marker.getLngLat()
    const endLng = latest.lon
    const endLat = latest.lat
    const startTime = performance.now()

    if (tweenFrameRef.current !== null) cancelAnimationFrame(tweenFrameRef.current)

    function step(now: number) {
      const t = Math.min(1, (now - startTime) / TWEEN_DURATION_MS)
      marker.setLngLat([start.lng + (endLng - start.lng) * t, start.lat + (endLat - start.lat) * t])
      if (t < 1) tweenFrameRef.current = requestAnimationFrame(step)
    }
    tweenFrameRef.current = requestAnimationFrame(step)
  }, [ambulances, dispatchedIncident])

  return <div ref={mapContainerRef} className="w-full h-[32rem]" />
}

export default MapView
