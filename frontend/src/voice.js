const ALLOWED_DATA_CHANNEL_EVENTS = new Set([
  'session.started',
  'session.closed',
  'session.input_audio.muted',
  'session.input_audio.unmuted',
  'error',
])

const INPUT_AUDIO_CONTROLS = {
  mute: {
    requestType: 'session.input_audio.mute',
    confirmationType: 'session.input_audio.muted',
    pendingStatus: 'muting',
    confirmedStatus: 'muted',
    previousStatus: 'active',
  },
  unmute: {
    requestType: 'session.input_audio.unmute',
    confirmationType: 'session.input_audio.unmuted',
    pendingStatus: 'unmuting',
    confirmedStatus: 'active',
    previousStatus: 'muted',
  },
}

function permissionWasDenied(error) {
  return error?.name === 'NotAllowedError' || error?.name === 'SecurityError'
}

export function waitForIceGathering(connection) {
  if (connection.iceGatheringState === 'complete') return Promise.resolve()

  return new Promise((resolve) => {
    const onChange = () => {
      if (connection.iceGatheringState !== 'complete') return
      connection.removeEventListener('icegatheringstatechange', onChange)
      resolve()
    }
    connection.addEventListener('icegatheringstatechange', onChange)
  })
}

/**
 * Owns native browser media/WebRTC work separately from the Vue presentation.
 * It never saves audio, transcript events, or the returned provider session ID.
 */
export function createVoiceConnection({
  getConfiguration,
  createSession,
  mediaDevices = globalThis.navigator?.mediaDevices,
  PeerConnection = globalThis.RTCPeerConnection,
  createAudio = () => document.createElement('audio'),
  onStatus = () => {},
  onPlaybackBlocked = () => {},
} = {}) {
  let connection = null
  let dataChannel = null
  let microphoneStream = null
  let remoteAudio = null
  let starting = false
  let attemptId = 0
  let nextControlId = 0
  let pendingInputControl = null

  function setStatus(status, error = null) {
    onStatus({ status, error })
  }

  function clearResources() {
    const peer = connection
    const channel = dataChannel
    const stream = microphoneStream
    connection = null
    dataChannel = null
    microphoneStream = null
    pendingInputControl = null
    stream?.getTracks().forEach((track) => track.stop())
    channel?.close()
    peer?.close()
    if (remoteAudio) {
      remoteAudio.pause?.()
      remoteAudio.srcObject = null
      remoteAudio.remove?.()
      remoteAudio = null
    }
  }

  function handleDataChannelEvent(event) {
    if (!event || typeof event.type !== 'string' || !ALLOWED_DATA_CHANNEL_EVENTS.has(event.type)) {
      return
    }
    if (event.type === 'session.started') {
      setStatus('active')
      return
    }
    if (event.type === 'session.closed') {
      setStatus('closing')
      clearResources()
      setStatus('closed')
      return
    }
    if (
      event.type === pendingInputControl?.confirmationType
      && event.client_event_id === pendingInputControl.eventId
    ) {
      const confirmedStatus = pendingInputControl.confirmedStatus
      pendingInputControl = null
      setStatus(confirmedStatus)
      return
    }
    if (event.type === 'error' && event.error?.client_event_id === pendingInputControl?.eventId) {
      const previousStatus = pendingInputControl.previousStatus
      pendingInputControl = null
      setStatus(previousStatus, 'input-control')
      return
    }
    if (event.type !== 'error') return
    // Provider/debug details are intentionally ignored. The UI only needs an
    // app-owned failure state while text chat and Crisis Support remain usable.
    clearResources()
    setStatus('error', 'connection')
  }

  function bindConnectionEvents(peer, stream) {
    peer.addEventListener('connectionstatechange', () => {
      if (connection !== peer) return
      if (peer.connectionState === 'failed') setStatus('error', 'connection')
      if (peer.connectionState === 'closed') setStatus('closed')
    })
    peer.ontrack = (event) => {
      if (connection !== peer || !remoteAudio) return
      remoteAudio.srcObject = event.streams?.[0] || null
      void remoteAudio.play().catch(() => onPlaybackBlocked(true))
    }
    stream.getTracks().forEach((track) => peer.addTrack(track, stream))
  }

  async function start() {
    if (starting) return
    starting = true
    const attempt = ++attemptId
    onPlaybackBlocked(false)
    try {
      const configuration = await getConfiguration()
      if (attempt !== attemptId) return
      if (!configuration?.configured) {
        setStatus('error', 'unavailable')
        return
      }
      if (!mediaDevices?.getUserMedia || !PeerConnection) {
        setStatus('error', 'unsupported')
        return
      }

      setStatus('permission')
      microphoneStream = await mediaDevices.getUserMedia({ audio: true, video: false })
      if (attempt !== attemptId) {
        clearResources()
        return
      }
      connection = new PeerConnection()
      remoteAudio = createAudio()
      remoteAudio.autoplay = true
      remoteAudio.setAttribute?.('aria-hidden', 'true')
      bindConnectionEvents(connection, microphoneStream)

      // GPT-Live requires the data channel before the SDP offer is created.
      const channel = connection.createDataChannel('oai-events')
      dataChannel = channel
      channel.addEventListener('message', (browserEvent) => {
        if (dataChannel !== channel) return
        try {
          handleDataChannelEvent(JSON.parse(browserEvent.data))
        } catch {
          // Malformed and transcript/debug events have no display or storage path.
        }
      })

      setStatus('connecting')
      const offer = await connection.createOffer()
      await connection.setLocalDescription(offer)
      await waitForIceGathering(connection)
      if (attempt !== attemptId) return
      const sdp = connection.localDescription?.sdp
      if (!sdp) throw new Error('Missing SDP offer')

      const result = await createSession(sdp)
      if (attempt !== attemptId) return
      if (!result?.sdp_answer) throw new Error('Missing SDP answer')
      await connection.setRemoteDescription({ type: 'answer', sdp: result.sdp_answer })
      // The HTTP session request starts GPT-Live. Active waits for the
      // allowlisted session.started data-channel event.
    } catch (error) {
      if (attempt !== attemptId) return
      clearResources()
      setStatus('error', permissionWasDenied(error) ? 'permission' : 'connection')
    } finally {
      starting = false
    }
  }

  async function enableAssistantAudio() {
    if (!remoteAudio) return false
    try {
      await remoteAudio.play()
      onPlaybackBlocked(false)
      return true
    } catch {
      onPlaybackBlocked(true)
      return false
    }
  }

  function updateInputAudio(controlName) {
    const control = INPUT_AUDIO_CONTROLS[controlName]
    if (
      !control
      || !connection
      || !dataChannel
      || dataChannel.readyState === 'closed'
      || pendingInputControl
    ) {
      return false
    }

    const eventId = `voice-${controlName}-${++nextControlId}`
    pendingInputControl = { ...control, eventId }
    setStatus(control.pendingStatus)
    try {
      dataChannel.send(JSON.stringify({ type: control.requestType, event_id: eventId }))
      return true
    } catch {
      pendingInputControl = null
      setStatus(control.previousStatus, 'input-control')
      return false
    }
  }

  return {
    start,
    mute: () => updateInputAudio('mute'),
    unmute: () => updateInputAudio('unmute'),
    enableAssistantAudio,
    dispose() {
      attemptId += 1
      clearResources()
    },
  }
}
