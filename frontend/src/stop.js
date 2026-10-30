// This sequence is fixed application content. The optional check-in adapter
// can suggest only a skill name; it never receives or changes these steps.
export const STOP_STEPS = Object.freeze([
  Object.freeze({
    title: 'Stop',
    prompt: 'Freeze immediately.',
    note: 'Do not react yet',
    detail: 'Do not act, speak, or react when emotions run high.',
  }),
  Object.freeze({
    title: 'Take a step back',
    prompt: 'Remove yourself physically or mentally from the situation.',
    note: 'Take a breath',
    detail: 'Take a few slow, deep breaths to calm your nervous system.',
  }),
  Object.freeze({
    title: 'Observe',
    prompt: 'Observe like an objective detective.',
    note: 'Notice what is happening',
    detail: 'Notice thoughts, physical sensations, and feelings, plus what others are doing or saying.',
  }),
  Object.freeze({
    title: 'Proceed mindfully',
    prompt: 'Ask yourself what your goal is.',
    note: 'Choose with intention',
    detail: 'Choose what will make things better rather than worse, then act with intention.',
  }),
])
