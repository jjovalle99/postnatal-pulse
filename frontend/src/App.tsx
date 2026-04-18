import { useEffect, useMemo, useRef, useState } from 'react'

import './index.css'

import {
  buildEventSourceUrl,
  fetchLatestCall,
  fetchScenarios,
  generateHandoff,
  saveProbeAnswers,
  startFixtureCall,
} from './lib/api'
import type {
  BiomarkerSnapshot,
  CallSseEvent,
  CallState,
  ConcordanceTracePoint,
} from './lib/call-state'
import { useCallStore } from './lib/call-store'
import { getRuntimeContext } from './lib/runtime'

const runtime = getRuntimeContext()

const demoLineNumber = '+44 20 7946 0123'
const biomarkerOrder = [
  'Fatigue',
  'Sleep issues',
  'Low energy',
  'Anhedonia',
  'Distress',
  'Stress',
] as const
const signalValueKeys: Record<(typeof biomarkerOrder)[number], string> = {
  Fatigue: 'fatigue',
  'Sleep issues': 'sleep_issues',
  'Low energy': 'low_energy',
  Anhedonia: 'anhedonia',
  Distress: 'distress',
  Stress: 'stress',
}
const probeDefinitions = [
  {
    question: 'How have you been sleeping when the baby sleeps?',
    options: ['Most days I rest', 'Some days', 'Hardly ever'],
  },
  {
    question: 'Are you still enjoying anything day to day?',
    options: ['Yes, mostly', 'Sometimes', 'Not really'],
  },
  {
    question: 'Who is helping you at the moment?',
    options: ['Plenty of support', 'Some help', 'Mostly on my own'],
  },
] as const

type RibbonState = 'idle' | 'thin' | 'expanded'
type TranscriptState = 'pre' | 'connecting' | 'live' | 'ended'
type LiveScenario = {
  id: string | null
  label: string
  confidence: string
  drivers: string[]
  rationale: string[]
  transcript: { t: number; s: 'C' | 'P'; text: string }[]
  transcriptExcerpt: {
    centerT: number
    spanBefore: number
    spanAfter: number
  } | null
  contributingSignals: string[]
  flagAt: number | null
}

function formatElapsed(totalSeconds: number): string {
  const safeSeconds = Number.isFinite(totalSeconds)
    ? Math.max(0, totalSeconds)
    : 0
  const minutes = Math.floor(safeSeconds / 60)
  const seconds = Math.floor(safeSeconds % 60)
  return `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`
}

function formatClock(date: Date): string {
  return `${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}`
}

function formatDateLong(date: Date): string {
  const days = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']
  const months = [
    'Jan',
    'Feb',
    'Mar',
    'Apr',
    'May',
    'Jun',
    'Jul',
    'Aug',
    'Sep',
    'Oct',
    'Nov',
    'Dec',
  ]
  return `${days[date.getDay()]} ${date.getDate()} ${months[date.getMonth()]} ${date.getFullYear()}`
}

function parseSseEvent<T>(event: MessageEvent<string>): T {
  return JSON.parse(event.data) as T
}

function getTranscriptState(
  callPhase: string,
  transcripts: CallState['transcripts'],
): TranscriptState {
  if (callPhase === 'pre') {
    return 'pre'
  }
  if (callPhase === 'connecting' && transcripts.length === 0) {
    return 'connecting'
  }
  if (callPhase === 'ended') {
    return 'ended'
  }
  return 'live'
}

function getRibbonState(flagFired: boolean, callPhase: string): RibbonState {
  if (callPhase === 'pre') {
    return 'idle'
  }
  if (flagFired) {
    return 'expanded'
  }
  return 'thin'
}

function getTriageLabel(triageState: string | null): string {
  if (triageState === 'green') {
    return 'Green: routine'
  }
  if (triageState === 'amber') {
    return 'Amber: review'
  }
  if (triageState === 'red') {
    return 'Red: urgent review'
  }
  return 'Awaiting call'
}

function deriveLatestBiomarkerValues(
  biomarkerSnapshots: BiomarkerSnapshot[],
): Record<string, number> {
  const values: Record<string, number> = {}
  for (const snapshot of biomarkerSnapshots) {
    Object.assign(values, snapshot.snapshots)
  }
  return values
}

function deriveSignalSeries(
  biomarkerSnapshots: BiomarkerSnapshot[],
): Record<string, number[]> {
  const series: Record<string, number[]> = {
    fatigue: [],
    sleep_issues: [],
    low_energy: [],
    anhedonia: [],
    distress: [],
    stress: [],
  }

  for (const snapshot of biomarkerSnapshots) {
    for (const [key, value] of Object.entries(snapshot.snapshots)) {
      if (key in series) {
        series[key].push(value)
      }
    }
  }

  return series
}

function deriveLiveScenario(
  callState: CallState,
  selectedScenarioId: string | null,
): LiveScenario {
  const drivers = callState.rationale?.drivers ?? []
  const transcript = callState.transcripts.map((line) => {
    const speaker: 'C' | 'P' = line.speaker === 'Clinician' ? 'C' : 'P'
    return {
      t: line.t,
      s: speaker,
      text: line.text,
    }
  })
  const flagAt = callState.flag?.t ?? null
  return {
    id: selectedScenarioId,
    label: selectedScenarioId ? `Scenario ${selectedScenarioId}` : 'Live call',
    confidence: callState.rationale?.confidence ?? 'Low',
    drivers,
    rationale: drivers,
    transcript,
    transcriptExcerpt:
      flagAt === null
        ? null
        : {
            centerT: flagAt,
            spanBefore: 3,
            spanAfter: 3,
          },
    contributingSignals: callState.flag?.contributingSignals ?? [],
    flagAt,
  }
}

function findTranscriptExcerpt(
  transcript: LiveScenario['transcript'],
  centerT: number | null,
): LiveScenario['transcript'] {
  if (centerT === null) {
    return transcript.slice(-8)
  }
  const centerIndex = transcript.findIndex(
    (row) => Math.abs(row.t - centerT) < 0.51,
  )
  if (centerIndex < 0) {
    return transcript.slice(-8)
  }
  return transcript.slice(
    Math.max(0, centerIndex - 4),
    Math.min(transcript.length, centerIndex + 5),
  )
}

function SectionLabel({
  children,
  style,
}: {
  children: string
  style?: React.CSSProperties
}) {
  return (
    <div
      style={{
        fontSize: 10.5,
        letterSpacing: 1.3,
        textTransform: 'uppercase',
        color: 'var(--ink-4)',
        fontWeight: 700,
        whiteSpace: 'nowrap',
        ...style,
      }}
    >
      {children}
    </div>
  )
}

function Chip({
  children,
  tone = 'neutral',
  size = 'sm',
}: {
  children: string
  tone?: 'neutral' | 'blue' | 'amber' | 'muted'
  size?: 'sm' | 'md'
}) {
  const toneStyles = {
    neutral: {
      background: 'var(--paper-2)',
      color: 'var(--ink-2)',
      border: '1px solid var(--paper-rule)',
    },
    blue: {
      background: 'var(--clinic-blue-wash)',
      color: 'var(--clinic-blue)',
      border: '1px solid var(--clinic-blue-tint)',
    },
    amber: {
      background: 'var(--amber-fill-soft)',
      color: 'var(--amber)',
      border: '1px solid var(--amber-rule)',
    },
    muted: {
      background: 'transparent',
      color: 'var(--ink-3)',
      border: '1px solid var(--paper-rule)',
    },
  }[tone]
  const sizeStyles = {
    sm: { fontSize: 11.5, padding: '3px 8px' },
    md: { fontSize: 13, padding: '5px 10px' },
  }[size]

  return (
    <span
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: 6,
        borderRadius: 999,
        fontWeight: 600,
        whiteSpace: 'nowrap',
        letterSpacing: -0.005,
        ...toneStyles,
        ...sizeStyles,
      }}
    >
      {children}
    </span>
  )
}

function Btn({
  kind = 'secondary',
  disabled = false,
  onClick,
  children,
  full = false,
}: {
  kind?: 'primary' | 'secondary' | 'ghost' | 'amber'
  disabled?: boolean
  onClick?: () => void
  children: React.ReactNode
  full?: boolean
}) {
  const kindStyles = {
    primary: {
      background: 'var(--clinic-blue)',
      color: '#fff',
      border: '1px solid var(--clinic-blue)',
      boxShadow:
        '0 1px 0 rgba(15,38,112,0.12), inset 0 1px 0 rgba(255,255,255,0.12)',
    },
    secondary: {
      background: 'var(--surface)',
      color: 'var(--clinic-blue)',
      border: '1px solid var(--clinic-blue-tint)',
    },
    ghost: {
      background: 'var(--surface-2)',
      color: 'var(--ink-2)',
      border: '1px solid var(--paper-rule-soft)',
    },
    amber: {
      background: 'var(--amber)',
      color: '#fff',
      border: '1px solid var(--amber)',
    },
  }[kind]

  return (
    <button
      disabled={disabled}
      onClick={onClick}
      style={{
        ...kindStyles,
        width: full ? '100%' : 'auto',
        padding: '11px 14px',
        borderRadius: 10,
        fontSize: 14,
        fontWeight: 600,
        letterSpacing: -0.005,
        opacity: disabled ? 0.48 : 1,
        cursor: disabled ? 'not-allowed' : 'pointer',
        transition:
          'background 160ms, color 160ms, border-color 160ms, transform 80ms, box-shadow 160ms',
        textAlign: 'left',
      }}
      type="button"
    >
      {children}
    </button>
  )
}

