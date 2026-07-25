// Typed wrappers over the REST API. Components import these, never fetch()
// directly, so the URL scheme lives in exactly one place.

import { getApiKey, request, stream } from './client';

export const health = {
  status: () => request('/health', { timeout: 5000 }),
  ready: () => request('/ready', { timeout: 5000 }),
};

export const chat = {
  send: (message, { conversationId = null, history = null } = {}) =>
    request('/chat', {
      method: 'POST',
      timeout: 45000,
      body: { message, conversation_id: conversationId, history },
    }),

  // onEvent(name, data): 'start' | 'status' | 'tool' | 'token' | 'done' | 'error'
  stream: (message, { conversationId = null, onEvent, signal } = {}) =>
    stream(
      '/chat/stream',
      { message, conversation_id: conversationId, history: null },
      onEvent,
      { signal },
    ),
};

export const conversations = {
  list: ({ limit = 20, offset = 0 } = {}) =>
    request(`/conversations?limit=${limit}&offset=${offset}`),
  get: (id) => request(`/conversations/${encodeURIComponent(id)}`),
  remove: (id) => request(`/conversations/${encodeURIComponent(id)}`, { method: 'DELETE' }),
};

export const memory = {
  list: ({ limit = 50, offset = 0, q = '' } = {}) => {
    const params = new URLSearchParams({ limit: String(limit), offset: String(offset) });
    if (q) params.set('q', q);
    return request(`/memory?${params.toString()}`);
  },
  upsert: (key, value) => request('/memory', { method: 'PUT', body: { key, value } }),
  remove: (key) => request(`/memory/${encodeURIComponent(key)}`, { method: 'DELETE' }),
};

export const tools = {
  list: () => request('/tools'),
  execute: (tool, args = {}) =>
    request('/tools/execute', { method: 'POST', body: { tool, args }, timeout: 30000 }),
};

export const voice = {
  capabilities: () => request('/voice/capabilities', { timeout: 5000 }),
  transcribe: async (wavBlob) => {
    // Multipart, so this one bypasses the JSON client. The API-key header is
    // still applied here to match the rest of the surface.
    const form = new FormData();
    form.append('file', wavBlob, 'recording.wav');
    const key = getApiKey();
    const res = await fetch(
      `${import.meta.env.VITE_API_URL || ''}/api/v1/voice/transcribe`,
      { method: 'POST', body: form, headers: key ? { 'X-API-Key': key } : {} },
    );
    if (!res.ok) {
      let msg = 'Transcription failed.';
      try {
        msg = (await res.json())?.error?.message || msg;
      } catch {
        /* ignore */
      }
      throw new Error(msg);
    }
    return res.json();
  },
};
