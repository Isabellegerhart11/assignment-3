import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('./api', () => ({
  api: {
    clearMoods: vi.fn(),
    clearProfile: vi.fn(),
    clearSessions: vi.fn(),
    clearConversations: vi.fn(),
    createConversation: vi.fn(),
    createSession: vi.fn(),
    createVoiceSession: vi.fn(),
    finishSession: vi.fn(),
    getConversation: vi.fn(),
    getProfile: vi.fn(),
    getVoiceConfiguration: vi.fn(),
    getSession: vi.fn(),
    listMoods: vi.fn(),
    listConversations: vi.fn(),
    listSessions: vi.fn(),
    sendConversationMessage: vi.fn(),
    saveMood: vi.fn(),
    removeMood: vi.fn(),
    submitCheckin: vi.fn(),
    updateProfile: vi.fn(),
  },
}))

import App from './App.vue'
import { api } from './api'
import { TOTAL_SECONDS } from './breathing'

const FICTIONAL_SESSION_ID = 'fictional-session-001'

function configureApi() {
  const profile = {
    preferred_skill: null,
    motion_preference: 'system',
    chat_personalization_enabled: false,
    updated_at: '2026-01-01T12:00:00Z',
  }
  const conversation = {
    id: 'fictional-conversation-001',
    created_at: '2026-01-01T12:00:00Z',
    updated_at: '2026-01-01T12:00:00Z',
    message_count: 0,
    messages: [],
  }
  api.clearConversations.mockResolvedValue(null)
  api.clearMoods.mockResolvedValue(null)
  api.clearProfile.mockResolvedValue(profile)
  api.clearSessions.mockResolvedValue(null)
  api.createConversation.mockResolvedValue(conversation)
  api.createSession.mockResolvedValue({ id: FICTIONAL_SESSION_ID })
  api.createVoiceSession.mockResolvedValue({
    session_id: 'fictional-live-session-001',
    sdp_answer: 'fictional-answer',
    max_session_seconds: 300,
  })
  api.finishSession.mockResolvedValue({ id: FICTIONAL_SESSION_ID })
  api.getConversation.mockResolvedValue(conversation)
  api.getProfile.mockResolvedValue(profile)
  api.getVoiceConfiguration.mockResolvedValue({ configured: false, max_session_seconds: 300 })
  api.getSession.mockResolvedValue({ conversation: [] })
  api.listConversations.mockResolvedValue([])
  api.listMoods.mockResolvedValue([])
  api.listSessions.mockResolvedValue([])
  api.sendConversationMessage.mockResolvedValue({
    ...conversation,
    message_count: 2,
    messages: [
      {
        id: 'fictional-user-message-001',
        role: 'user',
        content: 'Fictional saved context question.',
        status: 'complete',
        suggested_skill: null,
        supporting_message_ids: [],
        created_at: '2026-01-01T12:00:00Z',
      },
      {
        id: 'fictional-assistant-message-001',
        role: 'assistant',
        content: 'Fictional grounded reply.',
        status: 'complete',
        suggested_skill: 'paced_breathing',
        supporting_message_ids: ['fictional-user-message-001'],
        created_at: '2026-01-01T12:00:01Z',
      },
    ],
  })
  api.submitCheckin.mockResolvedValue({
    acknowledgement: 'Thanks for naming that.',
    suggested_skill: 'paced_breathing',
  })
  api.saveMood.mockImplementation(async (day, mood) => ({
    day,
    mood,
    updated_at: '2026-01-01T12:00:01Z',
  }))
  api.removeMood.mockResolvedValue(null)
  api.updateProfile.mockImplementation(async (nextProfile) => ({
    ...nextProfile,
    updated_at: '2026-01-01T12:00:01Z',
  }))
}

async function mountApp() {
  const wrapper = mount(App)
  await flushPromises()
  return wrapper
}

async function openActivities(wrapper) {
  await wrapper.findAll('button').find((button) => button.text().includes('All activities')).trigger('click')
  await flushPromises()
}

async function startPacedBreathing(wrapper) {
  await openActivities(wrapper)
  await wrapper.findAll('button').find((button) => button.text() === 'Start a 60-second reset').trigger('click')
  await flushPromises()
}

async function startOptionalCheckin(wrapper) {
  await openActivities(wrapper)
  await wrapper.vm.beginCheckin()
  await flushPromises()
}