function Card({
  children,
  style,
  padding = 20,
}: {
  children: React.ReactNode
  style?: React.CSSProperties
  padding?: number
}) {
  return (
    <div
      style={{
        background: 'var(--surface)',
        border: '1px solid var(--paper-rule-soft)',
        borderRadius: 14,
        padding,
        boxShadow: 'var(--shadow-card)',
        ...style,
      }}
    >
      {children}
    </div>
  )
}

function TriageLozenge({
  state,
  timestamp,
}: {
  state: 'awaiting' | 'green' | 'amber' | 'red'
  timestamp: string | null
}) {
  const config = {
    awaiting: {
      label: 'Awaiting call',
      fill: 'var(--paper-2)',
      text: 'var(--ink-2)',
      rule: 'var(--paper-rule)',
      dot: 'var(--slate-2)',
      sub: 'no active call',
    },
    green: {
      label: 'Green: routine',
      fill: 'var(--green-wash)',
      text: 'var(--green)',
      rule: '#bcdcc9',
      dot: 'var(--green)',
      sub: 'monitoring · no flag',
    },
    amber: {
      label: 'Amber: review',
      fill: 'var(--amber-fill)',
      text: 'var(--amber)',
      rule: 'var(--amber-rule)',
      dot: 'var(--amber)',
      sub: null,
    },
    red: {
      label: 'Red: urgent review',
      fill: 'var(--red-fill)',
      text: 'var(--red)',
      rule: '#d99992',
      dot: 'var(--red)',
      sub: null,
    },
  }[state]

  const subLabel = timestamp === null ? config.sub : `flagged ${timestamp}`
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
      <div
        style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: 10,
          background: config.fill,
          color: config.text,
          border: `1px solid ${config.rule}`,
          padding: '8px 14px 8px 12px',
          borderRadius: 10,
          fontWeight: 600,
          fontSize: 14,
          letterSpacing: -0.01,
          alignSelf: 'flex-start',
          whiteSpace: 'nowrap',
        }}
      >
        <span
          aria-hidden
          style={{
            width: 8,
            height: 8,
            borderRadius: 999,
            background: config.dot,
            boxShadow:
              state === 'red'
                ? '0 0 0 3px rgba(154,29,22,0.18)'
                : state === 'amber'
                  ? '0 0 0 3px rgba(138,74,7,0.14)'
                  : 'none',
          }}
        />
        <span>{config.label}</span>
      </div>
      {subLabel ? (
        <div
          className="tab"
          style={{
            fontSize: 11,
            color: 'var(--ink-4)',
            paddingLeft: 2,
            letterSpacing: 0.2,
            fontWeight: 500,
            whiteSpace: 'nowrap',
          }}
        >
          {subLabel}
        </div>
      ) : null}
    </div>
  )
}

function TopStrip({
  callPhase,
  elapsed,
  flagAt,
  triage,
  flagFired,
}: {
  callPhase: 'pre' | 'connecting' | 'live' | 'ended' | 'error'
  elapsed: number
  flagAt: number | null
  triage: 'awaiting' | 'green' | 'amber' | 'red'
  flagFired: boolean
}) {
  const showLargeDemo = callPhase === 'pre'
  const callStatusLabel = {
    pre: 'Awaiting call',
    connecting: 'Connecting…',
    live: 'Call live',
    ended: 'Call ended',
    error: 'Error',
  }[callPhase]

  return (
    <div
      style={{
        display: 'grid',
        gridTemplateColumns: 'minmax(0,1fr) auto',
        alignItems: 'center',
        gap: 28,
        padding: '16px 28px',
        borderBottom: '1px solid var(--paper-rule-soft)',
        background: 'var(--surface)',
        boxShadow: '0 1px 0 rgba(15,38,112,0.02)',
      }}
    >
      <div
        style={{ display: 'flex', alignItems: 'center', gap: 24, minWidth: 0 }}
      >
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 10,
            minWidth: 140,
          }}
        >
          <div
            aria-hidden
            style={{
              width: 28,
              height: 28,
              borderRadius: 8,
              background:
                'linear-gradient(135deg, var(--clinic-blue) 0%, var(--clinic-blue-3) 100%)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: '#fff',
              fontWeight: 700,
              fontSize: 13,
              letterSpacing: -0.02,
              boxShadow:
                '0 1px 2px rgba(15,38,112,0.18), inset 0 1px 0 rgba(255,255,255,0.2)',
            }}
          >
            PP
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
            <div
              style={{
                fontSize: 13.5,
                fontWeight: 700,
                color: 'var(--ink)',
                letterSpacing: -0.02,
              }}
            >
              Postnatal Pulse
            </div>
            <div
              style={{
                fontSize: 11,
                color: 'var(--ink-4)',
                letterSpacing: 0.1,
              }}
            >
              Live triage · {runtime.CLINICIAN}
            </div>
          </div>
        </div>

        <div
          style={{ width: 1, height: 36, background: 'var(--paper-rule-soft)' }}
        />

        <TriageLozenge
          state={triage}
          timestamp={
            flagFired && flagAt !== null ? formatElapsed(flagAt) : null
          }
        />

        <div
          style={{ width: 1, height: 36, background: 'var(--paper-rule-soft)' }}
        />

        <div
          style={{
            display: 'flex',
            flexWrap: 'nowrap',
            gap: 8,
            alignItems: 'center',
            minWidth: 0,
            overflow: 'hidden',
            whiteSpace: 'nowrap',
          }}
        >
          <div
            style={{
              fontSize: 15,
              fontWeight: 700,
              color: 'var(--ink)',
              letterSpacing: -0.015,
            }}
          >
            {runtime.PATIENT.name}, {runtime.PATIENT.age}
          </div>
          <span style={{ color: 'var(--paper-rule)', fontSize: 12 }}>·</span>
          <span style={{ fontSize: 13, color: 'var(--ink-2)' }}>
            {runtime.PATIENT.weeks}
          </span>
          <span style={{ color: 'var(--paper-rule)', fontSize: 12 }}>·</span>
          <span style={{ fontSize: 13, color: 'var(--ink-2)' }}>
            {runtime.PATIENT.parity}
          </span>
          <span style={{ color: 'var(--paper-rule)', fontSize: 12 }}>·</span>
          <span
            style={{
              fontSize: 13,
              color: 'var(--ink-2)',
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              minWidth: 0,
            }}
          >
            Baby: {runtime.PATIENT.baby}
          </span>
        </div>
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
        <div
          style={{
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'flex-end',
            gap: 6,
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            {callPhase === 'live' ? (
              <span
                aria-hidden
                style={{
                  width: 8,
                  height: 8,
                  borderRadius: 999,
                  background: 'var(--green)',
                  boxShadow: '0 0 0 3px rgba(23,115,74,0.18)',
                }}
              />
            ) : null}
            <div
              style={{
                fontSize: 13.5,
                fontWeight: 600,
                color: 'var(--ink)',
                letterSpacing: -0.01,
                whiteSpace: 'nowrap',
              }}
            >
              {callStatusLabel}
            </div>
            <span
              className="tab"
              style={{
                fontSize: 14,
                color:
                  callPhase === 'ended' ? 'var(--ink-3)' : 'var(--clinic-blue)',
                fontWeight: 700,
                background:
                  callPhase === 'ended'
                    ? 'var(--paper-2)'
                    : 'var(--clinic-blue-wash)',
                padding: '2px 8px',
                borderRadius: 6,
              }}
            >
              {formatElapsed(elapsed)}
            </span>
          </div>
        </div>

        <div
          style={{
            background: 'var(--clinic-blue-wash)',
            color: 'var(--clinic-blue-ink)',
            border: '1px solid var(--clinic-blue-tint)',
            padding: showLargeDemo ? '10px 16px' : '7px 12px',
            borderRadius: 12,
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'flex-end',
            gap: 2,
          }}
        >
          <div
            style={{
              fontSize: 9.5,
              letterSpacing: 1.3,
              textTransform: 'uppercase',
              fontWeight: 700,
              color: 'var(--clinic-blue)',
              opacity: 0.9,
              whiteSpace: 'nowrap',
            }}
          >
            Demo line
          </div>
          <div
            className="tab"
            style={{
              fontSize: showLargeDemo ? 20 : 14,
              fontWeight: 700,
              color: 'inherit',
              letterSpacing: -0.005,
              whiteSpace: 'nowrap',
            }}
          >
            {demoLineNumber}
          </div>
        </div>
      </div>
    </div>
  )
}

function Sparkline({
  points,
  contributing,
  height = 14,
  width = 120,
}: {
  points: number[]
  contributing: boolean
  height?: number
  width?: number
}) {
  if (points.length < 2) {
    return null
  }
  const path = points
    .map((value, index) => {
      const x = (index / Math.max(1, points.length - 1)) * width
      const y = height - value * height
      return `${x.toFixed(1)},${y.toFixed(1)}`
    })
    .join(' ')
  return (
    <svg
      aria-label="Biomarker trend"
      height={height}
      role="img"
      style={{ display: 'block' }}
      width={width}
    >
      <title>Biomarker trend</title>
      <polyline
        fill="none"
        points={path}
        stroke={contributing ? 'var(--amber)' : 'var(--slate-2)'}
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={contributing ? 1.6 : 1.2}
      />
    </svg>
  )
}

