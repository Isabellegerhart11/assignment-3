<script setup>
import { computed, h, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import { api } from './api'
import { breathingState, TOTAL_SECONDS } from './breathing'
import { STOP_STEPS } from './stop'
import { createVoiceConnection } from './voice'

const skillCopy = {
  paced_breathing: {
    label: 'Paced breathing',
    detail: 'A 60-second 4-in / 6-out practice.',
    chatDetail: 'A 60-second guided practice: follow the circle for four counts in and six counts out, for six cycles. You can pause or leave at any time.',
    researchDetail: 'A 2023 systematic review found that many studied breathing programs used guided, slower breathing. Its reviewed programs were generally at least five minutes long, so this 60-second exercise is a brief practice—not a copy of those research protocols or a treatment.',
    researchCitation: 'Bentley et al. (2023) · systematic review',
    researchUrl: 'https://doi.org/10.3390/brainsci13121612',
  },
  stop: {
    label: 'STOP skill',
    detail: 'Pause, notice, and choose one small next action.',
    chatDetail: 'A four-step, user-paced walkthrough: Stop, Take a step back, Observe, and Proceed mindfully. It shows one step at a time, with Back, Continue, and Leave controls.',
    researchDetail: 'A 2022 study of a 30-lesson school DBT skills program reported good acceptability, while many outcome findings remained preliminary or non-significant. This short STOP walkthrough uses a structured skills format; it is not that curriculum and does not claim the study’s outcomes.',
    researchCitation: 'Gasol et al. (2022) · school DBT skills study',
    researchUrl: 'https://doi.org/10.3390/ijerph19010494',
  },
}

const FALLBACK_ACKNOWLEDGEMENT = 'You can continue without sharing anything.'
const THEME_STORAGE_KEY = 'clearspace-theme'
const DEFAULT_PROFILE = Object.freeze({
  preferred_skill: null,
  motion_preference: 'system',
  chat_personalization_enabled: false,
  updated_at: '',
})
const themes = Object.freeze([
  Object.freeze({ id: 'forest', label: 'Night sky', detail: 'Calming night sky' }),
  Object.freeze({ id: 'snowy-winter', label: 'Snowy Winter', detail: 'Ice and soft blue' }),
  Object.freeze({ id: 'fall', label: 'Fall', detail: 'Warm earth and amber' }),
  Object.freeze({ id: 'spring', label: 'Spring', detail: 'Fresh leaves and bloom' }),
])
const PROFILE_REFLECTIONS = Object.freeze([
  Object.freeze({
    id: 'body_tension',
    prompt: 'At this moment, I notice tension in my body.',
    options: ['Not at all', 'A little', 'Mostly', 'Very much'],
  }),
  Object.freeze({
    id: 'thoughts_calm',
    prompt: 'At this moment, my thoughts feel calm.',
    options: ['Not at all', 'A little', 'Mostly', 'Very much'],
  }),
  Object.freeze({
    id: 'at_ease',
    prompt: 'At this moment, I feel at ease.',
    options: ['Not at all', 'A little', 'Mostly', 'Very much'],
  }),
  Object.freeze({
    id: 'on_edge',
    prompt: 'At this moment, I feel on edge.',
    options: ['Not at all', 'A little', 'Mostly', 'Very much'],
  }),
])
const MOOD_OPTIONS = Object.freeze([
  Object.freeze({ id: 'very_low', label: 'Very low', icon: 'mood-very_low' }),
  Object.freeze({ id: 'low', label: 'Low', icon: 'mood-low' }),
  Object.freeze({ id: 'in_between', label: 'In between', icon: 'mood-in_between' }),
  Object.freeze({ id: 'good', label: 'Good', icon: 'mood-good' }),
  Object.freeze({ id: 'very_good', label: 'Very good', icon: 'mood-very_good' }),
])
const ICON_SHAPES = Object.freeze({
  home: [
    ['path', { d: 'm3 10.5 9-7 9 7.5' }],
    ['path', { d: 'M5.5 9.5V21h13V9.5' }],
    ['path', { d: 'M9.5 21v-6h5v6' }],
  ],
  activities: [
    ['circle', { cx: '12', cy: '12', r: '9' }],
    ['circle', { cx: '12', cy: '12', r: '5' }],
    ['circle', { cx: '12', cy: '12', r: '1' }],
  ],
  chat: [
    ['path', { d: 'M20 15a4 4 0 0 1-4 4H9l-5 3v-7a4 4 0 0 1-2-3.5v-4A4 4 0 0 1 6 4h10a4 4 0 0 1 4 4Z' }],
    ['path', { d: 'M7 11h.01M12 11h.01M17 11h.01' }],
  ],
  calendar: [
    ['rect', { x: '3', y: '4.5', width: '18', height: '16', rx: '2.5' }],
    ['path', { d: 'M7 2.5v4M17 2.5v4M3 9h18M8 13h.01M12 13h.01M16 13h.01M8 17h.01M12 17h.01' }],
  ],
  profile: [
    ['circle', { cx: '12', cy: '8', r: '3.5' }],
    ['path', { d: 'M4.5 21a7.5 7.5 0 0 1 15 0' }],
  ],
  crisis: [
    ['path', { d: 'M12 2.5 20.5 6v5.2c0 5.1-3.4 8.5-8.5 10.3-5.1-1.8-8.5-5.2-8.5-10.3V6Z' }],
    ['path', { d: 'M12 8v6M9 11h6' }],
  ],
  clock: [
    ['circle', { cx: '12', cy: '12', r: '9' }],
    ['path', { d: 'M12 7v5l3.5 2' }],
  ],
  microphone: [
    ['rect', { x: '8.5', y: '3', width: '7', height: '12', rx: '3.5' }],
    ['path', { d: 'M5.5 11.5a6.5 6.5 0 0 0 13 0M12 18v3M8.5 21h7' }],
  ],
  chevron: [['path', { d: 'm9 18 6-6-6-6' }]],
  'chevron-left': [['path', { d: 'm15 18-6-6 6-6' }]],
  'mood-very_low': [
    ['circle', { cx: '12', cy: '12', r: '9' }],
    ['path', { d: 'M8.5 10h.01M15.5 10h.01M8.5 16c1.1-1.4 2.3-2 3.5-2s2.4.6 3.5 2' }],
  ],
  'mood-low': [
    ['circle', { cx: '12', cy: '12', r: '9' }],
    ['path', { d: 'M8.5 10h.01M15.5 10h.01M8.5 15.5c1.1-.8 2.3-1.2 3.5-1.2s2.4.4 3.5 1.2' }],
  ],
  'mood-in_between': [
    ['circle', { cx: '12', cy: '12', r: '9' }],
    ['path', { d: 'M8.5 10h.01M15.5 10h.01M8.5 15h7' }],
  ],
  'mood-good': [
    ['circle', { cx: '12', cy: '12', r: '9' }],
    ['path', { d: 'M8.5 10h.01M15.5 10h.01M8.5 14.5c1.1 1.1 2.3 1.7 3.5 1.7s2.4-.6 3.5-1.7' }],
  ],
  'mood-very_good': [
    ['circle', { cx: '12', cy: '12', r: '9' }],
    ['path', { d: 'M8.5 9.5h.01M15.5 9.5h.01M7.8 13.5c1.2 2 2.6 3 4.2 3s3-1 4.2-3' }],
  ],
})
const AppIcon = {
  props: { name: { type: String, required: true } },
  setup(props) {
    return () =>
      h(
        'svg',
        {
          class: 'app-icon-svg',
          viewBox: '0 0 24 24',
          'aria-hidden': 'true',
          focusable: 'false',
        },
        (ICON_SHAPES[props.name] || []).map(([tag, attributes]) => h(tag, attributes)),
      )
  },
}
const themeIds = new Set(themes.map((theme) => theme.id))

function storedTheme() {
  try {
    const savedTheme = globalThis.localStorage?.getItem(THEME_STORAGE_KEY)
    return themeIds.has(savedTheme) ? savedTheme : 'forest'
  } catch {
    return 'forest'
  }
}

function emptyProfileReflection() {
  return Object.fromEntries(PROFILE_REFLECTIONS.map((question) => [question.id, '']))
}

function defaultProfile() {
  return { ...DEFAULT_PROFILE }
}

function calendarDateKey(value) {
  return `${value.getFullYear()}-${String(value.getMonth() + 1).padStart(2, '0')}-${String(value.getDate()).padStart(2, '0')}`
}

function monthStart(value) {
  return new Date(value.getFullYear(), value.getMonth(), 1, 12)
}

function monthKey(value) {
  return `${value.getFullYear()}-${String(value.getMonth() + 1).padStart(2, '0')}`
}

function dateFromCalendarKey(value) {
  const [year, month, day] = value.split('-').map(Number)
  return new Date(year, month - 1, day, 12)
}

const screen = ref('home')
const previousScreen = ref('home')
const selectedTheme = ref(storedTheme())
const profile = ref(defaultProfile())
const profileBusy = ref(false)
const profileReflectionOpen = ref(false)
const profileReflection = ref(emptyProfileReflection())
const reflectionForNextChat = ref(null)
const selectedSkill = ref('paced_breathing')
const sessionId = ref(null)
const checkinText = ref('')
const checkinReply = ref(null)
const checkinFailure = ref(false)
const appError = ref('')
const history = ref([])
const historyDetail = ref(null)
const chatHistory = ref([])
const activeConversation = ref(null)
const chatText = ref('')
const chatBusy = ref(false)
const chatFailure = ref(false)
const busy = ref(false)
const stopStep = ref(0)
const elapsedBreathing = ref(0)
const isPaused = ref(false)
const calendarCursor = ref(monthStart(new Date()))
const selectedCalendarDay = ref(calendarDateKey(new Date()))
const moodEntries = ref([])
const calendarBusy = ref(false)
const voiceStatus = ref('idle')
const voiceError = ref(null)
const voicePlaybackBlocked = ref(false)

let breathingTimer = null
let breathingStartedAt = 0
let completedPractice = false
let checkinRequestGeneration = 0
let chatRequestGeneration = 0
let moodRequestGeneration = 0
let voiceConnection = null

const selected = computed(() => skillCopy[selectedSkill.value])
const currentStopStep = computed(() => STOP_STEPS[stopStep.value])
const breath = computed(() => breathingState(elapsedBreathing.value))
const historyItem = computed(() => history.value[0] || null)
const lastCompletedSession = computed(() =>
  history.value.find((session) => session.status === 'completed') || null,
)
const recommendedPractice = computed(() => {
  if (profile.value.preferred_skill) {
    return {
      skill: profile.value.preferred_skill,
      label: 'Your selected practice',
      detail: 'A familiar starting point you chose. You can always choose another activity.',
    }
  }
  if (lastCompletedSession.value) {
    return {
      skill: lastCompletedSession.value.skill,
      label: 'Continue a familiar practice',
      detail: 'Based on your most recent completed practice. You can always choose another activity.',
    }
  }
  return {
    skill: 'paced_breathing',
    label: 'Guided practice',
    detail: 'Four seconds in. Six seconds out.',
  }
})
const allowedResponses = computed(() =>
  historyDetail.value?.conversation.filter((event) => event.role === 'assistant') || [],
)
const isCheckinFallback = computed(
  () => checkinFailure.value || checkinReply.value?.acknowledgement === FALLBACK_ACKNOWLEDGEMENT,
)
const durationLabel = computed(() => `${breath.value.remaining} seconds left`)
const calendarMonth = computed(() =>
  new Intl.DateTimeFormat(undefined, { month: 'long', year: 'numeric' }).format(calendarCursor.value),
)
const selectedCalendarDayLabel = computed(() =>
  new Intl.DateTimeFormat(undefined, { month: 'long', day: 'numeric', year: 'numeric' }).format(
    dateFromCalendarKey(selectedCalendarDay.value),
  ),
)
const moodsByDay = computed(() => new Map(moodEntries.value.map((entry) => [entry.day, entry])))
const selectedMood = computed(() => moodsByDay.value.get(selectedCalendarDay.value) || null)
const voiceCanStart = computed(() => ['idle', 'closed', 'error'].includes(voiceStatus.value))
const voiceCanMute = computed(() => voiceStatus.value === 'active')
const voiceCanUnmute = computed(() => voiceStatus.value === 'muted')
const voiceStartLabel = computed(() => {
  if (voiceStatus.value === 'permission' || voiceStatus.value === 'connecting') return 'Connecting…'
  if (voiceStatus.value === 'active') return 'Voice active'
  if (voiceStatus.value === 'muted') return 'Microphone muted'
  if (voiceStatus.value === 'closing') return 'Closing…'
  return 'Start voice'
})
const voiceStatusText = computed(() => {
  if (voiceStatus.value === 'permission') return 'Requesting microphone permission…'
  if (voiceStatus.value === 'connecting') return 'Connecting voice…'
  if (voiceStatus.value === 'muting') return 'Muting your microphone…'
  if (voiceStatus.value === 'unmuting') return 'Unmuting your microphone…'
  if (voiceStatus.value === 'active') {
    if (voiceError.value === 'input-control') return 'Microphone setting could not update. You can try again or keep using text chat.'
    return 'Voice is active. Text chat is still available.'
  }
  if (voiceStatus.value === 'muted') return 'Your microphone is muted. Text chat is still available.'
  if (voiceStatus.value === 'closing') return 'Closing voice…'
  if (voiceStatus.value === 'closed') return 'Voice is closed. Text chat is still available.'
  if (voiceStatus.value === 'error') {
    if (voiceError.value === 'permission') return 'Microphone permission was not granted. You can keep using text chat.'
    if (voiceError.value === 'unsupported') return 'Voice is unavailable in this browser. You can keep using text chat.'
    if (voiceError.value === 'unavailable') return 'Voice is not configured. You can keep using text chat.'
    return 'Voice could not connect. You can keep using text chat.'
  }
  return 'Voice is optional. Text chat is always available.'
})
const hasProfileReflection = computed(() =>
  Object.values(profileReflection.value).some((answer) => Boolean(answer)),
)
const tabNavigationVisible = computed(() =>
  ['home', 'skills', 'calendar', 'profile', 'history', 'chat', 'finish'].includes(screen.value),
)
const themeSceneryVisible = computed(() =>
  ['home', 'skills', 'calendar', 'profile', 'history', 'chat', 'finish'].includes(screen.value),
)
const activeNavigationTab = computed(() => {
  if (screen.value === 'skills') return 'activities'
  return ['home', 'calendar', 'profile', 'chat'].includes(screen.value) ? screen.value : null
})
const calendarDays = computed(() => {
  const today = new Date()
  const year = calendarCursor.value.getFullYear()
  const month = calendarCursor.value.getMonth()
  const firstWeekday = new Date(year, month, 1).getDay()
  const daysInMonth = new Date(year, month + 1, 0).getDate()
  const practicedDays = new Set(
    history.value.map((session) => {
      const completed = new Date(session.updated_at)
      return calendarDateKey(completed)
    }),
  )
  const days = Array.from({ length: firstWeekday }, () => null)
  for (let day = 1; day <= daysInMonth; day += 1) {
    const dateKey = calendarDateKey(new Date(year, month, day, 12))
    days.push({
      day,
      dateKey,
      mood: moodsByDay.value.get(dateKey)?.mood || null,
      practiced: practicedDays.has(dateKey),
      today: dateKey === calendarDateKey(today),
      selected: dateKey === selectedCalendarDay.value,
    })
  }
  while (days.length % 7) days.push(null)
  return days
})

function clearError() {
  appError.value = ''
}

function reportError(_error, fallback) {
  // Surface only app-owned wording. Transport and provider errors can contain
  // unexpected data, so they should never be shown back to the person.
  appError.value = fallback
}

function updateVoiceStatus(next) {
  voiceStatus.value = next.status
  voiceError.value = next.error
}

function getVoiceConnection() {
  if (voiceConnection) return voiceConnection
  voiceConnection = createVoiceConnection({
    getConfiguration: api.getVoiceConfiguration,
    createSession: api.createVoiceSession,
    onStatus: updateVoiceStatus,
    onPlaybackBlocked: (blocked) => {
      voicePlaybackBlocked.value = blocked
    },
  })
  return voiceConnection
}

async function startVoiceConversation() {
  if (!voiceCanStart.value) return
  clearError()
  voiceError.value = null
  voicePlaybackBlocked.value = false
  await getVoiceConnection().start()
}

async function enableAssistantAudio() {
  await getVoiceConnection().enableAssistantAudio()
}

function muteVoiceConversation() {
  if (voiceCanMute.value) getVoiceConnection().mute()
}

function unmuteVoiceConversation() {
  if (voiceCanUnmute.value) getVoiceConnection().unmute()
}

function releaseVoiceConnection() {
  voiceConnection?.dispose()
  voiceConnection = null
  if (!['idle', 'closed', 'error'].includes(voiceStatus.value)) {
    voiceStatus.value = 'closed'
    voiceError.value = null
  }
  voicePlaybackBlocked.value = false
}

function chooseSkill(skill) {
  clearError()
  selectedSkill.value = skill
}

function chooseTheme(theme) {
  if (!themeIds.has(theme)) return
  selectedTheme.value = theme
  try {
    globalThis.localStorage?.setItem(THEME_STORAGE_KEY, theme)
  } catch {
    // Appearance remains usable when browser storage is unavailable.
  }
}

function clearProfileReflection() {
  profileReflection.value = emptyProfileReflection()
}

function selectedProfileReflection() {
  return Object.fromEntries(
    Object.entries(profileReflection.value).filter(([, answer]) => Boolean(answer)),
  )
}

function discardReflectionForChat() {
  reflectionForNextChat.value = null
}

function useReflectionInNextChat() {
  const answers = selectedProfileReflection()
  if (!Object.keys(answers).length) {
    appError.value = 'Choose at least one optional reflection response first, or continue without it.'
    return
  }
  clearError()
  reflectionForNextChat.value = answers
  resetProfileReflection()
  void openChat()
}

function resetProfileReflection() {
  profileReflectionOpen.value = false
  clearProfileReflection()
}

async function loadProfile() {
  try {
    profile.value = await api.getProfile()
  } catch (error) {
    // A missing preference record never blocks exercises or manual choices.
    profile.value = defaultProfile()
    reportError(error, 'Profile preferences are unavailable. You can still choose any activity.')
  }
}

async function saveProfile() {
  if (profileBusy.value) return
  clearError()
  profileBusy.value = true
  try {
    profile.value = await api.updateProfile({
      preferred_skill: profile.value.preferred_skill,
      motion_preference: profile.value.motion_preference,
      chat_personalization_enabled: profile.value.chat_personalization_enabled,
    })
  } catch (error) {
    reportError(error, 'Profile preferences could not be saved. You can still choose any activity.')
    await loadProfile()
  } finally {
    profileBusy.value = false
  }
}

async function clearProfilePreferences() {
  if (profileBusy.value) return
  clearError()
  profileBusy.value = true
  try {
    profile.value = await api.clearProfile()
  } catch (error) {
    reportError(error, 'Profile preferences could not be cleared. You can still choose any activity.')
  } finally {
    profileBusy.value = false
  }
}

function openActivities() {
  clearError()
  screen.value = 'skills'
}

function openDailyCheckin() {
  chooseSkill('paced_breathing')
  void beginCheckin()
}

function openFeaturedPractice() {
  chooseSkill(recommendedPractice.value.skill)
  void beginSelectedSkill()
}

function openCalendar() {
  clearError()
  screen.value = 'calendar'
  void loadMoods()
}

function updateMoodEntry(entry) {
  const withoutCurrentDay = moodEntries.value.filter((item) => item.day !== entry.day)
  moodEntries.value = [...withoutCurrentDay, entry].sort((left, right) => left.day.localeCompare(right.day))
}

async function loadMoods() {
  const requestGeneration = ++moodRequestGeneration
  calendarBusy.value = true
  try {
    const entries = await api.listMoods(monthKey(calendarCursor.value))
    if (requestGeneration === moodRequestGeneration) moodEntries.value = entries
  } catch (error) {
    if (requestGeneration === moodRequestGeneration) {
      reportError(error, 'Daily mood entries are unavailable. You can still use any activity.')
    }
  } finally {
    if (requestGeneration === moodRequestGeneration) calendarBusy.value = false
  }
}

function selectCalendarDay(day) {
  selectedCalendarDay.value = day.dateKey
}

function moveCalendarMonth(offset) {
  const current = calendarCursor.value
  const next = new Date(current.getFullYear(), current.getMonth() + offset, 1, 12)
  const selected = dateFromCalendarKey(selectedCalendarDay.value)
  const nextDay = Math.min(selected.getDate(), new Date(next.getFullYear(), next.getMonth() + 1, 0).getDate())
  calendarCursor.value = next
  selectedCalendarDay.value = calendarDateKey(new Date(next.getFullYear(), next.getMonth(), nextDay, 12))
  void loadMoods()
}

async function saveMood(mood) {
  if (calendarBusy.value) return
  clearError()
  calendarBusy.value = true
  try {
    updateMoodEntry(await api.saveMood(selectedCalendarDay.value, mood))
  } catch (error) {
    reportError(error, 'That daily mood entry could not be saved. You can try again or choose an activity.')
  } finally {
    calendarBusy.value = false
  }
}

async function removeMood() {
  if (!selectedMood.value || calendarBusy.value) return
  clearError()
  calendarBusy.value = true
  try {
    await api.removeMood(selectedCalendarDay.value)
    moodEntries.value = moodEntries.value.filter((entry) => entry.day !== selectedCalendarDay.value)
  } catch (error) {
    reportError(error, 'That daily mood entry could not be removed. You can still use any activity.')
  } finally {
    calendarBusy.value = false
  }
}

async function clearMoodHistory() {
  if (!moodEntries.value.length || calendarBusy.value) return
  clearError()
  calendarBusy.value = true
  try {
    await api.clearMoods()
    moodEntries.value = []
  } catch (error) {
    reportError(error, 'Daily mood entries could not be cleared. You can still use any activity.')
  } finally {
    calendarBusy.value = false
  }
}

function openProfile() {
  clearError()
  discardReflectionForChat()
  resetProfileReflection()
  screen.value = 'profile'
  void loadProfile()
}

function openNavigationTab(tab) {
  if (tab === 'home') {
    returnToDashboard()
    return
  }
  if (tab === 'activities') {
    openActivities()
    return
  }
  if (tab === 'calendar') {
    openCalendar()
    return
  }
  if (tab === 'profile') {
    openProfile()
    return
  }
  if (tab === 'chat') {
    if (screen.value !== 'chat') void openChat()
    return
  }
  if (tab === 'crisis') openCrisis()
}

async function startNewSession(nextScreen) {
  releaseVoiceConnection()
  checkinRequestGeneration += 1
  clearError()
  busy.value = true
  try {
    const session = await api.createSession(selectedSkill.value)
    sessionId.value = session.id
    checkinReply.value = null
    checkinFailure.value = false
    checkinText.value = ''
    completedPractice = false
    if (nextScreen === 'stop') {
      stopStep.value = 0
    }
    screen.value = nextScreen
    if (nextScreen === 'breathing') await startBreathingAfterInstruction()
  } catch (error) {
    reportError(error, 'A new practice could not be saved. You can still use the exercise.')
    sessionId.value = null
    completedPractice = false
    if (nextScreen === 'stop') stopStep.value = 0
    screen.value = nextScreen
    if (nextScreen === 'breathing') await startBreathingAfterInstruction()
  } finally {
    busy.value = false
  }
}

function beginSelectedSkill() {
  return startNewSession(selectedSkill.value === 'paced_breathing' ? 'breathing' : 'stop')
}

function beginSuggestedSkill(skill) {
  chooseSkill(skill)
  return beginSelectedSkill()
}

function beginCheckin() {
  return startNewSession('checkin')
}

async function enterSelectedSkill() {
  if (selectedSkill.value === 'paced_breathing') {
    screen.value = 'breathing'
    await startBreathingAfterInstruction()
  } else {
    stopStep.value = 0
    screen.value = 'stop'
  }
}

async function submitCheckin() {
  const text = checkinText.value.trim()
  if (!text) {
    enterSelectedSkill()
    return
  }
  if (!sessionId.value) {
    appError.value = 'The optional check-in is unavailable. You can continue without sharing.'
    return
  }
  clearError()
  checkinFailure.value = false
  busy.value = true
  const requestGeneration = ++checkinRequestGeneration
  try {
    // The input is sent once and cleared immediately; it is not kept in UI history.
    checkinText.value = ''
    const reply = await api.submitCheckin(sessionId.value, text)
    if (requestGeneration !== checkinRequestGeneration) return
    checkinReply.value = reply
  } catch (error) {
    if (requestGeneration !== checkinRequestGeneration) return
    // A transport/API failure receives the same non-clinical fallback as an
    // unavailable model. Crisis Support and leaving stay independently usable.
    checkinFailure.value = true
    checkinReply.value = {
      acknowledgement: FALLBACK_ACKNOWLEDGEMENT,
      suggested_skill: selectedSkill.value,
    }
  } finally {
    if (requestGeneration === checkinRequestGeneration) busy.value = false
  }
}

function trySuggestedSkill() {
  if (!checkinReply.value) return
  selectedSkill.value = checkinReply.value.suggested_skill
  void enterSelectedSkill()
}

async function startBreathingAfterInstruction() {
  // Begin only once the first instruction is visible, so the stated minute
  // measures the complete planned exercise rather than a pre-render delay.
  await nextTick()
  startBreathing()
}

function startBreathing() {
  clearBreathingTimer()
  elapsedBreathing.value = 0
  isPaused.value = false
  completedPractice = false
  breathingStartedAt = Date.now()
  breathingTimer = window.setInterval(tickBreathing, 250)
}

function tickBreathing() {
  elapsedBreathing.value = Math.min(
    TOTAL_SECONDS,
    Math.floor((Date.now() - breathingStartedAt) / 1000),
  )
  if (elapsedBreathing.value >= TOTAL_SECONDS) {
    clearBreathingTimer()
    completePractice('completed', TOTAL_SECONDS)
  }
}

function clearBreathingTimer() {
  if (breathingTimer) {
    window.clearInterval(breathingTimer)
    breathingTimer = null
  }
}

function togglePause() {
  if (isPaused.value) {
    breathingStartedAt = Date.now() - elapsedBreathing.value * 1000
    isPaused.value = false
    breathingTimer = window.setInterval(tickBreathing, 250)
  } else {
    tickBreathing()
    clearBreathingTimer()
    isPaused.value = true
  }
}

async function completePractice(status, secondsCompleted) {
  if (completedPractice) return
  completedPractice = true
  clearBreathingTimer()
  const completedSessionId = sessionId.value
  // A completed practice is shown immediately; history persistence never
  // keeps the person on a timed exercise or away from Crisis Support.
  screen.value = 'finish'
  if (completedSessionId) {
    try {
      await api.finishSession(
        completedSessionId,
        status,
        Math.min(90, Math.max(0, secondsCompleted)),
      )
    } catch (error) {
      reportError(error, 'The practice was not added to history. You can still continue.')
    }
  }
  await loadHistory()
}

function leaveExercise() {
  clearBreathingTimer()
  checkinRequestGeneration += 1
  const leavingSessionId = sessionId.value
  const seconds = screen.value === 'breathing' ? elapsedBreathing.value : 0
  // Leaving is immediate and non-blocking. The small local record is saved in
  // the background, so a slow or unavailable database never holds someone in
  // a practice or check-in screen.
  returnToActivitySelection()
  if (leavingSessionId) void recordVoluntaryExit(leavingSessionId, seconds)
}

async function recordVoluntaryExit(leavingSessionId, seconds) {
  try {
    await api.finishSession(leavingSessionId, 'left', Math.min(90, seconds))
  } catch (error) {
    reportError(error, 'The practice was not added to history. Leaving is always okay.')
  } finally {
    await loadHistory()
  }
}

function nextStopStep() {
  if (stopStep.value === STOP_STEPS.length - 1) {
    void completePractice('completed', 0)
    return
  }
  stopStep.value += 1
}

function previousStopStep() {
  if (stopStep.value > 0) stopStep.value -= 1
}

function openCrisis() {
  releaseVoiceConnection()
  clearError()
  previousScreen.value = screen.value
  if (screen.value === 'breathing' && !isPaused.value) togglePause()
  screen.value = 'crisis'
}

function closeCrisis() {
  screen.value = previousScreen.value
}

async function loadHistory() {
  try {
    history.value = await api.listSessions()
  } catch (error) {
    // History is optional; an unavailable database must not block practice.
    reportError(error, 'History is unavailable. You can still use a skill.')
  }
}

async function clearHistory() {
  clearError()
  try {
    await api.clearSessions()
    history.value = []
    historyDetail.value = null
  } catch (error) {
    reportError(error, 'History could not be cleared right now.')
  }
}

async function openHistory() {
  clearError()
  historyDetail.value = null
  screen.value = 'history'
  await loadHistory()
}

async function reviewSession(sessionId) {
  clearError()
  try {
    historyDetail.value = await api.getSession(sessionId)
  } catch (error) {
    reportError(error, 'That session could not be opened.')
  }
}

function useHistorySkill() {
  if (historyDetail.value) selectedSkill.value = historyDetail.value.skill
  beginSelectedSkill()
}

function formatSessionTime(timestamp) {
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(timestamp))
}

