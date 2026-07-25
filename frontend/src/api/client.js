// Base HTTP client.
//
// The backend speaks one error shape for every failure:
//   { error: { code, message, details }, request_id }
// so this is the single place that unwraps it. Everything above works with a
// normalised ApiError and never has to inspect envelopes again.

const API_URL = import.meta.env.VITE_API_URL || '';
const BASE = `${API_URL}/api/v1`;

const API_KEY_STORAGE = 'ultron.apiKey';

export function getApiKey() {
  try {
    return localStorage.getItem(API_KEY_STORAGE) || '';
  } catch {
    return '';
  }
}

export function setApiKey(key) {
  try {
    if (key) localStorage.setItem(API_KEY_STORAGE, key);
    else localStorage.removeItem(API_KEY_STORAGE);
  } catch {
    /* private mode — the key just won't persist */
  }
}

export class ApiError extends Error {
  constructor(message, { code = 'error', status = 0, details = null } = {}) {
    super(message);
    this.name = 'ApiError';
    this.code = code;
    this.status = status;
    this.details = details;
  }
}

function authHeaders() {
  const key = getApiKey();
  return key ? { 'X-API-Key': key } : {};
}

async function parseError(res) {
  let body = null;
  try {
    body = await res.json();
  } catch {
    /* non-JSON error page */
  }
  const err = body?.error;
  if (err?.message) {
    return new ApiError(err.message, { code: err.code, status: res.status, details: err.details });
  }
  const fallback = {
    401: 'Authentication is required. Add your API key in settings.',
    403: 'That action is not permitted.',
    404: 'Not found.',
    429: 'Too many requests. Slow down for a moment.',
    502: 'The AI provider could not be reached.',
    503: 'The service is not ready yet.',
  };
  return new ApiError(fallback[res.status] || `Request failed (${res.status}).`, {
    status: res.status,
  });
}

/**
 * JSON request with a timeout. Throws ApiError on any non-2xx or network fault.
 */
export async function request(path, { method = 'GET', body, timeout = 15000, signal } = {}) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(new DOMException('timeout', 'AbortError')), timeout);
  if (signal) signal.addEventListener('abort', () => controller.abort(), { once: true });

  try {
    const res = await fetch(`${BASE}${path}`, {
      method,
      headers: {
        ...(body !== undefined ? { 'Content-Type': 'application/json' } : {}),
        ...authHeaders(),
      },
      body: body !== undefined ? JSON.stringify(body) : undefined,
      signal: controller.signal,
    });
    if (!res.ok) throw await parseError(res);
    if (res.status === 204) return null;
    return await res.json();
  } catch (err) {
    if (err instanceof ApiError) throw err;
    if (err.name === 'AbortError') {
      throw new ApiError('The request timed out. Check the backend is running.', {
        code: 'timeout',
      });
    }
    throw new ApiError('Cannot reach the backend. Start it with: python run.py', {
      code: 'network',
    });
  } finally {
    clearTimeout(timer);
  }
}

/**
 * POST that consumes a text/event-stream response, calling onEvent(name, data)
 * for each frame. Returns when the stream closes.
 *
 * We use fetch + a stream reader rather than EventSource because EventSource is
 * GET-only and cannot send a request body or the API-key header.
 */
export async function stream(path, payload, onEvent, { signal } = {}) {
  const res = await fetch(`${BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Accept: 'text/event-stream', ...authHeaders() },
    body: JSON.stringify(payload),
    signal,
  });
  if (!res.ok) throw await parseError(res);
  if (!res.body) throw new ApiError('Streaming is not supported by this browser.');

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  const dispatch = (block) => {
    let event = 'message';
    const dataLines = [];
    for (const line of block.split('\n')) {
      if (line.startsWith('event:')) event = line.slice(6).trim();
      else if (line.startsWith('data:')) dataLines.push(line.slice(5).trim());
    }
    if (!dataLines.length) return;
    let data = dataLines.join('\n');
    try {
      data = JSON.parse(data);
    } catch {
      /* leave as string */
    }
    onEvent(event, data);
  };

  try {
    for (;;) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      // SSE frames are separated by a blank line.
      let sep;
      while ((sep = buffer.indexOf('\n\n')) !== -1) {
        dispatch(buffer.slice(0, sep));
        buffer = buffer.slice(sep + 2);
      }
    }
    if (buffer.trim()) dispatch(buffer);
  } finally {
    reader.releaseLock();
  }
}
