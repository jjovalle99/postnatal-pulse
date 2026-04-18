import { describe, expect, test } from 'bun:test'

import {
  applyCallSseEvent,
  type CallSseEvent,
  createInitialCallState,
} from './call-state'

describe('applyCallSseEvent', () => {
  test('reduces a fixture stream into the latest triage, transcript, rationale, and end state', () => {
    const events: CallSseEvent[] = [
      {
        type: 'triage',
        data: {
          t: 0,
          state: 'green',
          source: 'pre-flag',
          flag_id: null,
        },
      },
      {
        type: 'transcript',
        data: {
          t: 134,
          speaker: 'Patient',
          text: 'I’m fine. Honestly. I’m fine.',
          is_final: true,
          confidence: null,
        },
      },
      {
        type: 'flag',
        data: {
          flag_id: 'flag-123',
          kind: 'minimization',
          t: 134,
          contributing_signals: ['Fatigue', 'Anhedonia', 'Sleep issues'],
          deterministic_payload: {
            scenario_id: 'A',
            flag_at_t: 134,
            has_flag: true,
            contributing_signals: ['Fatigue', 'Anhedonia', 'Sleep issues'],
          },
        },
      },
      {
        type: 'biomarker',
        data: {
          t: 134,
          layer: 'helios',
          snapshots: {
            distress: 0.61,
            fatigue: 0.66,
          },
        },
      },
      {
        type: 'concordance_trace',
        data: {
          t: 134,
          transcript_min: 0.66,
          acoustic_strain: 0.51,
        },
      },
      {
        type: 'rationale_done',
        data: {
          flag_id: 'flag-123',
          drivers: [
            'Voice signals increasing strain and fatigue across the last 90 seconds.',
            'Voice signals reduced enjoyment and engagement when baby and feeding come up.',
            'Spoken words stay reassuring while acoustic stress keeps climbing — the two don’t match.',
          ],
          confidence: 'High',
        },
      },
      {
        type: 'triage',
        data: {
          t: 134,
          state: 'amber',
          source: 'post-flag',
          flag_id: 'flag-123',
        },
      },
      {
        type: 'end',
        data: {
          call_id: 'call-123',
          duration_seconds: 240,
          summary: {
            source: 'fixture',
            scenario_id: 'A',
          },
        },
      },
    ]

    const finalState = events.reduce(
      applyCallSseEvent,
      createInitialCallState(),
    )

    expect(finalState.triage).toEqual({
      t: 134,
      state: 'amber',
      source: 'post-flag',
      flagId: 'flag-123',
    })
    expect(finalState.transcripts).toEqual([
      {
        t: 134,
        speaker: 'Patient',
        text: 'I’m fine. Honestly. I’m fine.',
        isFinal: true,
        confidence: null,
      },
    ])
    expect(finalState.flag?.kind).toBe('minimization')
    expect(finalState.rationale?.confidence).toBe('High')
    expect(finalState.biomarkerSnapshots).toEqual([
      {
        t: 134,
        layer: 'helios',
        snapshots: {
          distress: 0.61,
          fatigue: 0.66,
        },
      },
    ])
    expect(finalState.concordanceTrace).toEqual([
      {
        t: 134,
        transcriptMin: 0.66,
        acousticStrain: 0.51,
      },
    ])
    expect(finalState.ended).toBe(true)
    expect(finalState.durationSeconds).toBe(240)
    expect(finalState.summary).toEqual({
      source: 'fixture',
      scenarioId: 'A',
    })
  })
})