function useLastSkill() {
  if (historyItem.value) selectedSkill.value = historyItem.value.skill
  beginSelectedSkill()
}

function createClientMessageId() {
  if (globalThis.crypto?.randomUUID) return globalThis.crypto.randomUUID()
  return `fictional-chat-${Date.now()}-${Math.random().toString(16).slice(2)}`
}

async function loadChatHistory() {
  try {
    chatHistory.value = await api.listConversations()
  } catch (error) {
    reportError(error, 'Chat history is unavailable. You can still use a skill.')
  }
}

async function openChat() {
  releaseVoiceConnection()
  voiceStatus.value = 'idle'
  voiceError.value = null
  clearError()
  resetProfileReflection()
  chatFailure.value = false
  chatBusy.value = true
  screen.value = 'chat'
  try {
    activeConversation.value = await api.createConversation()
    await loadChatHistory()
  } catch (error) {
    reportError(error, 'A saved chat could not be started. You can still use a skill.')
    activeConversation.value = null
  } finally {
    chatBusy.value = false
  }
}

async function openSavedChat(conversationId) {
  clearError()
  chatFailure.value = false
  chatBusy.value = true
  try {
    activeConversation.value = await api.getConversation(conversationId)
  } catch (error) {
    reportError(error, 'That saved chat could not be opened.')
  } finally {
    chatBusy.value = false
  }
}