function ConcordanceRibbon({
  state,
  trace,
  flagAt,
}: {
  state: RibbonState
  trace: ConcordanceTracePoint[]
  flagAt: number | null
}) {
  const width = 1000
  const expanded = state === 'expanded'
  const innerHeight = expanded ? 68 : 34
  const elapsed = trace.at(-1)?.t ?? 0
  const windowSeconds = 180
  const tEnd = Math.max(windowSeconds, Math.ceil(elapsed))
  const tStart = Math.max(0, tEnd - windowSeconds)

  const transcriptLine = trace
    .filter((point) => point.t >= tStart)
    .map((point) => {
      const x = ((point.t - tStart) / windowSeconds) * width
      const y = innerHeight - point.transcriptMin * innerHeight
      return `${x.toFixed(1)},${y.toFixed(1)}`
    })
    .join(' ')

  const strainLine = trace
    .filter((point) => point.t >= tStart)
    .map((point) => {
      const x = ((point.t - tStart) / windowSeconds) * width
      const y = innerHeight - point.acousticStrain * innerHeight
      return `${x.toFixed(1)},${y.toFixed(1)}`
    })
    .join(' ')

  const transcriptValues = trace.filter((point) => point.t >= tStart)
  const divergencePolygon = transcriptValues
    .map((point) => {
      const x = ((point.t - tStart) / windowSeconds) * width
      const y =
        innerHeight -
        Math.min(point.transcriptMin, point.acousticStrain) * innerHeight
      return `${x.toFixed(1)},${y.toFixed(1)}`
    })
    .concat(
      [...transcriptValues].reverse().map((point) => {
        const x = ((point.t - tStart) / windowSeconds) * width
        const y =
          innerHeight -
          Math.max(point.transcriptMin, point.acousticStrain) * innerHeight
        return `${x.toFixed(1)},${y.toFixed(1)}`
      }),
    )
    .join(' ')

  const flagX =
    flagAt !== null && flagAt >= tStart && flagAt <= tEnd
      ? ((flagAt - tStart) / windowSeconds) * width
      : null

  const labelText =
    state === 'idle'
      ? 'Concordance — awaiting call'
      : expanded
        ? 'MINIMIZATION DETECTED'
        : 'Concordance stable'

  return (
    <div
      className={expanded ? 'banner-in' : ''}
      style={{
        background: expanded
          ? 'rgba(219,188,114,0.14)'
          : 'var(--clinic-blue-wash)',
        borderTop: `1px solid ${expanded ? 'rgba(187,142,55,0.35)' : 'var(--clinic-blue-tint)'}`,
        borderBottom: `1px solid ${expanded ? 'rgba(187,142,55,0.35)' : 'var(--clinic-blue-tint)'}`,
        padding: expanded ? '16px 32px 20px 32px' : '8px 32px',
        position: 'relative',
      }}
    >
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          marginBottom: expanded ? 10 : 4,
          gap: 16,
        }}
      >
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 12,
            minWidth: 0,
            flex: '1 1 auto',
          }}
        >
          {expanded ? (
            <span
              aria-hidden
              className="pulse-once"
              style={{
                width: 10,
                height: 10,
                borderRadius: 999,
                background: 'var(--amber)',
                display: 'inline-block',
                flexShrink: 0,
              }}
            />
          ) : null}
          <div
            style={{
              fontSize: expanded ? 15 : 12,
              letterSpacing: expanded ? 1.6 : 1.2,
              textTransform: 'uppercase',
              fontWeight: expanded ? 700 : 600,
              color: expanded ? 'var(--amber)' : 'var(--ink-3)',
              whiteSpace: 'nowrap',
              flexShrink: 0,
            }}
          >
            {labelText}
          </div>
          {expanded ? (
            <div
              style={{
                fontSize: 13,
                color: 'var(--ink-2)',
                fontWeight: 500,
                minWidth: 0,
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                whiteSpace: 'nowrap',
              }}
            >
              Voice is rising; words stay calm. Review rationale and ask 3
              probes.
            </div>
          ) : null}
        </div>
        <div
          className="ribbon-legend"
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 14,
            fontSize: 11,
            color: 'var(--ink-4)',
            letterSpacing: 0.6,
            textTransform: 'uppercase',
            whiteSpace: 'nowrap',
            flexShrink: 0,
          }}
        >
          {state !== 'idle' ? (
            <>
              <span
                style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}
              >
                <span
                  style={{
                    width: 14,
                    height: 2,
                    background: 'var(--clinic-blue-3)',
                    display: 'inline-block',
                  }}
                />
                Transcript min.
              </span>
              <span
                style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}
              >
                <span
                  style={{
                    width: 14,
                    height: 2,
                    background: expanded ? 'var(--amber)' : 'var(--slate)',
                    display: 'inline-block',
                  }}
                />
                Acoustic strain
              </span>
              <span className="tab" style={{ color: 'var(--ink-3)' }}>
                {formatElapsed(tStart)}–{formatElapsed(tEnd)}
              </span>
            </>
          ) : null}
        </div>
      </div>

      <div style={{ position: 'relative', height: innerHeight, width: '100%' }}>
        <svg
          aria-label="Concordance timeline"
          height={innerHeight}
          preserveAspectRatio="none"
          role="img"
          style={{ display: 'block', overflow: 'visible' }}
          viewBox={`0 0 ${width} ${innerHeight}`}
          width="100%"
        >
          <title>Concordance timeline</title>
          <defs>
            <linearGradient id="divGap" x1="0" x2="0" y1="0" y2="1">
              <stop offset="0%" stopColor="rgba(184,122,28,0.55)" />
              <stop offset="100%" stopColor="rgba(184,122,28,0.22)" />
            </linearGradient>
          </defs>
          <line
            stroke="var(--paper-rule)"
            strokeWidth="0.5"
            x1="0"
            x2={width}
            y1={innerHeight - 0.5}
            y2={innerHeight - 0.5}
          />
          {state !== 'idle' && divergencePolygon !== '' ? (
            <polygon
              fill={expanded ? 'url(#divGap)' : 'rgba(160,86,11,0.08)'}
              points={divergencePolygon}
              stroke={expanded ? 'rgba(160,86,11,0.35)' : 'none'}
              strokeWidth="0.5"
            />
          ) : null}
          {state !== 'idle' && transcriptLine !== '' ? (
            <polyline
              fill="none"
              points={transcriptLine}
              stroke="var(--clinic-blue-3)"
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={expanded ? 2 : 1.5}
            />
          ) : null}
          {state !== 'idle' && strainLine !== '' ? (
            <polyline
              fill="none"
              points={strainLine}
              stroke={expanded ? 'var(--amber)' : 'var(--slate)'}
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={expanded ? 2.4 : 1.7}
            />
          ) : null}
          {flagX !== null ? (
            <g>
              <line
                opacity="0.85"
                stroke="var(--amber)"
                strokeDasharray="3 3"
                strokeWidth="1.75"
                x1={flagX}
                x2={flagX}
                y1="-4"
                y2={innerHeight + 2}
              />
              <circle
                cx={flagX}
                cy={
                  innerHeight -
                  (trace.at(-1)?.acousticStrain ?? 0.8) * innerHeight
                }
                fill="var(--amber)"
                r="4.5"
                stroke="#fff"
                strokeWidth="1.5"
              />
            </g>
          ) : null}
        </svg>
        {flagX !== null && expanded ? (
          <div
            className="tab"
            style={{
              position: 'absolute',
              left: `calc(${(flagX / width) * 100}% - 22px)`,
              top: -18,
              fontSize: 10.5,
              color: 'var(--amber)',
              fontWeight: 700,
              letterSpacing: 0.8,
              textTransform: 'uppercase',
              background: 'var(--amber-fill)',
              border: '1px solid var(--amber-rule)',
              padding: '1px 6px',
              borderRadius: 4,
              whiteSpace: 'nowrap',
            }}
          >
            ↓ {formatElapsed(flagAt ?? 0)}
          </div>
        ) : null}
      </div>
    </div>
  )
}

