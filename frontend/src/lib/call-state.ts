export type JsonPrimitive = boolean | number | string | null

export type JsonValue =
  | JsonPrimitive
  | JsonValue[]
  | { [key: string]: JsonValue }

export type TriageState = 'awaiting' | 'green' | 'amber' | 'red'

export type TriageSource =
  | 'pre-flag'
  | 'post-flag'
  | 'post-probe'
  | 'escalation'
  | 'dismiss'
  | 'call-end'

export type TranscriptLine = {
  t: number
  speaker: string
  text: string
  isFinal: boolean
  confidence: number | null
}

export type FlagSummary = {
  flagId: string
  kind: string
  t: number
  contributingSignals: string[]
  deterministicPayload: Record<string, JsonValue>
}

export type RationaleSummary = {
  flagId: string
  drivers: string[]
  confidence: string
}

export type CallSummary = {
  source: string
  scenarioId: string
}

export type BiomarkerSnapshot = {
  t: number
  layer: string
  snapshots: Record<string, number>
}

export type ConcordanceTracePoint = {
  t: number
  transcriptMin: number
  acousticStrain: number
}

export type CallState = {
  triage: {
    t: number
    state: TriageState
    source: TriageSource
    flagId: string | null
  } | null
  transcripts: TranscriptLine[]
  flag: FlagSummary | null
  rationale: RationaleSummary | null
  biomarkerSnapshots: BiomarkerSnapshot[]
  concordanceTrace: ConcordanceTracePoint[]
  systemMessages: string[]
  ended: boolean
  durationSeconds: number | null
  summary: CallSummary | null
}

export type TriageSseEvent = {
  type: 'triage'
  data: {
    t: number
    state: TriageState
    source: TriageSource
    flag_id: string | null
  }
}

export type TranscriptSseEvent = {
  type: 'transcript'
  data: {
    t: number
    speaker: string
    text: string
    is_final: boolean
    confidence: number | null
  }
}

export type FlagSseEvent = {
  type: 'flag'
  data: {
    flag_id: string
    kind: string
    t: number
    contributing_signals: string[]
    deterministic_payload: Record<string, JsonValue>
  }
}

export type RationaleDoneSseEvent = {
  type: 'rationale_done'
  data: {
    flag_id: string
    drivers: string[]
    confidence: string
  }
}

export type BiomarkerSseEvent = {
  type: 'biomarker'
  data: {
    t: number
    layer: string
    snapshots: Record<string, number>
  }
}

export type ConcordanceTraceSseEvent = {
  type: 'concordance_trace'
  data: {
    t: number
    transcript_min: number
    acoustic_strain: number
  }
}

export type SystemSseEvent = {
  type: 'system'
  data: {
    kind: string
    timestamp?: number
  }
}

export type EndSseEvent = {
  type: 'end'
  data: {
    call_id: string
    duration_seconds: number
    summary: {
      source: string
      scenario_id: string
    }
  }
}

export type CallSseEvent =
  | BiomarkerSseEvent
  | ConcordanceTraceSseEvent
  | EndSseEvent
  | FlagSseEvent
  | RationaleDoneSseEvent
  | SystemSseEvent
  | TranscriptSseEvent
  | TriageSseEvent

/** Creates the empty in-memory state for one active call stream. */
export function createInitialCallState(): CallState {
  return {
    triage: null,
    transcripts: [],
    flag: null,
    rationale: null,
    biomarkerSnapshots: [],
    concordanceTrace: [],
    systemMessages: [],
    ended: false,
    durationSeconds: null,
    summary: null,
  }
}

/** Applies one typed SSE event from the backend to the current call state. */
export function applyCallSseEvent(
  state: CallState,
  event: CallSseEvent,
): CallState {
  switch (event.type) {
    case 'triage':
      return {
        ...state,
        triage: {
          t: event.data.t,
          state: event.data.state,
          source: event.data.source,
          flagId: event.data.flag_id,
        },
      }
    case 'transcript':
      return {
        ...state,
        transcripts: [
          ...state.transcripts,
          {
            t: event.data.t,
            speaker: event.data.speaker,
            text: event.data.text,
            isFinal: event.data.is_final,
            confidence: event.data.confidence,
          },
        ],
      }
    case 'flag':
      return {
        ...state,
        flag: {
          flagId: event.data.flag_id,
          kind: event.data.kind,
          t: event.data.t,
          contributingSignals: event.data.contributing_signals,
          deterministicPayload: event.data.deterministic_payload,
        },
      }
    case 'rationale_done':
      return {
        ...state,
        rationale: {
          flagId: event.data.flag_id,
          drivers: event.data.drivers,
          confidence: event.data.confidence,
        },
      }
    case 'biomarker':
      return {
        ...state,
        biomarkerSnapshots: [
          ...state.biomarkerSnapshots,
          {
            t: event.data.t,
            layer: event.data.layer,
            snapshots: event.data.snapshots,
          },
        ],
      }
    case 'concordance_trace':
      return {
        ...state,
        concordanceTrace: [
          ...state.concordanceTrace,
          {
            t: event.data.t,
            transcriptMin: event.data.transcript_min,
            acousticStrain: event.data.acoustic_strain,
          },
        ],
      }
    case 'system':
      return {
        ...state,
        systemMessages: [...state.systemMessages, event.data.kind],
      }
    case 'end':
      return {
        ...state,
        ended: true,
        durationSeconds: event.data.duration_seconds,
        summary: {
          source: event.data.summary.source,
          scenarioId: event.data.summary.scenario_id,
        },
      }
  }
}
