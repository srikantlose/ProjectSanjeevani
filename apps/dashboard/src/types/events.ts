// TS mirror of services/api/schemas.py + the WS envelope (plan.md §8.2). Keep in sync.

export interface Location {
  lat: number
  lon: number
  label: string
}

export interface Evidence {
  clip_url: string | null
  snapshot_url: string | null
}

export interface DispatchInfo {
  dispatch_id: string
  ambulance_id: string
  hospital_id: string
  hospital_name: string
  eta_seconds: number
  route: [number, number][] // GeoJSON order: [lon, lat]
}

export type IncidentStatus = 'PENDING_VERIFICATION' | 'CONFIRMED' | 'REJECTED' | 'DISPATCHED' | 'RESOLVED'

export interface Incident {
  id: string
  camera_id: string
  mode: string
  status: IncidentStatus
  severity: string
  severity_reasons: string[]
  signals: Record<string, number>
  reasons: string[]
  location: Location
  evidence: Evidence
  detected_at: string
  dispatch?: DispatchInfo
}

export type AmbulanceState = 'TO_SCENE' | 'AT_SCENE' | 'TO_HOSPITAL' | 'ARRIVED'

export interface AmbulancePosition {
  dispatch_id: string
  ambulance_id: string
  lat: number
  lon: number
  heading_deg: number
  state: AmbulanceState
  eta_seconds: number
}

export type CorridorSignalState = 'GREEN' | 'DEFAULT'

export interface CorridorUpdate {
  dispatch_id: string
  junction_id: string
  junction_name: string
  signal_state: CorridorSignalState
}

export interface HospitalAlert {
  dispatch_id: string
  hospital_id: string
  hospital_name: string
  severity: string
  incident_type: string
  eta_seconds: number
}

export interface IncidentUpdatedPayload {
  id: string
  status: IncidentStatus
  dispatch?: DispatchInfo
}

export type WSMessage =
  | { type: 'incident.new'; ts: string; payload: Incident }
  | { type: 'incident.updated'; ts: string; payload: IncidentUpdatedPayload }
  | { type: 'ambulance.position'; ts: string; payload: AmbulancePosition }
  | { type: 'corridor.updated'; ts: string; payload: CorridorUpdate }
  | { type: 'hospital.alert'; ts: string; payload: HospitalAlert }