function TranscriptPanel({
  state,
  transcript,
  flagAt,
  transcriptExcerpt,
}: {
  state: TranscriptState
  transcript: LiveScenario['transcript']
  flagAt: number | null
  transcriptExcerpt: LiveScenario['transcriptExcerpt']
}) {
  const listRef = useRef<HTMLDivElement | null>(null)
  const [userScrolled, setUserScrolled] = useState(false)

  useEffect(() => {
    if (userScrolled || transcript.length === 0) {
      return
    }
    const element = listRef.current
    if (element === null) {
      return
    }
    element.scrollTop = element.scrollHeight
  }, [transcript.length, userScrolled])

  const flagCenterIndex =
    transcriptExcerpt === null
      ? -1
      : transcript.findIndex(
          (row) => Math.abs(row.t - transcriptExcerpt.centerT) < 0.51,
        )

  function onScroll(event: React.UIEvent<HTMLDivElement>): void {
    const element = event.currentTarget
    const nearBottom =
      element.scrollHeight - element.scrollTop - element.clientHeight < 48
    setUserScrolled(!nearBottom)
  }

  return (
    <section
      aria-label="Live transcript"
      style={{
        background: 'var(--surface)',
        border: '1px solid var(--paper-rule-soft)',
        borderRadius: 14,
        boxShadow: 'var(--shadow-card)',
        display: 'flex',
        flexDirection: 'column',
        height: '100%',
        position: 'relative',
      }}
    >
      <header
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '14px 20px',
          borderBottom: '1px solid var(--paper-rule-soft)',
        }}
      >
        <SectionLabel>Live transcript</SectionLabel>
        <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
          {state === 'live' ? (
            <span
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: 6,
                fontSize: 11,
                color: 'var(--ink-4)',
                letterSpacing: 0.6,
                textTransform: 'uppercase',
              }}
            >
              <span
                aria-hidden
                style={{
                  width: 6,
                  height: 6,
                  borderRadius: 999,
                  background: 'var(--clinic-blue-3)',
                  animation: 'fade-in 1s ease-in-out infinite alternate',
                }}
              />
              Streaming
            </span>
          ) : null}
          {state === 'ended' ? <Chip tone="muted">Record closed</Chip> : null}
        </div>
      </header>
      <div
        className="scroll"
        onScroll={onScroll}
        ref={listRef}
        style={{
          flex: 1,
          overflowY: 'auto',
          padding: '16px 20px 24px 20px',
          minHeight: 0,
        }}
      >
        {state === 'pre' ? (
          <EmptyTranscript line="Waiting for live audio" />
        ) : null}
        {state === 'connecting' ? <ConnectingTranscript /> : null}
        {(state === 'live' || state === 'ended') && transcript.length === 0 ? (
          <ConnectingTranscript />
        ) : null}
        {state === 'live' || state === 'ended'
          ? transcript.map((row, index) => {
              const isCenter =
                flagAt !== null && Math.abs(row.t - flagAt) < 0.51
              const isNearFlag =
                transcriptExcerpt !== null &&
                flagCenterIndex >= 0 &&
                index >= flagCenterIndex - transcriptExcerpt.spanBefore &&
                index <= flagCenterIndex + transcriptExcerpt.spanAfter
              return (
                <div
                  className="fade-in"
                  key={`${row.t}-${row.s}-${row.text}`}
                  style={{
                    display: 'grid',
                    gridTemplateColumns: '56px 92px 1fr',
                    gap: 14,
                    padding: '10px 8px 10px 12px',
                    borderLeft: isNearFlag
                      ? '4px solid var(--amber)'
                      : '4px solid transparent',
                    background: isCenter
                      ? 'rgba(160,86,11,0.11)'
                      : isNearFlag
                        ? 'rgba(160,86,11,0.05)'
                        : 'transparent',
                    borderRadius: isNearFlag ? 4 : 0,
                    marginBottom: 2,
                    alignItems: 'start',
                  }}
                >
                  <div
                    style={{
                      fontSize: 11,
                      letterSpacing: 1,
                      textTransform: 'uppercase',
                      fontWeight: 600,
                      color:
                        row.s === 'C' ? 'var(--clinic-blue)' : 'var(--ink-2)',
                      paddingTop: 2,
                    }}
                  >
                    {row.s === 'C' ? 'Clinician' : 'Patient'}
                  </div>
                  <div
                    className="tab"
                    style={{
                      fontSize: 12,
                      color: isCenter ? 'var(--amber)' : 'var(--ink-4)',
                      paddingTop: 3,
                      fontWeight: isCenter ? 700 : 400,
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: 6,
                    }}
                  >
                    {isCenter ? (
                      <span
                        aria-hidden
                        style={{
                          width: 8,
                          height: 8,
                          borderRadius: 999,
                          background: 'var(--amber)',
                          boxShadow: '0 0 0 3px rgba(184,122,28,0.22)',
                          display: 'inline-block',
                        }}
                      />
                    ) : null}
                    {formatElapsed(row.t)}
                  </div>
                  <div
                    style={{
                      fontSize: 16,
                      color: 'var(--ink)',
                      lineHeight: 1.5,
                      fontWeight: isCenter ? 600 : row.s === 'C' ? 400 : 500,
                    }}
                  >
                    {row.text}
                  </div>
                </div>
              )
            })
          : null}
      </div>
      {userScrolled && state === 'live' ? (
        <button
          onClick={() => {
            setUserScrolled(false)
          }}
          style={{
            position: 'absolute',
            bottom: 16,
            left: '50%',
            transform: 'translateX(-50%)',
            background: 'var(--clinic-blue)',
            color: '#fff',
            border: 'none',
            padding: '8px 14px',
            borderRadius: 999,
            fontSize: 13,
            fontWeight: 600,
            cursor: 'pointer',
            boxShadow: '0 4px 12px rgba(10,42,107,0.22)',
          }}
          type="button"
        >
          Resume live ↓
        </button>
      ) : null}
    </section>
  )
}

function EmptyTranscript({ line }: { line: string }) {
  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        height: '100%',
        minHeight: 320,
        gap: 10,
        color: 'var(--ink-4)',
      }}
    >
      <div
        aria-hidden
        style={{
          width: 36,
          height: 36,
          borderRadius: 999,
          border: '1px dashed var(--paper-rule)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
        }}
      >
        <div
          style={{
            width: 8,
            height: 8,
            borderRadius: 999,
            background: 'var(--slate-2)',
          }}
        />
      </div>
      <div style={{ fontSize: 14, letterSpacing: 0.2 }}>{line}</div>
      <div style={{ fontSize: 12, color: 'var(--ink-4)', letterSpacing: 0.3 }}>
        Transcript will populate when the call connects.
      </div>
    </div>
  )
}

function ConnectingTranscript() {
  return (
    <div
      style={{
        padding: '12px 8px',
        display: 'flex',
        flexDirection: 'column',
        gap: 14,
      }}
    >
      {[0, 1, 2].map((row) => (
        <div
          key={row}
          style={{
            display: 'grid',
            gridTemplateColumns: '56px 92px 1fr',
            gap: 14,
          }}
        >
          <div
            style={{
              fontSize: 11,
              letterSpacing: 1,
              textTransform: 'uppercase',
              fontWeight: 600,
              color: 'var(--ink-4)',
            }}
          >
            {row % 2 === 0 ? 'Clinician' : 'Patient'}
          </div>
          <div
            className="tab"
            style={{ fontSize: 12, color: 'var(--ink-4)', paddingTop: 3 }}
          >
            —
          </div>
          <div
            style={{ fontSize: 14, color: 'var(--ink-4)', fontStyle: 'italic' }}
          >
            Listening…
          </div>
        </div>
      ))}
    </div>
  )
}

function BiomarkerRail({
  signalSeries,
  latestValues,
  contributingSignals,
  state,
}: {
  signalSeries: Record<string, number[]>
  latestValues: Record<string, number>
  contributingSignals: string[]
  state: TranscriptState
}) {
  return (
    <Card padding={0}>
      <div
        style={{
          padding: '14px 18px',
          borderBottom: '1px solid var(--paper-rule-soft)',
        }}
      >
        <SectionLabel>Live biomarker signals</SectionLabel>
      </div>
      <div>
        {biomarkerOrder.map((name, index) => {
          const key = signalValueKeys[name]
          const series = signalSeries[key] ?? []
          const currentValue = latestValues[key]
          const contributing = contributingSignals.includes(name)
          const warming = state === 'connecting'
          const score =
            state === 'pre'
              ? '—'
              : warming || series.length === 0
                ? '··'
                : (currentValue * 10).toFixed(1)
          return (
            <div
              key={name}
              style={{
                display: 'grid',
                gridTemplateColumns: '1fr 130px 62px',
                alignItems: 'center',
                gap: 14,
                padding: '13px 18px',
                borderTop:
                  index === 0 ? 'none' : '1px solid var(--paper-rule-soft)',
                opacity: state === 'pre' ? 0.55 : 1,
              }}
            >
              <div
                style={{
                  fontSize: 14,
                  fontWeight: contributing ? 600 : 500,
                  color: contributing ? 'var(--amber)' : 'var(--ink-2)',
                  letterSpacing: 0.1,
                }}
              >
                {name}
              </div>
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'flex-end',
                }}
              >
                {state === 'pre' ? (
                  <span
                    style={{
                      fontSize: 11,
                      color: 'var(--ink-4)',
                      letterSpacing: 0.6,
                      textTransform: 'uppercase',
                    }}
                  >
                    standby
                  </span>
                ) : warming ? (
                  <span
                    style={{
                      fontSize: 11,
                      color: 'var(--ink-4)',
                      letterSpacing: 0.6,
                      textTransform: 'uppercase',
                    }}
                  >
                    warming up
                  </span>
                ) : series.length === 0 ? (
                  <span
                    style={{
                      fontSize: 11,
                      color: 'var(--ink-4)',
                      letterSpacing: 0.6,
                      textTransform: 'uppercase',
                    }}
                  >
                    signal delayed
                  </span>
                ) : (
                  <Sparkline
                    contributing={contributing}
                    points={series}
                    width={130}
                    height={16}
                  />
                )}
              </div>
              <div style={{ fontSize: 13, textAlign: 'right' }}>
                <span
                  className="tab"
                  style={{
                    display: 'inline-block',
                    background: contributing
                      ? 'var(--amber-fill-soft)'
                      : 'transparent',
                    color: contributing ? 'var(--amber)' : 'var(--ink-2)',
                    border: `1px solid ${contributing ? 'var(--amber-rule)' : 'var(--paper-rule)'}`,
                    padding: '2px 8px',
                    borderRadius: 6,
                    fontWeight: 600,
                    minWidth: 44,
                  }}
                >
                  {score}
                </span>
              </div>
            </div>
          )
        })}
      </div>
    </Card>
  )
}

