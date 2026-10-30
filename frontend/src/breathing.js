export const TOTAL_SECONDS = 60
export const INHALE_SECONDS = 4
export const EXHALE_SECONDS = 6
export const CYCLE_SECONDS = INHALE_SECONDS + EXHALE_SECONDS

export function breathingState(elapsedSeconds) {
  const elapsed = Math.min(TOTAL_SECONDS, Math.max(0, Math.floor(elapsedSeconds)))
  const position = elapsed % CYCLE_SECONDS
  const inhaling = elapsed < TOTAL_SECONDS && position < INHALE_SECONDS
  const phaseEnd = inhaling ? INHALE_SECONDS : CYCLE_SECONDS
  const phaseElapsed = inhaling ? position : position - INHALE_SECONDS

  return {
    elapsed,
    remaining: TOTAL_SECONDS - elapsed,
    phase: inhaling ? 'inhale' : 'exhale',
    label: inhaling ? 'Breathe in' : 'Breathe out',
    cue: inhaling ? 'INHALE' : 'EXHALE',
    phaseRemaining: elapsed === TOTAL_SECONDS ? 0 : phaseEnd - position,
    // Inhale visibly counts up as the circle grows; exhale counts down as it
    // settles, so the number and visual cue progress together.
    displayCount:
      elapsed === TOTAL_SECONDS
        ? 0
        : inhaling
          ? phaseElapsed + 1
          : EXHALE_SECONDS - phaseElapsed,
    cycle: Math.min(6, Math.floor(elapsed / CYCLE_SECONDS) + 1),
  }
}
