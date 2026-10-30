import { describe, expect, it } from 'vitest'
import { breathingState, TOTAL_SECONDS } from './breathing'

describe('breathingState', () => {
  it('starts with a four-second inhale and six cycles', () => {
    expect(breathingState(0)).toMatchObject({
      phase: 'inhale',
      phaseRemaining: 4,
      displayCount: 1,
      cycle: 1,
      remaining: 60,
    })
  })

  it('changes to exhale after four seconds', () => {
    expect(breathingState(4)).toMatchObject({
      phase: 'exhale',
      phaseRemaining: 6,
      displayCount: 6,
      cycle: 1,
    })
  })

  it('never extends the exercise beyond sixty seconds', () => {
    expect(breathingState(120)).toMatchObject({ remaining: 0, phaseRemaining: 0, cycle: 6 })
  })

  it('keeps the planned exercise at or below the ninety-second limit', () => {
    expect(TOTAL_SECONDS).toBeLessThanOrEqual(90)
  })

  it('uses an inhale count-up and an exhale countdown for the continuous circle cue', () => {
    expect(breathingState(3)).toMatchObject({ phase: 'inhale', displayCount: 4 })
    expect(breathingState(9)).toMatchObject({ phase: 'exhale', displayCount: 1 })
  })
})