function AssessmentCard({
  flagFired,
  liveScenario,
  probeAnswers,
  pdfState,
  pdfTimestamp,
  onWhyFlagged,
  onOpenProbes,
  onGenerate,
}: {
  flagFired: boolean
  liveScenario: LiveScenario
  probeAnswers: [string, string, string] | null
  pdfState: 'none' | 'generated' | 'sent'
  pdfTimestamp: string | null
  onWhyFlagged: () => void
  onOpenProbes: () => void
  onGenerate: () => void
}) {
  const pdfLabel =
    pdfState === 'sent'
      ? `Sent · ${pdfTimestamp ?? ''}`
      : pdfState === 'generated'
        ? `PDF generated · ${pdfTimestamp ?? ''}`
        : 'Generate handoff PDF'

  return (
    <Card padding={0}>
      <div
        style={{
          padding: '14px 18px',
          borderBottom: '1px solid var(--paper-rule-soft)',
        }}
      >
        <SectionLabel>Assessment & handoff</SectionLabel>
      </div>
      <div
        style={{
          padding: 18,
          display: 'flex',
          flexDirection: 'column',
          gap: 10,
        }}
      >
        <Btn
          disabled={!flagFired}
          full
          kind={flagFired ? 'primary' : 'ghost'}
          onClick={onWhyFlagged}
        >
          <ActionRow
            meta={
              flagFired && liveScenario.flagAt !== null
                ? `At ${formatElapsed(liveScenario.flagAt)} · Confidence ${liveScenario.confidence.toLowerCase()}`
                : 'Active only when a flag fires'
            }
            primary={flagFired}
            title="Why flagged?"
          />
        </Btn>
        <Btn
          disabled={!flagFired}
          full
          kind={flagFired ? 'primary' : 'ghost'}
          onClick={onOpenProbes}
        >
          <ActionRow
            meta={
              probeAnswers
                ? 'Responses saved'
                : flagFired
                  ? 'Structured follow-up questions'
                  : 'Active only when a flag fires'
            }
            primary={flagFired}
            title="Open 3 probes"
          />
        </Btn>
        <Btn
          full
          kind={probeAnswers ? 'primary' : 'secondary'}
          onClick={onGenerate}
        >
          <ActionRow
            meta={
              probeAnswers
                ? 'Ready for review'
                : 'Draft available; secondary until probes reviewed'
            }
            primary={Boolean(probeAnswers)}
            title={pdfLabel}
          />
        </Btn>
      </div>
    </Card>
  )
}

function ActionRow({
  title,
  meta,
  primary,
}: {
  title: string
  meta: string
  primary: boolean
}) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
      <div style={{ fontSize: 15, fontWeight: 600, letterSpacing: 0.1 }}>
        {title}
      </div>
      <div
        style={{
          fontSize: 12,
          fontWeight: 400,
          color: primary ? 'rgba(255,255,255,0.78)' : 'var(--ink-4)',
          letterSpacing: 0.1,
        }}
      >
        {meta}
      </div>
    </div>
  )
}

function Scrim({
  align = 'center',
  children,
  onClose,
}: {
  align?: 'center' | 'right'
  children: React.ReactNode
  onClose: () => void
}) {
  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        onClose()
      }
    }
    window.addEventListener('keydown', onKey)
    return () => {
      window.removeEventListener('keydown', onKey)
    }
  }, [onClose])

  return (
    <div
      className="fade-in"
      style={{
        position: 'fixed',
        inset: 0,
        background: 'rgba(11,18,32,0.42)',
        backdropFilter: 'blur(6px)',
        WebkitBackdropFilter: 'blur(6px)',
        zIndex: 100,
        display: 'flex',
        alignItems: 'center',
        justifyContent: align === 'right' ? 'flex-end' : 'center',
      }}
    >
      <button
        aria-label="Close dialog backdrop"
        onClick={onClose}
        style={{
          position: 'absolute',
          inset: 0,
          border: 'none',
          background: 'transparent',
          padding: 0,
        }}
        type="button"
      />
      <div style={{ position: 'relative', zIndex: 1 }}>{children}</div>
    </div>
  )
}

