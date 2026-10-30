import { describe, expect, it } from 'vitest'
import { STOP_STEPS } from './stop'

describe('STOP flow', () => {
  it('keeps the four user-directed steps in a fixed order', () => {
    expect(STOP_STEPS.map((step) => step.title)).toEqual([
      'Stop',
      'Take a step back',
      'Observe',
      'Proceed mindfully',
    ])
  })

  it('includes the defined content for each STOP step', () => {
    expect(STOP_STEPS.map((step) => [step.prompt, step.detail])).toEqual([
      ['Freeze immediately.', 'Do not act, speak, or react when emotions run high.'],
      ['Remove yourself physically or mentally from the situation.', 'Take a few slow, deep breaths to calm your nervous system.'],
      ['Observe like an objective detective.', 'Notice thoughts, physical sensations, and feelings, plus what others are doing or saying.'],
      ['Ask yourself what your goal is.', 'Choose what will make things better rather than worse, then act with intention.'],
    ])
  })

  it('does not permit runtime changes to the sequence', () => {
    expect(Object.isFrozen(STOP_STEPS)).toBe(true)
    expect(Object.isFrozen(STOP_STEPS[0])).toBe(true)
  })
})
