import { create } from 'zustand'
import type { LatestCallResponse, ScenarioSummary } from './api'
import {
  applyCallSseEvent,
  type CallSseEvent,
  type CallState,
  createInitialCallState,
} from './call-state'

type CallPhase = 'pre' | 'connecting' | 'live' | 'ended' | 'error'

type CallStoreState = {
  scenarios: ScenarioSummary[]
  selectedScenarioId: string | null
  drawerOpen: boolean
  callId: string | null
  callPhase: CallPhase
  callState: CallState
  errorMessage: string | null
  latestEventT: number
}

type CallStoreActions = {
  setScenarios: (scenarios: ScenarioSummary[]) => void
  setSelectedScenarioId: (scenarioId: string | null) => void
  setDrawerOpen: (drawerOpen: boolean) => void
  beginCall: (callId: string) => void
  attachLatestCall: (call: LatestCallResponse) => void
  applyEvent: (event: CallSseEvent) => void
  setErrorMessage: (errorMessage: string | null) => void
  resetCall: () => void
}

type EventWithTime =
  | { type: 'biomarker'; data: { t: number } }
  | { type: 'concordance_trace'; data: { t: number } }
  | { type: 'end'; data: { duration_seconds: number } }
  | { type: 'flag'; data: { t: number } }
  | { type: 'rationale_done'; data: { flag_id: string } }
  | { type: 'rationale_token'; data: { flag_id: string } }
  | { type: 'system'; data: { timestamp?: number } }
  | { type: 'transcript'; data: { t: number } }
  | { type: 'triage'; data: { t: number } }

function getEventTime(event: EventWithTime): number | null {
  switch (event.type) {
    case 'biomarker':
      return event.data.t
    case 'concordance_trace':
      return event.data.t
    case 'end':
      return event.data.duration_seconds
    case 'flag':
      return event.data.t
    case 'rationale_done':
      return null
    case 'rationale_token':
      return null
    case 'system':
      return event.data.timestamp ?? null
    case 'transcript':
      return event.data.t
    case 'triage':
      return event.data.t
  }
}

/** Zustand store for the single active call stream shown in the UI. */
export const useCallStore = create<CallStoreState & CallStoreActions>(
  (set) => ({
    scenarios: [],
    selectedScenarioId: null,
    drawerOpen: false,
    callId: null,
    callPhase: 'pre',
    callState: createInitialCallState(),
    errorMessage: null,
    latestEventT: 0,
    setScenarios: (scenarios) =>
      set(() => ({
        scenarios,
        selectedScenarioId: scenarios[0]?.id ?? null,
      })),
    setSelectedScenarioId: (selectedScenarioId) =>
      set(() => ({ selectedScenarioId })),
    setDrawerOpen: (drawerOpen) => set(() => ({ drawerOpen })),
    beginCall: (callId) =>
      set(() => ({
        callId,
        callPhase: 'connecting',
        callState: createInitialCallState(),
        latestEventT: 0,
        errorMessage: null,
      })),
    attachLatestCall: (call) =>
      set(() => ({
        callId: call.call_id,
        callPhase: call.phase === 'ended' ? 'ended' : 'connecting',
        callState: createInitialCallState(),
        latestEventT: 0,
        errorMessage: null,
      })),
    applyEvent: (event) =>
      set((state) => {
        const nextCallState = applyCallSseEvent(state.callState, event)
        const eventTime = getEventTime(event)
        return {
          callState: nextCallState,
          callPhase: event.type === 'end' ? 'ended' : 'live',
          latestEventT: eventTime ?? state.latestEventT,
        }
      }),
    setErrorMessage: (errorMessage) =>
      set(() => ({
        callPhase: errorMessage === null ? 'pre' : 'error',
        errorMessage,
      })),
    resetCall: () =>
      set((state) => ({
        callId: null,
        callPhase: 'pre',
        callState: createInitialCallState(),
        latestEventT: 0,
        errorMessage: null,
        drawerOpen: state.drawerOpen,
        scenarios: state.scenarios,
        selectedScenarioId: state.selectedScenarioId,
      })),
  }),
)
