import type { Incident } from '../types/events'

export const API_BASE = 'http://localhost:8000'

export interface HospitalRecord {
  id: string
  name: string
  lat: number
  lon: number
  trauma_level: number
}

export async function fetchIncidents(): Promise<Incident[]> {
  const res = await fetch(`${API_BASE}/api/incidents`)
  if (!res.ok) throw new Error(`fetchIncidents failed: ${res.status}`)
  return res.json()
}

export async function fetchHospitals(): Promise<HospitalRecord[]> {
  const res = await fetch(`${API_BASE}/api/hospitals`)
  if (!res.ok) throw new Error(`fetchHospitals failed: ${res.status}`)
  return res.json()
}

export interface JunctionRecord {
  id: string
  name: string
  lat: number
  lon: number
}

export async function fetchJunctions(): Promise<JunctionRecord[]> {
  const res = await fetch(`${API_BASE}/api/junctions`)
  if (!res.ok) throw new Error(`fetchJunctions failed: ${res.status}`)
  return res.json()
}

export async function verifyIncident(id: string, decision: 'confirm' | 'reject'): Promise<{ id: string; status: string }> {
  const res = await fetch(`${API_BASE}/api/incidents/${id}/verify`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ decision }),
  })
  if (!res.ok) throw new Error(`verifyIncident failed: ${res.status}`)
  return res.json()
}

export async function fetchMetricsSummary(): Promise<Record<string, unknown>> {
  const res = await fetch(`${API_BASE}/api/metrics/summary`)
  if (!res.ok) throw new Error(`fetchMetricsSummary failed: ${res.status}`)
  return res.json()
}