async function startNewChat() {
  await openChat()
}

async function sendChatMessage() {
  const text = chatText.value.trim()
  if (!text || !activeConversation.value || chatBusy.value) return
  clearError()
  chatFailure.value = false
  chatBusy.value = true
  const requestGeneration = ++chatRequestGeneration
  const conversationId = activeConversation.value.id
  const transientReflection = reflectionForNextChat.value
  chatText.value = ''
  // Deliberately one request only: discard before transport or history work.
  reflectionForNextChat.value = null
  try {
    const updatedConversation = transientReflection
      ? await api.sendConversationMessage(
        conversationId,
        text,
        createClientMessageId(),
        transientReflection,
      )
      : await api.sendConversationMessage(
        conversationId,
        text,
        createClientMessageId(),
      )
    if (requestGeneration !== chatRequestGeneration) return
    activeConversation.value = updatedConversation
    await loadChatHistory()
  } catch (error) {
    if (requestGeneration !== chatRequestGeneration) return
    chatFailure.value = true
    // The backend may have saved a failed user message. Refresh it without
    // echoing transport/provider details into the UI.
    try {
      activeConversation.value = await api.getConversation(conversationId)
      await loadChatHistory()
    } catch (_refreshError) {
      // The app-owned fallback below is sufficient if local history is also down.
    }
  } finally {
    if (requestGeneration === chatRequestGeneration) chatBusy.value = false
  }
}