function WhyFlaggedModal({
  liveScenario,
  onClose,
}: {
  liveScenario: LiveScenario
  onClose: () => void
}) {
  return (
    <Scrim align="right" onClose={onClose}>
      <aside
        className="sheet-in"
        style={{
          width: 480,
          maxWidth: '100%',
          height: '100%',
          background: 'var(--surface)',
          borderLeft: '1px solid var(--paper-rule)',
          boxShadow: 'var(--shadow-modal)',
          display: 'flex',
          flexDirection: 'column',
        }}
      >
        <header
          style={{
            padding: '20px 24px',
            borderBottom: '1px solid var(--paper-rule-soft)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
          }}
        >
          <div>
            <SectionLabel style={{ marginBottom: 4 }}>Assessment</SectionLabel>
            <h2
              style={{
                margin: 0,
                fontSize: 20,
                fontWeight: 700,
                letterSpacing: -0.2,
              }}
            >
              Why this was flagged
            </h2>
          </div>
          <button
            onClick={onClose}
            style={{
              width: 32,
              height: 32,
              borderRadius: 6,
              border: '1px solid var(--paper-rule)',
              background: 'transparent',
              color: 'var(--ink-2)',
              fontSize: 16,
            }}
            type="button"
          >
            ×
          </button>
        </header>
        <div
          style={{
            padding: 24,
            display: 'flex',
            flexDirection: 'column',
            gap: 20,
            overflowY: 'auto',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <SectionLabel>Confidence</SectionLabel>
            <Chip tone="amber">{liveScenario.confidence}</Chip>
            <span
              className="tab"
              style={{ fontSize: 12, color: 'var(--ink-4)' }}
            >
              Flagged at {formatElapsed(liveScenario.flagAt ?? 0)}
            </span>
          </div>
          <div>
            <SectionLabel style={{ marginBottom: 8 }}>
              Plain-English drivers
            </SectionLabel>
            <ol
              style={{
                margin: 0,
                padding: '0 0 0 20px',
                color: 'var(--ink)',
                fontSize: 15,
                lineHeight: 1.55,
              }}
            >
              {liveScenario.drivers.map((driver) => (
                <li key={driver} style={{ marginBottom: 10, paddingLeft: 4 }}>
                  {driver}
                </li>
              ))}
            </ol>
          </div>
          <div
            style={{
              padding: '14px 16px',
              background: 'var(--amber-fill-soft)',
              border: '1px solid var(--amber-rule)',
              borderRadius: 8,
            }}
          >
            <div
              style={{
                fontSize: 12,
                letterSpacing: 0.6,
                textTransform: 'uppercase',
                color: 'var(--amber)',
                fontWeight: 600,
                marginBottom: 4,
              }}
            >
              Suggested next step
            </div>
            <div style={{ fontSize: 14, color: 'var(--ink)' }}>
              Ask the 3 probes to confirm or rule out. Responses feed the
              handoff PDF.
            </div>
          </div>
        </div>
        <footer
          style={{
            padding: '16px 24px',
            borderTop: '1px solid var(--paper-rule-soft)',
            display: 'flex',
            justifyContent: 'flex-end',
          }}
        >
          <Btn kind="ghost" onClick={onClose}>
            Close
          </Btn>
        </footer>
      </aside>
    </Scrim>
  )
}

function ProbesModal({
  initial,
  onClose,
  onSave,
}: {
  initial: [string, string, string] | null
  onClose: () => void
  onSave: (answers: [string, string, string]) => void
}) {
  const [answers, setAnswers] = useState<
    [string | null, string | null, string | null]
  >(initial ?? [null, null, null])
  const complete = answers.every((answer) => answer !== null)

  return (
    <Scrim onClose={onClose}>
      <div
        className="modal-in"
        style={{
          width: 680,
          maxWidth: '92vw',
          maxHeight: '88vh',
          background: 'var(--surface)',
          border: '1px solid var(--paper-rule)',
          borderRadius: 16,
          boxShadow: 'var(--shadow-modal)',
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden',
        }}
      >
        <header
          style={{
            padding: '22px 28px',
            borderBottom: '1px solid var(--paper-rule-soft)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
          }}
        >
          <div>
            <SectionLabel style={{ marginBottom: 4 }}>
              Structured follow-up
            </SectionLabel>
            <h2
              style={{
                margin: 0,
                fontSize: 20,
                fontWeight: 700,
                letterSpacing: -0.2,
              }}
            >
              3 probes
            </h2>
          </div>
          <button
            onClick={onClose}
            style={{
              width: 32,
              height: 32,
              borderRadius: 6,
              border: '1px solid var(--paper-rule)',
              background: 'transparent',
              color: 'var(--ink-2)',
              fontSize: 16,
            }}
            type="button"
          >
            ×
          </button>
        </header>
        <div style={{ padding: '14px 28px 20px 28px', overflowY: 'auto' }}>
          {probeDefinitions.map((probe, index) => (
            <div
              key={probe.question}
              style={{
                padding: '16px 0',
                borderTop:
                  index === 0 ? 'none' : '1px solid var(--paper-rule-soft)',
              }}
            >
              <div
                style={{
                  display: 'flex',
                  alignItems: 'baseline',
                  gap: 10,
                  marginBottom: 12,
                }}
              >
                <span
                  className="tab"
                  style={{
                    fontSize: 12,
                    color: 'var(--ink-4)',
                    fontWeight: 600,
                    letterSpacing: 0.4,
                  }}
                >
                  0{index + 1}
                </span>
                <div
                  style={{
                    fontSize: 17,
                    fontWeight: 500,
                    color: 'var(--ink)',
                    lineHeight: 1.4,
                  }}
                >
                  {probe.question}
                </div>
              </div>
              <div
                style={{
                  display: 'grid',
                  gridTemplateColumns: '1fr 1fr 1fr',
                  gap: 10,
                }}
              >
                {probe.options.map((option) => {
                  const selected = answers[index] === option
                  return (
                    <button
                      key={option}
                      onClick={() => {
                        const nextAnswers: [
                          string | null,
                          string | null,
                          string | null,
                        ] = [...answers]
                        nextAnswers[index] = option
                        setAnswers(nextAnswers)
                      }}
                      style={{
                        padding: '14px 14px',
                        borderRadius: 8,
                        background: selected
                          ? 'var(--clinic-blue)'
                          : 'transparent',
                        color: selected ? '#fff' : 'var(--ink-2)',
                        border: `1px solid ${selected ? 'var(--clinic-blue)' : 'var(--paper-rule)'}`,
                        fontSize: 14,
                        fontWeight: 500,
                        textAlign: 'left',
                        transition:
                          'background 140ms, color 140ms, border 140ms',
                      }}
                      type="button"
                    >
                      {option}
                    </button>
                  )
                })}
              </div>
            </div>
          ))}
        </div>
        <footer
          style={{
            padding: '16px 28px',
            borderTop: '1px solid var(--paper-rule-soft)',
            display: 'flex',
            gap: 10,
            justifyContent: 'space-between',
            alignItems: 'center',
          }}
        >
          <div style={{ fontSize: 12, color: 'var(--ink-4)' }}>
            {complete
              ? 'All three captured. Saving writes back to the call record.'
              : `${answers.filter((answer) => answer !== null).length}/3 answered`}
          </div>
          <div style={{ display: 'flex', gap: 10 }}>
            <Btn kind="ghost" onClick={onClose}>
              Cancel
            </Btn>
            <Btn
              disabled={!complete}
              kind="primary"
              onClick={() => {
                if (answers[0] && answers[1] && answers[2]) {
                  onSave([answers[0], answers[1], answers[2]])
                }
              }}
            >
              Save responses
            </Btn>
          </div>
        </footer>
      </div>
    </Scrim>
  )
}

function HandoffModal({
  elapsedSeconds,
  generatedAt,
  liveScenario,
  onClose,
  probeAnswers,
  triageState,
  callStartedAt,
  callEndedAt,
  onOpenPdf,
}: {
  elapsedSeconds: number
  generatedAt: Date
  liveScenario: LiveScenario
  onClose: () => void
  probeAnswers: [string, string, string] | null
  triageState: 'awaiting' | 'green' | 'amber' | 'red'
  callStartedAt: Date | null
  callEndedAt: Date | null
  onOpenPdf: () => void
}) {
  const generatedLabel = `${formatDateLong(generatedAt)} · ${formatClock(generatedAt)}`
  const callDate = callStartedAt
    ? `${formatDateLong(callStartedAt)} · ${formatClock(callStartedAt)}`
    : '—'
  const totalSeconds =
    callStartedAt !== null && callEndedAt !== null
      ? Math.max(
          0,
          Math.round((callEndedAt.getTime() - callStartedAt.getTime()) / 1000),
        )
      : Math.max(0, Math.round(elapsedSeconds))
  const flagLabel =
    liveScenario.flagAt === null ? '—' : formatElapsed(liveScenario.flagAt)
  const excerpt = findTranscriptExcerpt(
    liveScenario.transcript,
    liveScenario.flagAt,
  )
  const triageLabel = getTriageLabel(triageState)

  return (
    <Scrim onClose={onClose}>
      <div
        className="modal-in"
        style={{
          width: 900,
          maxWidth: '96vw',
          height: '90vh',
          background: 'var(--paper-2)',
          border: '1px solid var(--paper-rule)',
          borderRadius: 14,
          boxShadow: 'var(--shadow-modal)',
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden',
        }}
      >
        <header
          style={{
            padding: '14px 20px',
            borderBottom: '1px solid var(--paper-rule-soft)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            background: 'var(--paper-3)',
          }}
        >
          <SectionLabel>Handoff preview · read-only</SectionLabel>
          <div style={{ display: 'flex', gap: 8 }}>
            <Btn kind="ghost" onClick={onClose}>
              Close
            </Btn>
            <Btn kind="primary" onClick={onOpenPdf}>
              Open generated PDF
            </Btn>
          </div>
        </header>
        <div
          className="scroll"
          style={{
            flex: 1,
            overflowY: 'auto',
            padding: '24px 32px',
            display: 'flex',
            justifyContent: 'center',
          }}
        >
          <div
            style={{
              width: 760,
              minHeight: '100%',
              background: 'var(--surface)',
              border: '1px solid var(--paper-rule-soft)',
              borderRadius: 6,
              padding: '44px 52px',
              boxShadow: '0 2px 18px rgba(11,18,32,0.08)',
            }}
          >
            <div
              style={{
                borderBottom: '2px solid var(--clinic-blue)',
                paddingBottom: 12,
                marginBottom: 18,
              }}
            >
              <div
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'baseline',
                }}
              >
                <div>
                  <div
                    style={{
                      fontSize: 10,
                      letterSpacing: 1.4,
                      textTransform: 'uppercase',
                      color: 'var(--clinic-blue)',
                      fontWeight: 700,
                    }}
                  >
                    Postnatal Pulse
                  </div>
                  <h1
                    style={{
                      fontSize: 22,
                      margin: '4px 0 0 0',
                      fontWeight: 700,
                      letterSpacing: -0.2,
                      color: 'var(--ink)',
                    }}
                  >
                    Postnatal Call Handoff Summary
                  </h1>
                </div>
                <div
                  className="tab"
                  style={{
                    fontSize: 11,
                    color: 'var(--ink-3)',
                    textAlign: 'right',
                    lineHeight: 1.5,
                  }}
                >
                  Generated {generatedLabel}
                  <br />
                  Clinician: {runtime.CLINICIAN}
                </div>
              </div>
            </div>

            <div
              style={{
                display: 'grid',
                gridTemplateColumns: '1fr 1fr',
                gap: '6px 32px',
                fontSize: 13,
                color: 'var(--ink)',
                marginBottom: 18,
              }}
            >
              <MetaRow
                k="Patient"
                v={`${runtime.PATIENT.name}, ${runtime.PATIENT.age}`}
              />
              <MetaRow k="Call date" v={callDate} />
              <MetaRow k="Postpartum" v={runtime.PATIENT.weeks} />
              <MetaRow k="Call duration" v={formatElapsed(totalSeconds)} />
              <MetaRow k="Baby" v={runtime.PATIENT.baby} />
              <MetaRow k="Visit reason" v={runtime.PATIENT.reason} />
            </div>

            <ReportSection title="Current triage">
              <div
                style={{
                  display: 'flex',
                  gap: 16,
                  alignItems: 'center',
                  fontSize: 14,
                }}
              >
                <TriageInline triage={triageState} />
                <div
                  className="tab"
                  style={{ color: 'var(--ink-3)', fontSize: 12 }}
                >
                  Flagged at {flagLabel}
                  {triageState !== 'awaiting' ? ' · Handoff ready' : ''}
                </div>
              </div>
            </ReportSection>

            <ReportSection title="Why this was flagged">
              <p
                style={{
                  margin: 0,
                  fontSize: 13.5,
                  lineHeight: 1.55,
                  color: 'var(--ink)',
                }}
              >
                {liveScenario.rationale.join(' ')} The divergence between
                reassuring spoken content and sustained acoustic strain was
                first detected at {flagLabel}, triggering a MINIMIZATION
                DETECTED event. Handoff escalated to {triageLabel.toLowerCase()}
                .
              </p>
            </ReportSection>

            <ReportSection title="Probe responses">
              {probeAnswers !== null ? (
                <div
                  style={{
                    display: 'flex',
                    flexDirection: 'column',
                    gap: 10,
                    fontSize: 13,
                  }}
                >
                  {probeDefinitions.map((probe, index) => (
                    <div key={probe.question}>
                      <div style={{ color: 'var(--ink-2)', fontWeight: 500 }}>
                        {index + 1}. {probe.question}
                      </div>
                      <div
                        style={{
                          color: 'var(--ink)',
                          paddingLeft: 14,
                          paddingTop: 2,
                        }}
                      >
                        <span
                          style={{ color: 'var(--ink-3)', fontWeight: 500 }}
                        >
                          Response:
                        </span>{' '}
                        {probeAnswers[index]}
                      </div>
                    </div>
                  ))}
                  <div
                    className="tab"
                    style={{
                      fontSize: 11,
                      color: 'var(--ink-4)',
                      marginTop: 4,
                    }}
                  >
                    Saved {formatClock(generatedAt)}
                  </div>
                </div>
              ) : (
                <div
                  style={{
                    fontSize: 13,
                    color: 'var(--ink-4)',
                    fontStyle: 'italic',
                  }}
                >
                  Probes not yet captured.
                </div>
              )}
            </ReportSection>

            <ReportSection
              subtitle={
                liveScenario.flagAt !== null
                  ? `Centred on ${flagLabel} trigger window`
                  : ''
              }
              title="Transcript excerpt"
            >
              {excerpt.length > 0 ? (
                <div style={{ fontSize: 13, lineHeight: 1.55 }}>
                  {excerpt.map((row) => {
                    const isTrigger = row.t === liveScenario.flagAt
                    return (
                      <div
                        key={`${row.t}-${row.s}-${row.text}`}
                        style={{
                          display: 'grid',
                          gridTemplateColumns: '74px 56px 1fr',
                          gap: 10,
                          padding: '3px 0',
                          background: isTrigger
                            ? 'rgba(160,86,11,0.08)'
                            : 'transparent',
                          borderLeft: isTrigger
                            ? '2px solid var(--amber)'
                            : '2px solid transparent',
                          paddingLeft: 8,
                        }}
                      >
                        <span
                          style={{
                            fontSize: 11,
                            letterSpacing: 0.8,
                            textTransform: 'uppercase',
                            color:
                              row.s === 'C'
                                ? 'var(--clinic-blue)'
                                : 'var(--ink-2)',
                            fontWeight: 600,
                            paddingTop: 2,
                          }}
                        >
                          {row.s === 'C' ? 'Clinician' : 'Patient'}
                        </span>
                        <span
                          className="tab"
                          style={{
                            fontSize: 12,
                            color: 'var(--ink-4)',
                            paddingTop: 2,
                          }}
                        >
                          {formatElapsed(row.t)}
                        </span>
                        <span>{row.text}</span>
                      </div>
                    )
                  })}
                </div>
              ) : (
                <div
                  style={{
                    fontSize: 13,
                    color: 'var(--ink-4)',
                    fontStyle: 'italic',
                  }}
                >
                  No flagged window in this call.
                </div>
              )}
            </ReportSection>

            <div
              style={{
                marginTop: 32,
                borderTop: '1px solid var(--paper-rule)',
                paddingTop: 14,
                fontSize: 11,
                color: 'var(--ink-3)',
                fontStyle: 'italic',
                lineHeight: 1.55,
              }}
            >
              Decision-support summary generated from live call signals and
              transcript excerpts for clinician review only. This document is
              not a diagnosis and does not replace clinical judgment,
              safeguarding procedure, or local perinatal mental health pathways.
              Confirm details against the full conversation before acting.
            </div>
          </div>
        </div>
      </div>
    </Scrim>
  )
}

