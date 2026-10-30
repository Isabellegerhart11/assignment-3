const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000/api'

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
    ...options,
  })

  if (response.status === 204) return null
  const body = await response.json().catch(() => ({}))
  if (!response.ok) {
    throw new Error(body.detail || 'Something did not work. You can still continue.')
  }
  return body
}

export const api = {
  getProfile: () => request('/profile'),
  updateProfile: (profile) => request('/profile', { method: 'PUT', body: JSON.stringify(profile) }),
  clearProfile: () => request('/profile', { method: 'DELETE' }),
  getVoiceConfiguration: () => request('/voice/config'),
  createVoiceSession: (sdp) => request('/voice/sessions', {
    method: 'POST',
    body: JSON.stringify({ sdp }),
  }),
  listMoods: (month) => request(`/moods?month=${encodeURIComponent(month)}`),
  saveMood: (day, mood) => request(`/moods/${encodeURIComponent(day)}`, {
    method: 'PUT',
    body: JSON.stringify({ mood }),
  }),
  removeMood: (day) => request(`/moods/${encodeURIComponent(day)}`, { method: 'DELETE' }),
  clearMoods: () => request('/moods', { method: 'DELETE' }),
  createSession: (skill) => request('/sessions', { method: 'POST', body: JSON.stringify({ skill }) }),
  createConversation: () => request('/conversations', { method: 'POST', body: JSON.stringify({}) }),
  listConversations: () => request('/conversations'),
  getConversation: (id) => request(`/conversations/${id}`),
  sendConversationMessage: (id, content, clientMessageId, reflection = null) =>
    request(`/conversations/${id}/messages`, {
      method: 'POST',
      body: JSON.stringify({
        content,
        client_message_id: clientMessageId,
        ...(reflection ? { reflection } : {}),
      }),
    }),
  clearConversations: () => request('/conversations', { method: 'DELETE' }),
  submitCheckin: (id, text) =>
    request(`/sessions/${id}/checkin`, { method: 'POST', body: JSON.stringify({ text }) }),
  finishSession: (id, status, secondsCompleted) =>
    request(`/sessions/${id}/finish`, {
      method: 'POST',
      body: JSON.stringify({ status, seconds_completed: secondsCompleted }),
    }),
  listSessions: () => request('/sessions'),
  getSession: (id) => request(`/sessions/${id}`),
  clearSessions: () => request('/sessions', { method: 'DELETE' }),
}