describe('ClearSpace Part 3.2 flows', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    vi.setSystemTime(new Date('2026-01-01T12:00:00Z'))
    vi.clearAllMocks()
    window.localStorage.clear()
    configureApi()
  })

  afterEach(() => {
    vi.runOnlyPendingTimers()
    vi.useRealTimers()
  })

  it('lets a person choose and retain a theme from profile setup', async () => {
    const wrapper = await mountApp()

    expect(wrapper.get('.page-shell').attributes('data-theme')).toBe('forest')
    expect(wrapper.findAll('.theme-scenery-forest .forest-star')).toHaveLength(24)
    await wrapper.findAll('button').find((button) => button.text().includes('Profile setup')).trigger('click')
    expect(wrapper.get('h1').text()).toBe('Profile setup')

    const winterTheme = wrapper.findAll('.theme-option').find((button) => button.text().includes('Snowy Winter'))
    await winterTheme.trigger('click')
    expect(wrapper.findAll('.theme-scenery-snowy-winter .snowflake')).toHaveLength(30)

    const springTheme = wrapper.findAll('.theme-option').find((button) => button.text().includes('Spring'))
    await springTheme.trigger('click')
    expect(wrapper.findAll('.theme-scenery-spring .wildflower')).toHaveLength(48)

    const fallTheme = wrapper.findAll('.theme-option').find((button) => button.text().includes('Fall'))
    await fallTheme.trigger('click')

    expect(wrapper.get('.page-shell').attributes('data-theme')).toBe('fall')
    expect(window.localStorage.getItem('clearspace-theme')).toBe('fall')
    await wrapper.findAll('button').find((button) => button.text() === 'Done').trigger('click')
    await openActivities(wrapper)
    expect(wrapper.get('h1').text()).toBe('What would you like to practice?')
    wrapper.unmount()

    const restored = await mountApp()
    expect(restored.get('.page-shell').attributes('data-theme')).toBe('fall')
    restored.unmount()
  })

  it('uses nine concentric circles in the featured paced-breathing visual', async () => {
    const wrapper = await mountApp()

    expect(wrapper.findAll('.featured-orbit .featured-ring')).toHaveLength(9)
    wrapper.unmount()
  })

  it('provides bottom navigation to the existing activity, calendar, profile, and chat routes', async () => {
    const wrapper = await mountApp()
    const primaryNavigation = () => wrapper.get('nav[aria-label="Primary navigation"]')
    const navigate = async (label) => {
      await primaryNavigation().findAll('button').find((button) => button.text().includes(label)).trigger('click')
      await flushPromises()
    }

    expect(primaryNavigation().findAll('button')).toHaveLength(6)
    expect(primaryNavigation().get('button[aria-current="page"]').text()).toContain('Home')

    await navigate('Activities')
    expect(wrapper.get('h1').text()).toBe('What would you like to practice?')
    expect(primaryNavigation().get('button[aria-current="page"]').text()).toContain('Activities')

    await navigate('Calendar')
    expect(wrapper.get('h1').text()).toBe('Your days')

    await navigate('Profile')
    expect(wrapper.get('h1').text()).toBe('Profile setup')

    await navigate('Chat')
    expect(wrapper.get('h1').text()).toBe('What would you like to practice today?')

    await navigate('Crisis')
    expect(wrapper.get('h1').text()).toBe('Crisis support')
    expect(wrapper.find('nav[aria-label="Primary navigation"]').exists()).toBe(false)
    wrapper.unmount()
  })

  it('keeps text chat usable when optional voice is not configured', async () => {
    const wrapper = await mountApp()

    await wrapper.findAll('button').find((button) => button.text().includes('Talk it through')).trigger('click')
    await flushPromises()
    await wrapper.findAll('button').find((button) => button.text() === 'Start voice').trigger('click')
    await flushPromises()

    expect(wrapper.text()).toContain('Voice is not configured. You can keep using text chat.')
    expect(wrapper.get('textarea[aria-label="Message for the chatbot"]').attributes('disabled')).toBeUndefined()
    expect(api.createVoiceSession).not.toHaveBeenCalled()
    wrapper.unmount()
  })

  it('uses an anonymous preference for the home starting point and lets the person override or clear it', async () => {
    const wrapper = await mountApp()

    await wrapper.findAll('button').find((button) => button.text().includes('Profile setup')).trigger('click')
    await wrapper.get('input[name="preferred-skill"][value="stop"]').setValue()
    await flushPromises()
    expect(api.updateProfile).toHaveBeenLastCalledWith({
      preferred_skill: 'stop',
      motion_preference: 'system',
      chat_personalization_enabled: false,
    })

    await wrapper.get('input[name="motion-preference"][value="reduce"]').setValue()
    await flushPromises()
    expect(wrapper.get('.page-shell').attributes('data-motion')).toBe('reduce')

    await wrapper.get('input[type="checkbox"]').setValue(true)
    await flushPromises()
    expect(api.updateProfile).toHaveBeenLastCalledWith({
      preferred_skill: 'stop',
      motion_preference: 'reduce',
      chat_personalization_enabled: true,
    })

    await wrapper.findAll('button').find((button) => button.text() === 'Done').trigger('click')
    expect(wrapper.text()).toContain('Your selected practice')
    expect(wrapper.get('.featured-practice').text()).toContain('STOP skill')
    await wrapper.findAll('button').find((button) => button.text() === 'Choose another activity').trigger('click')
    expect(wrapper.get('h1').text()).toBe('What would you like to practice?')

    await wrapper.findAll('button').find((button) => button.text() === 'Home').trigger('click')
    await wrapper.findAll('button').find((button) => button.text().includes('Profile setup')).trigger('click')
    await wrapper.findAll('button').find((button) => button.text() === 'Clear practice preferences').trigger('click')
    await flushPromises()
    expect(api.clearProfile).toHaveBeenCalledTimes(1)
    wrapper.unmount()
  })

  it('offers an optional, unscored right-now reflection only in profile setup', async () => {
    const wrapper = await mountApp()

    await wrapper.findAll('button').find((button) => button.text().includes('Profile setup')).trigger('click')
    expect(wrapper.text()).not.toContain('At this moment, I notice tension in my body.')

    await wrapper.findAll('button').find((button) => button.text().includes('Optional right-now reflection')).trigger('click')
    expect(wrapper.text()).toContain('They are not the STAI or a standardized assessment.')
    expect(wrapper.text()).toContain('There is no score or conclusion.')
    expect(wrapper.find('.profile-reflection').findAll('input[type="radio"]').length).toBe(16)

    const firstResponse = wrapper.get('input[name="reflection-body_tension"][value="Not at all"]')
    await firstResponse.setValue()
    expect(firstResponse.element.checked).toBe(true)
    expect(api.createSession).not.toHaveBeenCalled()
    expect(api.submitCheckin).not.toHaveBeenCalled()

    await wrapper.findAll('button').find((button) => button.text() === 'Clear responses').trigger('click')
    expect(wrapper.find('.profile-reflection').findAll('input[type="radio"]:checked')).toHaveLength(0)

    await wrapper.findAll('button').find((button) => button.text() === 'Close').trigger('click')
    await wrapper.findAll('button').find((button) => button.text().includes('Profile setup')).trigger('click')
    expect(wrapper.find('.profile-reflection').findAll('input[type="radio"]')).toHaveLength(0)
    wrapper.unmount()
  })

  it('uses selected reflection responses for one chat request without keeping them in the UI', async () => {
    const wrapper = await mountApp()

    await wrapper.findAll('button').find((button) => button.text().includes('Profile setup')).trigger('click')
    await wrapper.findAll('button').find((button) => button.text().includes('Optional right-now reflection')).trigger('click')
    await wrapper.get('input[name="reflection-body_tension"][value="Very much"]').setValue()

    await wrapper.findAll('button').find((button) => button.text() === 'Use selected responses in Check-in Chat').trigger('click')
    await flushPromises()
    expect(wrapper.get('h1').text()).toBe('What would you like to practice today?')
    expect(wrapper.text()).toContain('Optional reflection ready')

    await wrapper.get('textarea[aria-label="Message for the chatbot"]').setValue('Which practice could I start with?')
    await wrapper.findAll('button').find((button) => button.text() === 'Ask chatbot').trigger('click')
    await flushPromises()

    expect(api.sendConversationMessage).toHaveBeenCalledWith(
      'fictional-conversation-001',
      'Which practice could I start with?',
      expect.any(String),
      { body_tension: 'Very much' },
    )
    expect(wrapper.text()).not.toContain('Optional reflection ready')
    wrapper.unmount()
  })

  it('lets a person record, revise, remove, and clear an explicit daily mood choice', async () => {
    const wrapper = await mountApp()

    await wrapper.findAll('button').find((button) => button.text().includes('Your days')).trigger('click')
    await flushPromises()

    expect(wrapper.get('h1').text()).toBe('Your days')
    expect(wrapper.get('.calendar-card').exists()).toBe(true)
    expect(wrapper.find('.daily-mood-card textarea').exists()).toBe(false)
    expect(wrapper.get('button[aria-label="Previous month"] .app-icon-svg').exists()).toBe(true)
    expect(wrapper.get('button[aria-label="Next month"] .app-icon-svg').exists()).toBe(true)
    expect(wrapper.findAll('.mood-face .app-icon-svg')).toHaveLength(5)
    expect(wrapper.text()).toContain('Self-reported mood')
    expect(wrapper.text()).toContain('Saved activity')

    await wrapper.get('button.mood-good').trigger('click')
    await flushPromises()
    expect(api.saveMood).toHaveBeenCalledWith(expect.stringMatching(/^\d{4}-\d{2}-\d{2}$/), 'good')
    expect(wrapper.text()).toContain('Selected: Good. You can change it any time.')

    await wrapper.get('button.mood-very_good').trigger('click')
    await flushPromises()
    expect(api.saveMood).toHaveBeenLastCalledWith(expect.stringMatching(/^\d{4}-\d{2}-\d{2}$/), 'very_good')

    await wrapper.findAll('button').find((button) => button.text() === 'Remove mood').trigger('click')
    await flushPromises()
    expect(api.removeMood).toHaveBeenCalledWith(expect.stringMatching(/^\d{4}-\d{2}-\d{2}$/))

    await wrapper.get('button.mood-low').trigger('click')
    await flushPromises()
    await wrapper.findAll('button').find((button) => button.text() === 'Clear all moods').trigger('click')
    await flushPromises()
    expect(api.clearMoods).toHaveBeenCalledTimes(1)

    await wrapper.get('button[aria-label="Next month"]').trigger('click')
    await flushPromises()
    expect(api.listMoods).toHaveBeenLastCalledWith(expect.stringMatching(/^\d{4}-\d{2}$/))
    wrapper.unmount()
  })

  it('records completion after the full fictional paced-breathing practice', async () => {
    const wrapper = await mountApp()

    await startPacedBreathing(wrapper)
    expect(wrapper.get('h1').text()).toBe('Breathe in')
    expect(wrapper.text()).not.toContain('End practice')

    await vi.advanceTimersByTimeAsync(TOTAL_SECONDS * 1000)
    await flushPromises()

    expect(api.finishSession).toHaveBeenCalledWith(
      FICTIONAL_SESSION_ID,
      'completed',
      TOTAL_SECONDS,
    )
    expect(wrapper.get('h1').text()).toBe('You finished a short practice.')
    wrapper.unmount()
  })

  it('keeps the breathing cue understandable without a live countdown announcement', async () => {
    const wrapper = await mountApp()

    await startPacedBreathing(wrapper)

    const cue = wrapper.get('.breathing-wrap')
    expect(cue.attributes('aria-live')).toBeUndefined()
    expect(cue.attributes('aria-label')).toContain('Paced breathing visual cue')
    expect(wrapper.findAll('button').some((button) => button.text() === 'Pause')).toBe(true)
    expect(wrapper.find('nav[aria-label="Primary navigation"]').exists()).toBe(false)
    expect(wrapper.find('.theme-scenery').exists()).toBe(false)
    wrapper.unmount()
  })

  it.each([
    ['paced breathing', async (wrapper) => startPacedBreathing(wrapper)],
    [
      'STOP',
      async (wrapper) => {
        await openActivities(wrapper)
        await wrapper.findAll('button').find((button) => button.text().includes('STOP skill')).trigger('click')
        await wrapper.get('button.primary-button').trigger('click')
        await flushPromises()
      },
    ],
  ])('lets a user leave the %s skill without penalty', async (_label, beginSkill) => {
    const wrapper = await mountApp()

    await beginSkill(wrapper)
    await wrapper.get('.leave-button').trigger('click')
    await flushPromises()

    expect(api.finishSession).toHaveBeenCalledWith(FICTIONAL_SESSION_ID, 'left', 0)
    expect(wrapper.get('h1').text()).toBe('What would you like to practice?')
    wrapper.unmount()
  })

  it('returns home immediately when saving a voluntary exit is delayed', async () => {
    let resolveExit
    api.finishSession.mockImplementation(
      () =>
        new Promise((resolve) => {
          resolveExit = resolve
        }),
    )
    const wrapper = await mountApp()

    await startPacedBreathing(wrapper)
    await wrapper.get('.leave-button').trigger('click')

    expect(wrapper.get('h1').text()).toBe('What would you like to practice?')
    resolveExit({ id: FICTIONAL_SESSION_ID })
    await flushPromises()
    wrapper.unmount()
  })

  it('lets a user skip the optional check-in without sending text', async () => {
    const wrapper = await mountApp()

    await startOptionalCheckin(wrapper)
    await wrapper.findAll('button').find((button) => button.text() === 'Continue without sharing').trigger('click')
    await flushPromises()

    expect(api.submitCheckin).not.toHaveBeenCalled()
    expect(wrapper.get('h1').text()).toBe('Breathe in')
    wrapper.unmount()
  })

  it('does not surface unexpected backend error contents in the interface', async () => {
    api.createSession.mockRejectedValue(new Error('Fictional private wording must not be echoed.'))
    const wrapper = await mountApp()

    await startPacedBreathing(wrapper)

    expect(wrapper.text()).toContain('A new practice could not be saved.')
    expect(wrapper.text()).not.toContain('Fictional private wording')
    wrapper.unmount()
  })

  it('keeps Crisis Support available while a fictional model request waits and after it fails', async () => {
    let resolveCheckin
    api.submitCheckin.mockImplementation(
      () =>
        new Promise((resolve) => {
          resolveCheckin = resolve
        }),
    )
    const wrapper = await mountApp()

    await startOptionalCheckin(wrapper)
    await wrapper.get('textarea').setValue('Fictional test check-in for a short practice.')
    await wrapper.findAll('button').find((button) => button.text() === 'Use optional check-in').trigger('click')

    expect(wrapper.text()).toContain('Checking optional text')
    await wrapper.get('.crisis-button').trigger('click')
    expect(wrapper.get('h1').text()).toBe('Crisis support')
    expect(wrapper.get('a[href="tel:988"]').exists()).toBe(true)

    await wrapper.get('.leave-button').trigger('click')
    resolveCheckin({
      acknowledgement: 'You can continue without sharing anything.',
      suggested_skill: 'paced_breathing',
    })
    await flushPromises()

    expect(wrapper.text()).toContain('Optional check-in did not respond.')
    expect(wrapper.get('.leave-button').text()).toBe('Leave check-in')
    await wrapper.get('.crisis-button').trigger('click')

    expect(wrapper.get('h1').text()).toBe('Crisis support')
    expect(wrapper.get('a[href="tel:988"]').exists()).toBe(true)
    wrapper.unmount()
  })

  it('ignores a late fictional check-in response after leaving', async () => {
    let resolveCheckin
    api.submitCheckin.mockImplementation(
      () =>
        new Promise((resolve) => {
          resolveCheckin = resolve
        }),
    )
    const wrapper = await mountApp()

    await startOptionalCheckin(wrapper)
    await wrapper.get('textarea').setValue('Fictional check-in that is left immediately.')
    await wrapper.findAll('button').find((button) => button.text() === 'Use optional check-in').trigger('click')
    await wrapper.get('.leave-button').trigger('click')
    resolveCheckin({
      acknowledgement: 'Thanks for naming that.',
      suggested_skill: 'paced_breathing',
    })
    await flushPromises()

    expect(wrapper.get('h1').text()).toBe('What would you like to practice?')
    expect(wrapper.text()).not.toContain('Thanks for naming that.')
    wrapper.unmount()
  })

  it('keeps Crisis Support available during normal fictional use', async () => {
    const wrapper = await mountApp()

    await wrapper.get('.crisis-button').trigger('click')

    expect(wrapper.get('h1').text()).toBe('Crisis support')
    expect(wrapper.get('a[href="tel:911"]').exists()).toBe(true)
    wrapper.unmount()
  })

  it('sends one fictional chat message and shows the saved grounded reply', async () => {
    const wrapper = await mountApp()

    await openActivities(wrapper)
    await wrapper.findAll('button').find((button) => button.text().includes('Check-in Chat')).trigger('click')
    await flushPromises()
    await wrapper.get('textarea').setValue('Fictional saved context question.')
    await wrapper.findAll('button').find((button) => button.text() === 'Ask chatbot').trigger('click')
    await flushPromises()

    expect(api.sendConversationMessage).toHaveBeenCalledWith(
      'fictional-conversation-001',
      'Fictional saved context question.',
      expect.any(String),
    )
    expect(wrapper.text()).toContain('Fictional grounded reply.')
    expect(wrapper.text()).toContain('A 60-second guided practice: follow the circle for four counts in and six counts out, for six cycles.')
    expect(wrapper.text()).toContain('A 2023 systematic review found that many studied breathing programs used guided, slower breathing.')
    expect(wrapper.text()).not.toContain('Records:')

    const researchSource = wrapper.get('.chat-research-note a')
    expect(researchSource.attributes('href')).toBe('https://doi.org/10.3390/brainsci13121612')

    const suggestedSkill = wrapper.get('.chat-suggestion')
    expect(suggestedSkill.text()).toBe('Try Paced breathing')
    await suggestedSkill.trigger('click')
    await flushPromises()
    expect(api.createSession).toHaveBeenCalledWith('paced_breathing')
    expect(wrapper.get('h1').text()).toBe('Breathe in')
    wrapper.unmount()
  })

  it('shows the reviewed STOP source when the chatbot suggests STOP', async () => {
    api.sendConversationMessage.mockResolvedValueOnce({
      id: 'fictional-conversation-001',
      message_count: 2,
      messages: [
        {
          id: 'fictional-user-message-002',
          role: 'user',
          content: 'Fictional pause question.',
          status: 'complete',
          suggested_skill: null,
          supporting_message_ids: [],
          created_at: '2026-01-01T12:00:00Z',
        },
        {
          id: 'fictional-assistant-message-002',
          role: 'assistant',
          content: 'A fictional STOP suggestion.',
          status: 'complete',
          suggested_skill: 'stop',
          supporting_message_ids: ['fictional-user-message-002'],
          created_at: '2026-01-01T12:00:01Z',
        },
      ],
    })
    const wrapper = await mountApp()

    await openActivities(wrapper)
    await wrapper.findAll('button').find((button) => button.text().includes('Check-in Chat')).trigger('click')
    await flushPromises()
    await wrapper.get('textarea').setValue('Fictional pause question.')
    await wrapper.findAll('button').find((button) => button.text() === 'Ask chatbot').trigger('click')
    await flushPromises()

    expect(wrapper.text()).toContain('A four-step, user-paced walkthrough: Stop, Take a step back, Observe, and Proceed mindfully.')
    expect(wrapper.text()).toContain('A 2022 study of a 30-lesson school DBT skills program reported good acceptability')
    expect(wrapper.get('.chat-research-note a').attributes('href')).toBe('https://doi.org/10.3390/ijerph19010494')
    wrapper.unmount()
  })

  it('keeps Crisis Support available while the fictional RAG request fails', async () => {
    api.sendConversationMessage.mockRejectedValue(new Error('Fictional provider failure.'))
    api.getConversation.mockResolvedValue({
      id: 'fictional-conversation-001',
      messages: [
        {
          id: 'fictional-user-message-001',
          role: 'user',
          content: 'Fictional saved context question.',
          status: 'failed',
          supporting_message_ids: [],
          created_at: '2026-01-01T12:00:00Z',
        },
      ],
    })
    const wrapper = await mountApp()

    await openActivities(wrapper)
    await wrapper.findAll('button').find((button) => button.text().includes('Check-in Chat')).trigger('click')
    await flushPromises()
    await wrapper.get('textarea').setValue('Fictional saved context question.')
    await wrapper.findAll('button').find((button) => button.text() === 'Ask chatbot').trigger('click')
    await flushPromises()

    expect(wrapper.text()).toContain('The chatbot did not reply.')
    await wrapper.get('.crisis-button').trigger('click')
    expect(wrapper.get('h1').text()).toBe('Crisis support')
    expect(wrapper.get('a[href="tel:988"]').exists()).toBe(true)
    wrapper.unmount()
  })
})
