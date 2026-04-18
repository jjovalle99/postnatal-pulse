import ky from 'ky'

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'
const apiKey = import.meta.env.VITE_API_KEY ?? 'dev-api-key'

function buildApiUrl(pathname: string): string {
  return new URL(pathname, apiBaseUrl).toString()
}

const apiHeaders = {
  'X-API-Key': apiKey,
}

/** One scenario available for fixture replay. */
export type ScenarioSummary = {
  id: string
  label: string
  duration_seconds: number
  has_flag: boolean
  flag_at_t: number | null
  audio_url: string
}

/** Response payload for call creation. */
export type StartCallResponse = {
  call_id: string
  sse_url: string
  ws_url: string | null
}

/** Response payload for discovering the latest call known by the backend. */
export type LatestCallResponse = {
  call_id: string
  source: string
  phase: string
  sse_url: string
}

/** Response payload for probe submission. */
export type SaveProbesResponse = {
  triage: {
    t: number
    state: 'awaiting' | 'green' | 'amber' | 'red'
    source:
      | 'pre-flag'
      | 'post-flag'
      | 'post-probe'
      | 'escalation'
      | 'dismiss'
      | 'call-end'
    flag_id: string | null
  }
  flag: {
    flag_id: string
    kind: string
    t: number
    contributing_signals: string[]
    deterministic_payload: Record<
      string,
      boolean | number | string | null | string[]
    >
  }
}

/** Response payload for PDF generation. */
export type GenerateHandoffResponse = {
  pdf_id: string
  preview_url: string
  download_url: string
}

/** Fetches the deterministic demo scenarios from the backend. */
export async function fetchScenarios(): Promise<ScenarioSummary[]> {
  return ky
    .get(buildApiUrl('api/scenarios'), { headers: apiHeaders })
    .json<ScenarioSummary[]>()
}

/** Starts one fixture replay call and returns the URLs needed for the live screen. */
export async function startFixtureCall(
  scenarioId: string,
): Promise<StartCallResponse> {
  return ky
    .post(buildApiUrl('api/calls'), {
      headers: apiHeaders,
      json: {
        source: 'fixture',
        scenario_id: scenarioId,
      },
    })
    .json<StartCallResponse>()
}

/** Fetches the most recent call so the UI can attach to a live browser or Twilio session. */
export async function fetchLatestCall(): Promise<LatestCallResponse> {
  return ky
    .get(buildApiUrl('api/calls/latest'), { headers: apiHeaders })
    .json<LatestCallResponse>()
}

/** Saves the three structured probe answers for the active flag. */
export async function saveProbeAnswers(
  callId: string,
  flagId: string,
  answers: [string, string, string],
): Promise<SaveProbesResponse> {
  return ky
    .post(buildApiUrl(`api/calls/${callId}/probes`), {
      headers: apiHeaders,
      json: {
        flag_id: flagId,
        answers,
      },
    })
    .json<SaveProbesResponse>()
}

/** Builds an EventSource-compatible URL for the backend SSE stream. */
export function buildEventSourceUrl(relativeUrl: string): string {
  const url = new URL(relativeUrl, apiBaseUrl)
  url.searchParams.set('api_key', apiKey)
  return url.toString()
}

/** Generates the current handoff PDF and returns its signed preview URL. */
export async function generateHandoff(
  callId: string,
): Promise<GenerateHandoffResponse> {
  return ky
    .post(buildApiUrl(`api/calls/${callId}/handoff`), {
      headers: apiHeaders,
    })
    .json<GenerateHandoffResponse>()
}