async function clearChatHistory() {
  clearError()
  try {
    await api.clearConversations()
    chatHistory.value = []
    activeConversation.value = null
    discardReflectionForChat()
  } catch (error) {
    reportError(error, 'Chat history could not be cleared right now.')
  }
}

function resetExperience(nextScreen) {
  releaseVoiceConnection()
  clearBreathingTimer()
  checkinRequestGeneration += 1
  chatRequestGeneration += 1
  sessionId.value = null
  checkinText.value = ''
  checkinReply.value = null
  checkinFailure.value = false
  busy.value = false
  chatBusy.value = false
  discardReflectionForChat()
  resetProfileReflection()
  screen.value = nextScreen
}

function returnToActivitySelection() {
  resetExperience('skills')
}

function returnToDashboard() {
  resetExperience('home')
}

onMounted(() => {
  void loadHistory()
  void loadProfile()
  void loadMoods()
})
onBeforeUnmount(() => {
  clearBreathingTimer()
  releaseVoiceConnection()
})
</script>

<template>
  <main class="page-shell" :data-theme="selectedTheme" :data-motion="profile.motion_preference">
    <section class="phone" :aria-label="`ClearSpace: ${screen === 'checkin' ? 'journal check-in' : screen}`">
      <div
        v-if="themeSceneryVisible"
        class="theme-scenery"
        :class="`theme-scenery-${selectedTheme}`"
        aria-hidden="true"
      >
        <template v-if="selectedTheme === 'snowy-winter'">
          <i v-for="flake in 30" :key="`snow-${flake}`" class="snowflake"></i>
        </template>
        <template v-else-if="selectedTheme === 'fall'">
          <i v-for="leaf in 12" :key="`leaf-${leaf}`" class="falling-leaf"></i>
        </template>
        <template v-else-if="selectedTheme === 'spring'">
          <i v-for="flower in 48" :key="`flower-${flower}`" class="wildflower"></i>
        </template>
        <template v-else>
          <i v-for="star in 24" :key="`star-${star}`" class="forest-star"></i>
        </template>
      </div>

      <div v-if="appError" class="error-banner" role="status">
        <span>{{ appError }}</span>
        <button class="text-button" type="button" @click="clearError">Dismiss</button>
      </div>

      <template v-if="screen === 'home'">
        <header class="app-header">
          <span>ClearSpace</span>
          <button class="crisis-button" type="button" @click="openCrisis">Crisis support</button>
        </header>

        <div class="hero-space dashboard-hero">
          <h1>Clear some space for yourself</h1>
          <p>A small place to pause and choose what comes next.</p>
        </div>

        <button class="daily-card" type="button" :disabled="busy" @click="openDailyCheckin">
          <span class="dashboard-icon" aria-hidden="true"><AppIcon name="calendar" /></span>
          <span>
            <small>Your day</small>
            <strong>How are you feeling?</strong>
            <em>Optional daily check-in</em>
          </span>
          <span class="dashboard-arrow" aria-hidden="true"><AppIcon name="chevron" /></span>
        </button>

        <section class="featured-practice" :aria-label="`${skillCopy[recommendedPractice.skill].label} practice`">
          <div class="featured-topline">
            <small>{{ recommendedPractice.label }}</small>
            <span class="featured-duration"><AppIcon name="clock" /> {{ recommendedPractice.skill === 'paced_breathing' ? '60 seconds' : 'Four steps' }}</span>
          </div>
          <div class="featured-copy">
            <h2>{{ skillCopy[recommendedPractice.skill].label }}</h2>
            <p>{{ recommendedPractice.detail }}</p>
            <small v-if="recommendedPractice.skill === 'paced_breathing'">6 cycles · No hold</small>
            <small v-else>Stop · step back · observe · proceed</small>
          </div>
          <div v-if="recommendedPractice.skill === 'paced_breathing'" class="featured-orbit" aria-hidden="true">
            <i v-for="ring in 9" :key="`featured-ring-${ring}`" class="featured-ring"></i>
          </div>
          <button class="primary-button" type="button" :disabled="busy" @click="openFeaturedPractice">
            {{ busy ? 'Opening…' : `Open ${skillCopy[recommendedPractice.skill].label}  →` }}
          </button>
          <div class="featured-options">
            <button class="quiet-link" type="button" @click="openActivities">Choose another activity</button>
            <button class="quiet-link" type="button" @click="openProfile">Change preference</button>
          </div>
        </section>

        <p class="explore-label">More to explore</p>
        <section class="dashboard-links" aria-label="Explore ClearSpace">
          <button type="button" @click="openChat">
            <span class="dashboard-icon chat" aria-hidden="true"><AppIcon name="chat" /></span>
            <span><strong>Talk it through</strong><small>Ask about a skill</small></span>
            <span class="dashboard-arrow" aria-hidden="true"><AppIcon name="chevron" /></span>
          </button>
          <button type="button" @click="openCalendar">
            <span class="dashboard-icon calendar" aria-hidden="true"><AppIcon name="calendar" /></span>
            <span><strong>Your days</strong><small>Practice calendar</small></span>
            <span class="dashboard-arrow" aria-hidden="true"><AppIcon name="chevron" /></span>
          </button>
          <button type="button" @click="openActivities">
            <span class="dashboard-icon activities" aria-hidden="true"><AppIcon name="activities" /></span>
            <span><strong>All activities</strong><small>Find your starting point</small></span>
            <span class="dashboard-arrow" aria-hidden="true"><AppIcon name="chevron" /></span>
          </button>
          <button type="button" @click="openProfile">
            <span class="dashboard-icon profile" aria-hidden="true"><AppIcon name="profile" /></span>
            <span><strong>Profile setup</strong><small>Choose your appearance</small></span>
            <span class="dashboard-arrow" aria-hidden="true"><AppIcon name="chevron" /></span>
          </button>
        </section>
        <p class="prototype-note home-disclosure">Coursework skills-practice prototype — not therapy, diagnosis, monitoring, or emergency care.</p>
      </template>

      <template v-else-if="screen === 'skills'">
        <header class="app-header">
          <button class="leave-button" type="button" @click="returnToDashboard">Home</button>
          <button class="crisis-button" type="button" @click="openCrisis">Crisis support</button>
        </header>

        <div class="hero-space">
          <h1>What would you like to practice?</h1>
          <p>Choose a short skills practice. You can leave at any time.</p>
        </div>

        <div class="skill-list" aria-label="Choose an activity">
          <button
            v-for="(copy, skill) in skillCopy"
            :key="skill"
            class="skill-card"
            :class="{ selected: selectedSkill === skill }"
            type="button"
            :aria-pressed="selectedSkill === skill"
            @click="chooseSkill(skill)"
          >
            <strong>{{ copy.label }}</strong>
            <span>{{ copy.detail }}</span>
          </button>
          <button class="skill-card" type="button" @click="openChat">
            <strong>Check-in Chat</strong>
            <span>A brief, self-directed chat to help choose a practice.</span>
          </button>
        </div>

        <div class="bottom-actions">
          <button class="primary-button" type="button" :disabled="busy" @click="beginSelectedSkill">
            {{ busy ? 'Starting…' : `Start ${selectedSkill === 'paced_breathing' ? 'a 60-second reset' : 'the STOP skill'}` }}
          </button>
          <button class="quiet-link" type="button" @click="openHistory">View history</button>
        </div>
      </template>

      <template v-else-if="screen === 'calendar'">
        <header class="app-header">
          <button class="leave-button" type="button" @click="returnToDashboard">Close</button>
          <button class="crisis-button" type="button" @click="openCrisis">Crisis support</button>
        </header>

        <div class="hero-space compact calendar-heading">
          <h1>Your days</h1>
          <p>A simple calendar for your practices and optional daily mood choices.</p>
        </div>

        <section class="calendar-card" aria-label="Daily mood and practice calendar" :aria-busy="calendarBusy">
          <div class="calendar-title">
            <strong>{{ calendarMonth }}</strong>
            <span class="calendar-nav">
              <button type="button" aria-label="Previous month" :disabled="calendarBusy" @click="moveCalendarMonth(-1)"><AppIcon name="chevron-left" /></button>
              <button type="button" aria-label="Next month" :disabled="calendarBusy" @click="moveCalendarMonth(1)"><AppIcon name="chevron" /></button>
            </span>
          </div>
          <div class="calendar-weekdays" aria-hidden="true">
            <span v-for="(weekday, index) in ['S', 'M', 'T', 'W', 'T', 'F', 'S']" :key="index">{{ weekday }}</span>
          </div>
          <div class="calendar-grid">
            <template
              v-for="(day, index) in calendarDays"
              :key="`${day?.day || 'blank'}-${index}`"
            >
              <span v-if="!day" class="calendar-day blank" aria-hidden="true"></span>
              <button
                v-else
                class="calendar-day"
                :class="{ today: day.today, selected: day.selected }"
                type="button"
                :aria-pressed="day.selected"
                :aria-label="`${day.dateKey}${day.mood ? `, mood: ${MOOD_OPTIONS.find((option) => option.id === day.mood)?.label}` : ''}${day.practiced ? ', activity recorded' : ''}`"
                @click="selectCalendarDay(day)"
              >
                <span>{{ day.day }}</span>
                <span class="calendar-markers" aria-hidden="true">
                  <i v-if="day.mood" class="calendar-marker mood-marker" :class="`mood-${day.mood}`"></i>
                  <i v-if="day.practiced" class="calendar-marker practice-marker"></i>
                </span>
              </button>
            </template>
          </div>
          <p class="calendar-key"><span><i class="calendar-marker mood-marker" aria-hidden="true"></i> Self-reported mood</span><span><i class="calendar-marker practice-marker" aria-hidden="true"></i> Saved activity</span></p>
        </section>

        <section class="daily-mood-card" aria-labelledby="daily-mood-title" :aria-busy="calendarBusy">
          <div class="daily-mood-heading">
            <span>Selected day</span>
            <button
              v-if="moodEntries.length"
              class="text-button"
              type="button"
              :disabled="calendarBusy"
              @click="clearMoodHistory"
            >Clear all moods</button>
          </div>
          <strong>{{ selectedCalendarDayLabel }}</strong>
          <h2 id="daily-mood-title">How did this day feel?</h2>
          <p>Choose the word that fits the day. Every choice is okay.</p>
          <div class="mood-options" aria-label="Choose a mood for the selected day">
            <button
              v-for="option in MOOD_OPTIONS"
              :key="option.id"
              class="mood-option"
              :class="[`mood-${option.id}`, { selected: selectedMood?.mood === option.id }]"
              type="button"
              :aria-pressed="selectedMood?.mood === option.id"
              :disabled="calendarBusy"
              @click="saveMood(option.id)"
            >
              <span class="mood-face" aria-hidden="true"><AppIcon :name="option.icon" /></span>
              <span>{{ option.label }}</span>
            </button>
          </div>
          <div class="daily-mood-footer">
            <span>{{ selectedMood ? `Selected: ${MOOD_OPTIONS.find((option) => option.id === selectedMood.mood)?.label}. You can change it any time.` : 'No mood selected for this day.' }}</span>
            <button v-if="selectedMood" class="quiet-link" type="button" :disabled="calendarBusy" @click="removeMood">Remove mood</button>
          </div>
        </section>

        <div class="bottom-actions">
          <button class="primary-button" type="button" @click="openActivities">Explore activities</button>
          <button class="quiet-link" type="button" @click="openHistory">View history</button>
        </div>
      </template>

      <template v-else-if="screen === 'profile'">
        <header class="app-header">
          <button class="leave-button" type="button" @click="returnToDashboard">Close</button>
          <button class="crisis-button" type="button" @click="openCrisis">Crisis support</button>
        </header>

        <div class="hero-space compact profile-heading">
          <h1>Profile setup</h1>
          <p>Choose the appearance of your ClearSpace.</p>
        </div>

        <section class="theme-picker" aria-label="Choose a theme">
          <button
            v-for="theme in themes"
            :key="theme.id"
            class="theme-option"
            :class="[`theme-${theme.id}`, { selected: selectedTheme === theme.id }]"
            type="button"
            :aria-pressed="selectedTheme === theme.id"
            @click="chooseTheme(theme.id)"
          >
            <span class="theme-swatch" aria-hidden="true"></span>
            <span>
              <strong>{{ theme.label }}</strong>
              <small>{{ theme.detail }}</small>
            </span>
          </button>
        </section>

        <section class="profile-settings" aria-label="Practice preferences" :aria-busy="profileBusy">
          <div class="profile-settings-heading">
            <strong>Practice preferences</strong>
            <span>These choices shape the starting point; they never limit the activities you can choose.</span>
          </div>
          <fieldset class="profile-choice-group">
            <legend>Preferred practice</legend>
            <label class="profile-choice">
              <input v-model="profile.preferred_skill" type="radio" name="preferred-skill" :value="null" :disabled="profileBusy" @change="saveProfile">
              <span>No preference</span>
            </label>
            <label v-for="(copy, skill) in skillCopy" :key="skill" class="profile-choice">
              <input v-model="profile.preferred_skill" type="radio" name="preferred-skill" :value="skill" :disabled="profileBusy" @change="saveProfile">
              <span>{{ copy.label }}</span>
            </label>
          </fieldset>
          <fieldset class="profile-choice-group">
            <legend>Motion preference</legend>
            <label class="profile-choice">
              <input v-model="profile.motion_preference" type="radio" name="motion-preference" value="system" :disabled="profileBusy" @change="saveProfile">
              <span>Follow device setting</span>
            </label>
            <label class="profile-choice">
              <input v-model="profile.motion_preference" type="radio" name="motion-preference" value="reduce" :disabled="profileBusy" @change="saveProfile">
              <span>Less motion</span>
            </label>
            <label class="profile-choice">
              <input v-model="profile.motion_preference" type="radio" name="motion-preference" value="standard" :disabled="profileBusy" @change="saveProfile">
              <span>Standard motion</span>
            </label>
          </fieldset>
          <label class="profile-choice chat-personalization-choice">
            <input v-model="profile.chat_personalization_enabled" type="checkbox" :disabled="profileBusy" @change="saveProfile">
            <span>Let Check-in Chat use my selected practice and a short completed-practice summary. This saved practice context never uses reflection answers or check-in text.</span>
          </label>
          <button class="quiet-link clear-profile-button" type="button" :disabled="profileBusy" @click="clearProfilePreferences">Clear practice preferences</button>
        </section>

        <section class="profile-reflection" aria-label="Optional right-now reflection">
          <button
            class="reflection-toggle"
            type="button"
            :aria-expanded="profileReflectionOpen"
            @click="profileReflectionOpen = !profileReflectionOpen"
          >
            <span>
              <strong>Optional right-now reflection</strong>
              <small>Four brief statements, if you want to pause and notice.</small>
            </span>
            <span aria-hidden="true">{{ profileReflectionOpen ? '−' : '+' }}</span>
          </button>

          <div v-if="profileReflectionOpen" class="reflection-questions">
            <p class="reflection-intro">These are original present-moment prototype statements with a four-choice response format. They are not the STAI or a standardized assessment. You can skip any question.</p>
            <fieldset v-for="question in PROFILE_REFLECTIONS" :key="question.id" class="reflection-question">
              <legend>{{ question.prompt }}</legend>
              <label v-for="option in question.options" :key="option" class="reflection-option">
                <input
                  v-model="profileReflection[question.id]"
                  type="radio"
                  :name="`reflection-${question.id}`"
                  :value="option"
                >
                <span>{{ option }}</span>
              </label>
            </fieldset>
            <button class="quiet-link reflection-clear" type="button" @click="clearProfileReflection">Clear responses</button>
            <button
              v-if="hasProfileReflection"
              class="quiet-link reflection-use-chat"
              type="button"
              @click="useReflectionInNextChat"
            >
              Use selected responses in Check-in Chat
            </button>
            <p v-if="hasProfileReflection" class="reflection-note">Use these choices once to help select a practice in your next chat message.</p>
            <p class="reflection-note">There is no score or conclusion.</p>
          </div>
        </section>

        <div class="bottom-actions">
          <button class="primary-button" type="button" @click="returnToDashboard">Done</button>
        </div>
      </template>

      <template v-else-if="screen === 'checkin'">
        <header class="app-header">
          <button class="leave-button" type="button" @click="leaveExercise">Leave check-in</button>
          <button class="crisis-button" type="button" @click="openCrisis">Crisis support</button>
        </header>

        <div class="hero-space compact">
          <h1>Journal Check-in</h1>
          <p>If you want, jot down a word or two. You can continue without sharing anything.</p>
        </div>

        <label class="checkin-box">
          <span>What feels most present? (optional)</span>
          <textarea
            v-model="checkinText"
            maxlength="280"
            placeholder="Type here…"
            :disabled="busy || Boolean(checkinReply)"
          />
        </label>

        <p v-if="busy" class="loading-note" role="status">Checking optional text… Crisis Support remains available.</p>
        <p v-else-if="isCheckinFallback" class="fallback-note" role="status">
          Optional check-in did not respond. You can continue without sharing or leave whenever you want.
        </p>
        <div class="bottom-actions">
          <button v-if="!checkinReply" class="secondary-button" type="button" :disabled="busy" @click="submitCheckin">
            {{ busy ? 'Sending…' : 'Use optional check-in' }}
          </button>
          <button class="primary-button" type="button" :disabled="busy" @click="enterSelectedSkill">
            Continue without sharing
          </button>
          <button v-if="checkinReply" class="quiet-link" type="button" @click="trySuggestedSkill">
            Try suggested {{ skillCopy[checkinReply.suggested_skill].label.toLowerCase() }}
          </button>
          <p class="footer-note">Crisis support remains available at any point.</p>
        </div>
      </template>

      <template v-else-if="screen === 'breathing'">
        <header class="app-header">
          <button class="leave-button" type="button" @click="leaveExercise">Leave exercise</button>
          <button class="crisis-button" type="button" @click="openCrisis">Crisis support</button>
        </header>

        <div class="practice-copy">
          <span>1 minute · 4 in / 6 out</span>
          <h1>{{ isPaused ? 'Paused' : breath.label }}</h1>
          <p>Follow the circle at your pace.</p>
        </div>

        <div
          class="breathing-wrap"
          :class="[breath.phase, { paused: isPaused }]"
          aria-label="Paced breathing visual cue. The visible words and count describe the current phase. Use Pause, Resume, or Leave exercise whenever you want."
        >
          <div class="breathing-circle">
            <strong>{{ breath.displayCount }}</strong>
            <span>{{ isPaused ? 'PAUSED' : breath.cue }}</span>
          </div>
        </div>
        <div class="cycle-copy">
          <strong>Cycle {{ breath.cycle }} of 6</strong>
          <p>{{ isPaused ? 'Take your time. Resume only if you want to.' : 'You can slow down, pause, or leave at any time.' }}</p>
          <span class="sr-only">{{ durationLabel }}</span>
        </div>

        <div class="bottom-actions">
          <button class="secondary-button" type="button" @click="togglePause">
            {{ isPaused ? 'Resume when ready' : 'Pause' }}
          </button>
        </div>
      </template>

      <template v-else-if="screen === 'stop'">
        <header class="app-header">
          <button class="leave-button" type="button" @click="leaveExercise">Leave exercise</button>
          <button class="crisis-button" type="button" @click="openCrisis">Crisis support</button>
        </header>

        <div class="practice-copy">
          <span>STOP · {{ stopStep + 1 }} of {{ STOP_STEPS.length }}</span>
          <h1>{{ currentStopStep.title }}</h1>
          <p>{{ currentStopStep.prompt }}</p>
        </div>

        <aside class="observe-card">
          <strong>{{ currentStopStep.note }}</strong>
          <p>{{ currentStopStep.detail }}</p>
        </aside>

        <div class="bottom-actions">
          <button class="primary-button" type="button" @click="nextStopStep">
            {{ stopStep === STOP_STEPS.length - 1 ? 'Finish practice' : 'Continue' }}
          </button>
          <button v-if="stopStep > 0" class="quiet-link" type="button" @click="previousStopStep">Back to the previous step</button>
        </div>
      </template>

      <template v-else-if="screen === 'finish'">
        <header class="app-header">
          <span>ClearSpace</span>
          <button class="crisis-button" type="button" @click="openCrisis">Crisis support</button>
        </header>

        <div class="hero-space finish-heading">
          <h1>You finished a short practice.</h1>
        </div>

        <section class="history-card" aria-label="Recent sessions">
          <div class="history-title">
            <strong>Recent sessions</strong>
            <button v-if="history.length" class="text-button" type="button" @click="clearHistory">Clear history</button>
          </div>
          <template v-if="historyItem">
            <p>
              {{ skillCopy[historyItem.skill].label }} ·
              {{ historyItem.seconds_completed ? `${historyItem.seconds_completed} seconds` : 'short practice' }}
            </p>
            <span>Check-in text and crisis-support activity are not retained.</span>
          </template>
          <p v-else>No sessions yet.</p>
        </section>

        <aside class="prototype-card control-card">
          <strong>You stay in control</strong>
          <span>Use the same skill again, choose another, or leave the prototype.</span>
        </aside>

        <div class="bottom-actions">
          <button class="primary-button" type="button" @click="useLastSkill">
            {{ historyItem ? 'Use last time’s skill' : 'Use this skill again' }}
          </button>
          <button class="quiet-link" type="button" @click="returnToActivitySelection">Choose another skill</button>
          <button class="quiet-link" type="button" @click="openHistory">View saved history</button>
        </div>
      </template>

      <template v-else-if="screen === 'history'">
        <header class="app-header">
          <button class="leave-button" type="button" @click="returnToActivitySelection">Close</button>
          <button class="crisis-button" type="button" @click="openCrisis">Crisis support</button>
        </header>

        <div class="hero-space compact history-heading">
          <h1>History</h1>
          <p>Past sessions can help you choose a familiar skill. Check-in text is not retained.</p>
        </div>

        <section class="history-list" aria-label="Session history">
          <p v-if="!history.length" class="empty-history">No sessions yet.</p>
          <button
            v-for="session in history"
            :key="session.id"
            class="history-session"
            :class="{ selected: historyDetail?.id === session.id }"
            type="button"
            @click="reviewSession(session.id)"
          >
            <strong>{{ skillCopy[session.skill].label }}</strong>
            <span>
              {{ session.status === 'left' ? 'Left when ready' : 'Completed' }} ·
              {{ session.seconds_completed ? `${session.seconds_completed} seconds` : 'short practice' }}
            </span>
            <small>{{ formatSessionTime(session.updated_at) }}</small>
          </button>
        </section>

        <section v-if="historyDetail" class="history-detail" aria-live="polite">
          <strong>Allowed check-in response</strong>
          <template v-if="allowedResponses.length">
            <p v-for="response in allowedResponses" :key="response.created_at">
              “{{ response.content }}”
              <span v-if="response.suggested_skill">Suggested: {{ skillCopy[response.suggested_skill].label }}.</span>
            </p>
          </template>
          <p v-else>No optional check-in response was saved for this session.</p>
          <small>Only the fixed response is shown here; your check-in text was not retained.</small>
        </section>

        <div class="bottom-actions">
          <button v-if="historyDetail" class="primary-button" type="button" @click="useHistorySkill">
            Use this skill again
          </button>
          <button v-if="history.length" class="secondary-button" type="button" @click="clearHistory">Clear history</button>
          <button class="quiet-link" type="button" @click="returnToActivitySelection">Choose another skill</button>
        </div>
      </template>

      <template v-else-if="screen === 'chat'">
        <header class="app-header">
          <button class="leave-button" type="button" @click="returnToActivitySelection">Close chat</button>
          <button class="crisis-button" type="button" @click="openCrisis">Crisis support</button>
        </header>

        <div class="hero-space compact chat-heading">
          <h1>What would you like to practice today?</h1>
        </div>

        <section class="voice-card" :data-status="voiceStatus" aria-label="Optional voice conversation">
          <span class="voice-icon" aria-hidden="true"><AppIcon name="microphone" /></span>
          <div>
            <strong>Voice conversation</strong>
            <p role="status" aria-live="polite">{{ voiceStatusText }}</p>
          </div>
          <button
            class="voice-start-button"
            type="button"
            :disabled="!voiceCanStart"
            @click="startVoiceConversation"
          >
            {{ voiceStartLabel }}
          </button>
          <button
            v-if="voiceCanMute || voiceStatus === 'muting'"
            class="voice-control-button"
            type="button"
            :disabled="voiceStatus === 'muting'"
            :aria-pressed="false"
            @click="muteVoiceConversation"
          >{{ voiceStatus === 'muting' ? 'Muting…' : 'Mute microphone' }}</button>
          <button
            v-if="voiceCanUnmute || voiceStatus === 'unmuting'"
            class="voice-control-button"
            type="button"
            :disabled="voiceStatus === 'unmuting'"
            :aria-pressed="true"
            @click="unmuteVoiceConversation"
          >{{ voiceStatus === 'unmuting' ? 'Unmuting…' : 'Unmute microphone' }}</button>
          <button
            v-if="voicePlaybackBlocked"
            class="quiet-link voice-audio-button"
            type="button"
            @click="enableAssistantAudio"
          >Enable assistant audio</button>
        </section>

        <aside class="chat-context-card" :class="{ enabled: profile.chat_personalization_enabled }">
          <strong>{{ profile.chat_personalization_enabled ? 'Practice context is on' : 'Practice context is off' }}</strong>
          <span v-if="profile.chat_personalization_enabled">Chat suggestions may use your selected practice and a short completed-practice summary. You can change this in Profile.</span>
          <span v-else>Chat uses this conversation’s saved messages. You can turn on an optional practice summary in Profile.</span>
        </aside>

        <aside v-if="reflectionForNextChat" class="chat-context-card reflection-chat-ready">
          <strong>Optional reflection ready</strong>
          <span>Your selected responses will be used only with this next message to help choose a practice.</span>
          <button class="quiet-link" type="button" :disabled="chatBusy" @click="discardReflectionForChat">Don’t use reflection</button>
        </aside>

        <section class="chat-transcript" aria-live="polite" aria-label="Chat messages">
          <p v-if="!activeConversation?.messages?.length" class="empty-history">
            {{ chatBusy ? 'Opening a chat…' : "We don't offer therapy, just a safe space to land." }}
          </p>
          <article
            v-for="message in activeConversation?.messages || []"
            :key="message.id"
            class="chat-message"
            :class="message.role"
          >
            <strong>{{ message.role === 'user' ? 'You' : 'Chatbot' }}</strong>
            <p>{{ message.content }}</p>
            <small :aria-label="`${formatSessionTime(message.created_at)} · ${message.status}`">
              {{ formatSessionTime(message.created_at) }}
            </small>
            <section v-if="message.suggested_skill" class="chat-skill-detail">
              <strong>About {{ skillCopy[message.suggested_skill].label }}</strong>
              <p>{{ skillCopy[message.suggested_skill].chatDetail }}</p>
            </section>
            <aside v-if="message.suggested_skill" class="chat-research-note">
              <strong>Research context</strong>
              <p>{{ skillCopy[message.suggested_skill].researchDetail }}</p>
              <a
                :href="skillCopy[message.suggested_skill].researchUrl"
                target="_blank"
                rel="noreferrer"
              >{{ skillCopy[message.suggested_skill].researchCitation }} <span aria-hidden="true">↗</span></a>
            </aside>
            <button
              v-if="message.suggested_skill"
              class="chat-suggestion"
              type="button"
              :disabled="chatBusy"
              @click="beginSuggestedSkill(message.suggested_skill)"
            >
              Try {{ skillCopy[message.suggested_skill].label }}
            </button>
          </article>
        </section>

        <label class="checkin-box chat-box">
          <textarea
            v-model="chatText"
            aria-label="Message for the chatbot"
            maxlength="800"
            placeholder="example: I am feeling anxious today. What should I do?"
            :disabled="chatBusy || !activeConversation"
          />
        </label>
        <p v-if="chatBusy" class="loading-note" role="status">
          Retrieving saved context… Crisis Support remains available.
        </p>
        <p v-else-if="chatFailure" class="fallback-note" role="status">
          The chatbot did not reply. Your message may be saved as failed; you can try later, start a skill, or leave.
        </p>

        <details v-if="chatHistory.length" class="chat-history">
          <summary>Open chat history ({{ chatHistory.length }})</summary>
          <button
            v-for="conversation in chatHistory"
            :key="conversation.id"
            class="history-session"
            :class="{ selected: activeConversation?.id === conversation.id }"
            type="button"
            :disabled="chatBusy"
            @click="openSavedChat(conversation.id)"
          >
            <strong>{{ conversation.message_count }} saved message{{ conversation.message_count === 1 ? '' : 's' }}</strong>
            <small>{{ formatSessionTime(conversation.updated_at) }}</small>
          </button>
        </details>

        <div class="bottom-actions">
          <button class="primary-button" type="button" :disabled="chatBusy || !chatText.trim() || !activeConversation" @click="sendChatMessage">
            {{ chatBusy ? 'Working…' : 'Ask chatbot' }}
          </button>
          <button class="quiet-link" type="button" :disabled="chatBusy" @click="startNewChat">Start a new chat</button>
          <button v-if="chatHistory.length" class="quiet-link" type="button" :disabled="chatBusy" @click="clearChatHistory">Clear chat history</button>
          <button class="quiet-link" type="button" @click="returnToActivitySelection">Choose a skill instead</button>
        </div>
        <p class="chat-boundary">Coursework skills-practice prototype · fictional scenarios only · not therapy or emergency care.</p>
      </template>

      <template v-else-if="screen === 'crisis'">
        <header class="app-header">
          <button class="leave-button" type="button" @click="closeCrisis">Close</button>
        </header>

        <div class="crisis-copy">
          <span class="urgent-label">U.S. prototype information</span>
          <h1>Crisis support</h1>
          <p>If you may be in immediate danger, call 911 now. This screen is configured for the United States and its territories.</p>
        </div>

        <a class="emergency-button" href="tel:911" aria-label="Call 911 emergency services">
          <strong>Call 911 emergency services</strong>
          <span>For immediate danger in the United States and its territories.</span>
        </a>
        <a class="lifeline-card" href="tel:988" aria-label="Call the 988 Suicide and Crisis Lifeline">
          <strong>Call 988</strong>
          <span>U.S. 988 Lifeline. Text 988 or use its official chat options if you prefer.</span>
        </a>
        <a class="source-link" href="https://988lifeline.org/get-help/" target="_blank" rel="noreferrer">
          Source: 988 Lifeline — Get Help
        </a>
        <a class="trusted-person-card" href="mailto:?subject=Could%20you%20stay%20with%20me%3F">
          <strong>Contact a trusted person</strong>
          <span>Ask someone to stay with you or help you find support.</span>
        </a>

        <aside class="disclosure-card">
          <strong>Prototype disclosure</strong>
          <p>This coursework prototype is not an emergency service and does not replace professional help. It does not identify your location, track crisis-support use, or monitor you.</p>
          <p>For use outside the U.S., local resources must be selected and verified before a real deployment.</p>
        </aside>

        <div class="bottom-actions">
          <button class="primary-button" type="button" @click="closeCrisis">Return to ClearSpace</button>
        </div>
      </template>

      <nav v-if="tabNavigationVisible" class="bottom-nav" aria-label="Primary navigation">
        <button
          class="bottom-nav-item"
          :class="{ active: activeNavigationTab === 'home' }"
          type="button"
          :aria-current="activeNavigationTab === 'home' ? 'page' : undefined"
          @click="openNavigationTab('home')"
        >
          <AppIcon name="home" />
          <span>Home</span>
        </button>
        <button
          class="bottom-nav-item"
          :class="{ active: activeNavigationTab === 'activities' }"
          type="button"
          :aria-current="activeNavigationTab === 'activities' ? 'page' : undefined"
          @click="openNavigationTab('activities')"
        >
          <AppIcon name="activities" />
          <span>Activities</span>
        </button>
        <button
          class="bottom-nav-item"
          :class="{ active: activeNavigationTab === 'chat' }"
          type="button"
          :aria-current="activeNavigationTab === 'chat' ? 'page' : undefined"
          @click="openNavigationTab('chat')"
        >
          <AppIcon name="chat" />
          <span>Chat</span>
        </button>
        <button
          class="bottom-nav-item"
          :class="{ active: activeNavigationTab === 'calendar' }"
          type="button"
          :aria-current="activeNavigationTab === 'calendar' ? 'page' : undefined"
          @click="openNavigationTab('calendar')"
        >
          <AppIcon name="calendar" />
          <span>Calendar</span>
        </button>
        <button
          class="bottom-nav-item"
          :class="{ active: activeNavigationTab === 'profile' }"
          type="button"
          :aria-current="activeNavigationTab === 'profile' ? 'page' : undefined"
          @click="openNavigationTab('profile')"
        >
          <AppIcon name="profile" />
          <span>Profile</span>
        </button>
        <button class="bottom-nav-item crisis-tab" type="button" @click="openNavigationTab('crisis')">
          <AppIcon name="crisis" />
          <span>Crisis</span>
        </button>
      </nav>
    </section>
  </main>
</template>
