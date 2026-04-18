/** Patient identity injected at runtime for the live screen. */
export type RuntimePatient = {
  name: string
  age: number
  weeks: string
  parity: string
  baby: string
  reason: string
}

/** Runtime context consumed by the Postnatal Pulse UI. */
export type RuntimeContext = {
  PATIENT: RuntimePatient
  CLINICIAN: string
}

const fallbackRuntime: RuntimeContext = {
  PATIENT: {
    name: 'Maya Patel',
    age: 29,
    weeks: '6 weeks postpartum',
    parity: 'First baby',
    baby: 'Leo Patel, 6 weeks',
    reason: 'Routine postnatal follow-up',
  },
  CLINICIAN: 'Sister J. Okafor',
}

declare global {
  interface Window {
    POSTNATAL?: Partial<RuntimeContext>
  }
}

/** Reads runtime-injected patient and clinician data, with safe fixture fallbacks. */
export function getRuntimeContext(): RuntimeContext {
  return {
    PATIENT: {
      ...fallbackRuntime.PATIENT,
      ...window.POSTNATAL?.PATIENT,
    },
    CLINICIAN: window.POSTNATAL?.CLINICIAN ?? fallbackRuntime.CLINICIAN,
  }
}