function MetaRow({ k, v }: { k: string; v: string }) {
  return (
    <div style={{ display: 'flex', gap: 10, alignItems: 'baseline' }}>
      <div
        style={{
          fontSize: 11,
          textTransform: 'uppercase',
          letterSpacing: 0.8,
          color: 'var(--ink-4)',
          fontWeight: 600,
          minWidth: 88,
        }}
      >
        {k}
      </div>
      <div style={{ fontSize: 13, color: 'var(--ink)' }}>{v}</div>
    </div>
  )
}

function TriageInline({
  triage,
}: {
  triage: 'awaiting' | 'green' | 'amber' | 'red'
}) {
  const config = {
    green: {
      label: 'Green: routine',
      bg: 'var(--green-fill)',
      fg: 'var(--green)',
      rule: '#b6cdb2',
    },
    amber: {
      label: 'Amber: review',
      bg: 'var(--amber-fill)',
      fg: 'var(--amber)',
      rule: 'var(--amber-rule)',
    },
    red: {
      label: 'Red: urgent review',
      bg: 'var(--red-fill)',
      fg: 'var(--red)',
      rule: '#c78880',
    },
    awaiting: {
      label: 'Awaiting call',
      bg: 'var(--paper-3)',
      fg: 'var(--ink-3)',
      rule: 'var(--paper-rule)',
    },
  }[triage]

  return (
    <span
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: 8,
        background: config.bg,
        color: config.fg,
        border: `1px solid ${config.rule}`,
        padding: '4px 12px',
        borderRadius: 999,
        fontWeight: 600,
        fontSize: 13,
      }}
    >
      <span
        style={{
          width: 7,
          height: 7,
          borderRadius: 999,
          background: config.fg,
          display: 'inline-block',
        }}
      />
      {config.label}
    </span>
  )
}

function ReportSection({
  title,
  subtitle,
  children,
}: {
  title: string
  subtitle?: string
  children: React.ReactNode
}) {
  return (
    <section style={{ marginBottom: 20 }}>
      <div
        style={{
          borderBottom: '1px solid var(--clinic-blue-tint)',
          paddingBottom: 4,
          marginBottom: 10,
          display: 'flex',
          alignItems: 'baseline',
          justifyContent: 'space-between',
        }}
      >
        <div
          style={{
            fontSize: 11,
            letterSpacing: 1.4,
            textTransform: 'uppercase',
            color: 'var(--clinic-blue)',
            fontWeight: 700,
          }}
        >
          {title}
        </div>
        {subtitle ? (
          <div style={{ fontSize: 11, color: 'var(--ink-4)' }}>{subtitle}</div>
        ) : null}
      </div>
      {children}
    </section>
  )
}

function DevDrawer({
  onAttachLive,
  onClose,
  onPickScenario,
  open,
  scenarios,
}: {
  onAttachLive: () => void
  onClose: () => void
  onPickScenario: (scenarioId: string) => void
  open: boolean
  scenarios: {
    id: string
    label: string
    flag_at_t: number | null
    has_flag: boolean
  }[]
}) {
  if (!open) {
    return null
  }
  return (
    <div
      className="fade-in"
      style={{
        position: 'fixed',
        bottom: 20,
        left: 20,
        zIndex: 80,
        background: 'var(--paper)',
        border: '1px solid var(--paper-rule)',
        borderRadius: 10,
        boxShadow: 'var(--shadow-modal)',
        padding: 16,
        minWidth: 300,
      }}
    >
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: 10,
        }}
      >
        <SectionLabel>Demo scenarios · Shift+D</SectionLabel>
        <button
          onClick={onClose}
          style={{
            width: 22,
            height: 22,
            border: '1px solid var(--paper-rule)',
            borderRadius: 4,
            background: 'transparent',
            color: 'var(--ink-2)',
            fontSize: 12,
            cursor: 'pointer',
          }}
          type="button"
        >
          ×
        </button>
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
        <Btn full kind="secondary" onClick={onAttachLive}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
            <div style={{ fontWeight: 600, fontSize: 13 }}>
              Attach latest live call
            </div>
            <div style={{ fontSize: 11, color: 'var(--ink-4)' }}>
              Browser/Twilio live stream
            </div>
          </div>
        </Btn>
        {scenarios.map((scenario) => (
          <Btn
            full
            key={scenario.id}
            kind="secondary"
            onClick={() => {
              onPickScenario(scenario.id)
            }}
          >
            <div style={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
              <div style={{ fontWeight: 600, fontSize: 13 }}>
                {scenario.label}
              </div>
              <div style={{ fontSize: 11, color: 'var(--ink-4)' }}>
                {scenario.has_flag && scenario.flag_at_t !== null
                  ? `Flag at ${formatElapsed(scenario.flag_at_t)}`
                  : 'No flag'}
              </div>
            </div>
          </Btn>
        ))}
      </div>
    </div>
  )
}

