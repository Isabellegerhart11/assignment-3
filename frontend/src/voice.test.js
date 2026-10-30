import { describe, expect, it, vi } from 'vitest'

import { createVoiceConnection } from './voice'

class FakeEventTarget {
  constructor() {
    this.listeners = new Map()
  }

  addEventListener(type, listener) {
    this.listeners.set(type, [...(this.listeners.get(type) || []), listener])
  }

  removeEventListener(type, listener) {
    this.listeners.set(type, (this.listeners.get(type) || []).filter((item) => item !== listener))
  }

  emit(type, event = {}) {
    for (const listener of this.listeners.get(type) || []) listener(event)
  }
}

class FakeDataChannel extends FakeEventTarget {
  constructor(label) {
    super()
    this.label = label
    this.readyState = 'open'
    this.send = vi.fn()
    this.close = vi.fn()
  }
}

class FakePeerConnection extends FakeEventTarget {
  constructor(callOrder) {
    super()
    this.callOrder = callOrder
    this.iceGatheringState = 'complete'
    this.connectionState = 'new'
    this.localDescription = null
    this.remoteDescription = null
    this.dataChannel = null
    this.addTrack = vi.fn()
    this.ontrack = null
    this.close = vi.fn(() => {
      this.connectionState = 'closed'
      this.emit('connectionstatechange')
    })
  }

  createDataChannel(label) {
    this.callOrder.push('data-channel')
    this.dataChannel = new FakeDataChannel(label)
    return this.dataChannel
  }

  async createOffer() {
    this.callOrder.push('offer')
    return { type: 'offer', sdp: 'v=0\r\nfake-offer' }
  }

  async setLocalDescription(description) {
    this.localDescription = description
  }

  async setRemoteDescription(description) {
    this.remoteDescription = description
    this.ontrack?.({ streams: [{ id: 'remote-fake-stream' }] })
  }
}

function fakeMicrophoneStream() {
  const track = new FakeEventTarget()
  track.stop = vi.fn()
  return { stream: { getTracks: () => [track] }, track }
}

function fakeAudio(play = vi.fn().mockResolvedValue(undefined)) {
  return {
    autoplay: false,
    srcObject: null,
    pause: vi.fn(),
    play,
    remove: vi.fn(),
    setAttribute: vi.fn(),
  }
}

