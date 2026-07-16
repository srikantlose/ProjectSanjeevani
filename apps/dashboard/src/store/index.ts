import { create } from 'zustand'
import type {
  AmbulancePosition,
  CorridorSignalState,
  HospitalAlert,
  Incident,
  WSMessage,
} from '../types/events'

export type WsStatus = 'connecting' | 'open' | 'closed'

interface Store {
  incidents: Record<string, Incident>
  ambulances: Record<string, AmbulancePosition>
  corridor: Record<string, CorridorSignalState>
  hospitalAlerts: HospitalAlert[]
  wsStatus: WsStatus
  setWsStatus: (status: WsStatus) => void
  setIncidents: (incidents: Incident[]) => void
  applyMessage: (msg: WSMessage) => void
}

export const useStore = create<Store>()((set) => ({
  incidents: {},
  ambulances: {},
  corridor: {},
  hospitalAlerts: [],
  wsStatus: 'connecting',

  setWsStatus: (status) => set({ wsStatus: status }),

  setIncidents: (incidents) => set({ incidents: Object.fromEntries(incidents.map((i) => [i.id, i])) }),

  applyMessage: (msg) =>
    set((state) => {
      switch (msg.type) {
        case 'incident.new':
          return { incidents: { ...state.incidents, [msg.payload.id]: msg.payload } }

        case 'incident.updated': {
          const existing = state.incidents[msg.payload.id]
          const merged: Incident = existing
            ? { ...existing, status: msg.payload.status, dispatch: msg.payload.dispatch ?? existing.dispatch }
            : ({ ...msg.payload } as Incident)
          return { incidents: { ...state.incidents, [msg.payload.id]: merged } }
        }

        case 'ambulance.position':
          return { ambulances: { ...state.ambulances, [msg.payload.ambulance_id]: msg.payload } }

        case 'corridor.updated':
          return { corridor: { ...state.corridor, [msg.payload.junction_id]: msg.payload.signal_state } }

        case 'hospital.alert':
          return { hospitalAlerts: [...state.hospitalAlerts, msg.payload] }

        default:
          return {}
      }
    }),
}))