function App() {
  const eventSourceRef = useRef<EventSource | null>(null)
  const [whyOpen, setWhyOpen] = useState(false)
  const [probesOpen, setProbesOpen] = useState(false)
  const [handoffOpen, setHandoffOpen] = useState(false)
  const [handoffUrl, setHandoffUrl] = useState<string | null>(null)
  const [handoffGeneratedAt, setHandoffGeneratedAt] = useState<Date | null>(
    null,
  )
  const [pdfState, setPdfState] = useState<'none' | 'generated' | 'sent'>(
    'none',
  )
  const [pdfTimestamp, setPdfTimestamp] = useState<string | null>(null)
  const [probeAnswers, setProbeAnswers] = useState<
    [string, string, string] | null
  >(null)
  const [callStartedAt, setCallStartedAt] = useState<Date | null>(null)
  const [callEndedAt, setCallEndedAt] = useState<Date | null>(null)

  const {
    applyEvent,
    attachLatestCall,
    beginCall,
    callId,
    callPhase,
    callState,
    drawerOpen,
    errorMessage,
    latestEventT,
    resetCall,
    scenarios,
    selectedScenarioId,
    setDrawerOpen,
    setErrorMessage,
    setScenarios,
    setSelectedScenarioId,
  } = useCallStore()

  useEffect(() => {
    void fetchScenarios()
      .then((nextScenarios) => {
        setScenarios(nextScenarios)
      })
      .catch(() => {
        setErrorMessage('Could not load scenarios')
      })
  }, [setErrorMessage, setScenarios])

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (event.shiftKey && (event.key === 'D' || event.key === 'd')) {
        event.preventDefault()
        setDrawerOpen(!drawerOpen)
      }
    }
    window.addEventListener('keydown', onKey)
    return () => {
      window.removeEventListener('keydown', onKey)
    }
  }, [drawerOpen, setDrawerOpen])

  useEffect(() => {
    return () => {
      eventSourceRef.current?.close()
    }
  }, [])

  useEffect(() => {
    if (callStartedAt === null && callPhase !== 'pre' && latestEventT > 0) {
      setCallStartedAt(new Date(Date.now() - latestEventT * 1000))
    }
  }, [callPhase, callStartedAt, latestEventT])

  useEffect(() => {
    if (callPhase === 'ended' && callEndedAt === null) {
      setCallEndedAt(new Date())
    }
  }, [callEndedAt, callPhase])

  const signalSeries = useMemo(
    () => deriveSignalSeries(callState.biomarkerSnapshots),
    [callState.biomarkerSnapshots],
  )
  const latestBiomarkerValues = useMemo(
    () => deriveLatestBiomarkerValues(callState.biomarkerSnapshots),
    [callState.biomarkerSnapshots],
  )
  const liveScenario = useMemo(
    () => deriveLiveScenario(callState, selectedScenarioId),
    [callState, selectedScenarioId],
  )
  const flagFired = callState.flag !== null
  const triageState = (callState.triage?.state ?? 'awaiting') as
    | 'awaiting'
    | 'green'
    | 'amber'
    | 'red'
  const transcriptState = getTranscriptState(callPhase, callState.transcripts)
  const ribbonState = getRibbonState(flagFired, callPhase)

  function connectToCallStream(sseUrl: string): void {
    const eventSource = new EventSource(buildEventSourceUrl(sseUrl))
    let receivedEnd = false
    eventSourceRef.current = eventSource

    eventSource.addEventListener('triage', (event) => {
      applyEvent({
        type: 'triage',
        data: parseSseEvent<Extract<CallSseEvent, { type: 'triage' }>['data']>(
          event as MessageEvent<string>,
        ),
      })
    })
    eventSource.addEventListener('transcript', (event) => {
      applyEvent({
        type: 'transcript',
        data: parseSseEvent<
          Extract<CallSseEvent, { type: 'transcript' }>['data']
        >(event as MessageEvent<string>),
      })
    })
    eventSource.addEventListener('flag', (event) => {
      applyEvent({
        type: 'flag',
        data: parseSseEvent<Extract<CallSseEvent, { type: 'flag' }>['data']>(
          event as MessageEvent<string>,
        ),
      })
    })
    eventSource.addEventListener('rationale_done', (event) => {
      applyEvent({
        type: 'rationale_done',
        data: parseSseEvent<
          Extract<CallSseEvent, { type: 'rationale_done' }>['data']
        >(event as MessageEvent<string>),
      })
    })
    eventSource.addEventListener('biomarker', (event) => {
      applyEvent({
        type: 'biomarker',
        data: parseSseEvent<
          Extract<CallSseEvent, { type: 'biomarker' }>['data']
        >(event as MessageEvent<string>),
      })
    })
    eventSource.addEventListener('concordance_trace', (event) => {
      applyEvent({
        type: 'concordance_trace',
        data: parseSseEvent<
          Extract<CallSseEvent, { type: 'concordance_trace' }>['data']
        >(event as MessageEvent<string>),
      })
    })
    eventSource.addEventListener('system', (event) => {
      applyEvent({
        type: 'system',
        data: parseSseEvent<Extract<CallSseEvent, { type: 'system' }>['data']>(
          event as MessageEvent<string>,
        ),
      })
    })
    eventSource.addEventListener('end', (event) => {
      receivedEnd = true
      applyEvent({
        type: 'end',
        data: parseSseEvent<Extract<CallSseEvent, { type: 'end' }>['data']>(
          event as MessageEvent<string>,
        ),
      })
      eventSource.close()
      eventSourceRef.current = null
    })

    eventSource.onerror = () => {
      if (receivedEnd || eventSource.readyState === EventSource.CLOSED) {
        return
      }
      setErrorMessage('Stream disconnected')
      eventSource.close()
      eventSourceRef.current = null
    }
  }

  async function startScenario(scenarioId: string): Promise<void> {
    eventSourceRef.current?.close()
    resetCall()
    setSelectedScenarioId(scenarioId)
    setDrawerOpen(false)
    setCallStartedAt(new Date())
    setCallEndedAt(null)
    setHandoffGeneratedAt(null)
    setPdfState('none')
    setPdfTimestamp(null)
    setProbeAnswers(null)
    try {
      const startedCall = await startFixtureCall(scenarioId)
      beginCall(startedCall.call_id)
      connectToCallStream(startedCall.sse_url)
    } catch {
      setErrorMessage('Could not start fixture replay')
    }
  }

  async function attachLatestLiveCall(): Promise<void> {
    eventSourceRef.current?.close()
    resetCall()
    setDrawerOpen(false)
    setSelectedScenarioId(null)
    setCallStartedAt(null)
    setCallEndedAt(null)
    setHandoffGeneratedAt(null)
    setPdfState('none')
    setPdfTimestamp(null)
    setProbeAnswers(null)
    try {
      const latestCall = await fetchLatestCall()
      attachLatestCall(latestCall)
      connectToCallStream(latestCall.sse_url)
    } catch {
      setErrorMessage('Could not attach to latest live call')
    }
  }

  async function submitProbeAnswers(
    nextAnswers: [string, string, string],
  ): Promise<void> {
    if (callId === null || callState.flag === null) {
      return
    }
    try {
      const response = await saveProbeAnswers(
        callId,
        callState.flag.flagId,
        nextAnswers,
      )
      applyEvent({ type: 'flag', data: response.flag })
      applyEvent({ type: 'triage', data: response.triage })
      setProbeAnswers(nextAnswers)
      setProbesOpen(false)
    } catch {
      setErrorMessage('Could not save probe responses')
    }
  }

  async function openHandoffPreview(): Promise<void> {
    if (callId === null) {
      return
    }
    try {
      const response = await generateHandoff(callId)
      const generatedAt = new Date()
      setHandoffUrl(
        new URL(
          response.preview_url,
          import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000',
        ).toString(),
      )
      setHandoffGeneratedAt(generatedAt)
      setPdfState('generated')
      setPdfTimestamp(formatClock(generatedAt))
      setHandoffOpen(true)
    } catch {
      setErrorMessage('Could not generate handoff PDF')
    }
  }

  return (
    <div
      style={{
        minHeight: '100vh',
        background: 'var(--paper)',
        display: 'flex',
        flexDirection: 'column',
      }}
    >
      <TopStrip
        callPhase={
          callPhase as 'pre' | 'connecting' | 'live' | 'ended' | 'error'
        }
        elapsed={latestEventT}
        flagAt={liveScenario.flagAt}
        flagFired={flagFired}
        triage={triageState}
      />
      <ConcordanceRibbon
        flagAt={liveScenario.flagAt}
        state={ribbonState}
        trace={callState.concordanceTrace}
      />

      <main
        style={{
          flex: 1,
          display: 'grid',
          gridTemplateColumns: 'minmax(0, 1fr) 400px',
          gap: 20,
          padding: '20px 32px 24px 32px',
          minHeight: 0,
        }}
      >
        <div
          style={{ minHeight: 560, display: 'flex', flexDirection: 'column' }}
        >
          <TranscriptPanel
            flagAt={liveScenario.flagAt}
            state={transcriptState}
            transcript={liveScenario.transcript}
            transcriptExcerpt={liveScenario.transcriptExcerpt}
          />
        </div>

        <aside
          style={{
            display: 'flex',
            flexDirection: 'column',
            gap: 16,
            minHeight: 0,
          }}
        >
          <BiomarkerRail
            contributingSignals={liveScenario.contributingSignals}
            latestValues={latestBiomarkerValues}
            signalSeries={signalSeries}
            state={transcriptState}
          />
          <AssessmentCard
            flagFired={flagFired}
            liveScenario={liveScenario}
            onGenerate={() => {
              void openHandoffPreview()
            }}
            onOpenProbes={() => setProbesOpen(true)}
            onWhyFlagged={() => setWhyOpen(true)}
            pdfState={pdfState}
            pdfTimestamp={pdfTimestamp}
            probeAnswers={probeAnswers}
          />
          {errorMessage ? (
            <Card
              style={{ border: '1px solid #e2b0a8', background: '#fff4f2' }}
            >
              <div style={{ fontSize: 13, color: 'var(--red)' }}>
                {errorMessage}
              </div>
            </Card>
          ) : null}
        </aside>
      </main>

      <DevDrawer
        onAttachLive={() => {
          void attachLatestLiveCall()
        }}
        onClose={() => setDrawerOpen(false)}
        onPickScenario={(scenarioId) => {
          void startScenario(scenarioId)
        }}
        open={drawerOpen}
        scenarios={scenarios}
      />
      {!drawerOpen ? (
        <button
          onClick={() => setDrawerOpen(true)}
          style={{
            position: 'fixed',
            bottom: 18,
            left: 18,
            zIndex: 70,
            background: 'rgba(20,22,28,0.88)',
            color: '#f3eedd',
            border: '1px solid rgba(255,255,255,0.16)',
            borderRadius: 10,
            padding: '10px 12px',
            fontFamily: 'var(--font-mono)',
            fontSize: 12,
            boxShadow: '0 6px 24px rgba(0,0,0,0.18)',
          }}
          type="button"
        >
          Open demo drawer
        </button>
      ) : null}

      {whyOpen && callState.rationale ? (
        <WhyFlaggedModal
          liveScenario={liveScenario}
          onClose={() => setWhyOpen(false)}
        />
      ) : null}
      {probesOpen ? (
        <ProbesModal
          initial={probeAnswers}
          onClose={() => setProbesOpen(false)}
          onSave={(answers) => {
            void submitProbeAnswers(answers)
          }}
        />
      ) : null}
      {handoffOpen && handoffUrl ? (
        <HandoffModal
          callEndedAt={callEndedAt}
          callStartedAt={callStartedAt}
          elapsedSeconds={latestEventT}
          generatedAt={handoffGeneratedAt ?? new Date()}
          liveScenario={liveScenario}
          onClose={() => setHandoffOpen(false)}
          onOpenPdf={() => {
            window.open(handoffUrl, '_blank', 'noopener,noreferrer')
          }}
          probeAnswers={probeAnswers}
          triageState={triageState}
        />
      ) : null}
    </div>
  )
}

export default App