describe('native voice connection controller', () => {
  it('does not ask for the microphone when FastAPI reports voice is unavailable', async () => {
    const getUserMedia = vi.fn()
    const statuses = []
    const controller = createVoiceConnection({
      getConfiguration: vi.fn().mockResolvedValue({ configured: false }),
      createSession: vi.fn(),
      mediaDevices: { getUserMedia },
      PeerConnection: FakePeerConnection,
      onStatus: (state) => statuses.push(state),
    })

    await controller.start()

    expect(getUserMedia).not.toHaveBeenCalled()
    expect(statuses.at(-1)).toEqual({ status: 'error', error: 'unavailable' })
  })

  it('keeps text fallback possible after microphone permission is denied', async () => {
    const denial = Object.assign(new Error('permission denied'), { name: 'NotAllowedError' })
    const statuses = []
    const createSession = vi.fn()
    const controller = createVoiceConnection({
      getConfiguration: vi.fn().mockResolvedValue({ configured: true }),
      createSession,
      mediaDevices: { getUserMedia: vi.fn().mockRejectedValue(denial) },
      PeerConnection: FakePeerConnection,
      onStatus: (state) => statuses.push(state),
    })

    await controller.start()

    expect(createSession).not.toHaveBeenCalled()
    expect(statuses.at(-1)).toEqual({ status: 'error', error: 'permission' })
  })

  it('creates the data channel before the offer and confirms mute changes through provider events', async () => {
    const callOrder = []
    let peer = null
    const { stream, track } = fakeMicrophoneStream()
    const statuses = []
    const audio = fakeAudio()
    const PeerConnection = class extends FakePeerConnection {
      constructor() {
        super(callOrder)
        peer = this
      }
    }
    const createSession = vi.fn().mockResolvedValue({
      session_id: 'fictional-live-session-001',
      sdp_answer: 'v=0\r\nfake-answer',
      max_session_seconds: 300,
    })
    const controller = createVoiceConnection({
      getConfiguration: vi.fn().mockResolvedValue({ configured: true }),
      createSession,
      mediaDevices: { getUserMedia: vi.fn().mockResolvedValue(stream) },
      PeerConnection,
      createAudio: () => audio,
      onStatus: (state) => statuses.push(state),
    })

    await controller.start()

    expect(callOrder).toEqual(['data-channel', 'offer'])
    expect(peer.dataChannel.label).toBe('oai-events')
    expect(createSession).toHaveBeenCalledWith('v=0\r\nfake-offer')
    expect(peer.remoteDescription).toEqual({ type: 'answer', sdp: 'v=0\r\nfake-answer' })
    expect(statuses.some((state) => state.status === 'active')).toBe(false)
    expect(audio.play).toHaveBeenCalledTimes(1)

    peer.dataChannel.emit('message', { data: JSON.stringify({ type: 'session.input_transcript.delta', delta: 'do not store me' }) })
    expect(statuses.some((state) => state.status === 'active')).toBe(false)

    peer.dataChannel.emit('message', { data: JSON.stringify({ type: 'session.started' }) })
    expect(statuses.at(-1)).toEqual({ status: 'active', error: null })

    expect(controller.mute()).toBe(true)
    expect(peer.dataChannel.send).toHaveBeenCalledWith(
      JSON.stringify({ type: 'session.input_audio.mute', event_id: 'voice-mute-1' }),
    )
    expect(statuses.at(-1)).toEqual({ status: 'muting', error: null })

    peer.dataChannel.emit('message', {
      data: JSON.stringify({ type: 'session.input_audio.muted', client_event_id: 'voice-mute-1' }),
    })
    expect(statuses.at(-1)).toEqual({ status: 'muted', error: null })

    expect(controller.unmute()).toBe(true)
    expect(peer.dataChannel.send).toHaveBeenLastCalledWith(
      JSON.stringify({ type: 'session.input_audio.unmute', event_id: 'voice-unmute-2' }),
    )
    expect(statuses.at(-1)).toEqual({ status: 'unmuting', error: null })

    peer.dataChannel.emit('message', {
      data: JSON.stringify({ type: 'session.input_audio.unmuted', client_event_id: 'voice-unmute-2' }),
    })
    expect(statuses.at(-1)).toEqual({ status: 'active', error: null })

    peer.dataChannel.emit('message', { data: JSON.stringify({ type: 'session.closed' }) })
    expect(statuses.slice(-2)).toEqual([
      { status: 'closing', error: null },
      { status: 'closed', error: null },
    ])
    expect(track.stop).toHaveBeenCalledTimes(1)
    expect(peer.close).toHaveBeenCalledTimes(1)
    expect(audio.remove).toHaveBeenCalledTimes(1)
  })

  it('offers a user-gesture playback retry when automatic assistant audio is blocked', async () => {
    const callOrder = []
    const { stream } = fakeMicrophoneStream()
    const blockedPlay = vi.fn().mockRejectedValueOnce(new Error('autoplay blocked')).mockResolvedValueOnce(undefined)
    const audio = fakeAudio(blockedPlay)
    const blockedStates = []
    const PeerConnection = class extends FakePeerConnection {
      constructor() {
        super(callOrder)
      }
    }
    const controller = createVoiceConnection({
      getConfiguration: vi.fn().mockResolvedValue({ configured: true }),
      createSession: vi.fn().mockResolvedValue({ sdp_answer: 'v=0\r\nfake-answer' }),
      mediaDevices: { getUserMedia: vi.fn().mockResolvedValue(stream) },
      PeerConnection,
      createAudio: () => audio,
      onPlaybackBlocked: (blocked) => blockedStates.push(blocked),
    })

    await controller.start()
    expect(blockedStates).toContain(true)

    await expect(controller.enableAssistantAudio()).resolves.toBe(true)
    expect(blockedStates.at(-1)).toBe(false)
  })
})
