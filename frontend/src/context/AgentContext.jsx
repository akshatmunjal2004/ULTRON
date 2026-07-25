import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from 'react';

import * as api from '../api/endpoints';

// Holds everything shared across pages: whether the backend is reachable, which
// model is answering, the active conversation, and the primitives for sending a
// message (buffered or streamed). Voice orchestration lives in the Assistant
// page instead, because it is specific to that screen.

const AgentContext = createContext(null);

const POLL_MS = 15000;

export function AgentProvider({ children }) {
  const [connection, setConnection] = useState('checking'); // checking | online | offline
  const [model, setModel] = useState('');
  const [capabilities, setCapabilities] = useState(null);
  const [conversationId, setConversationId] = useState(null);
  const [messages, setMessages] = useState([]);

  const addMessage = useCallback((msg) => {
    setMessages((current) => [...current, { id: crypto.randomUUID(), ...msg }]);
  }, []);

  const updateLastAssistant = useCallback((patch) => {
    setMessages((current) => {
      const next = [...current];
      for (let i = next.length - 1; i >= 0; i -= 1) {
        if (next[i].role === 'assistant') {
          next[i] = { ...next[i], ...patch };
          break;
        }
      }
      return next;
    });
  }, []);

  const reset = useCallback(() => {
    setConversationId(null);
    setMessages([]);
  }, []);

  const loadConversation = useCallback(async (id) => {
    const detail = await api.conversations.get(id);
    setConversationId(detail.id);
    setMessages(
      detail.messages.map((m) => ({
        id: `srv-${m.id}`,
        role: m.role,
        content: m.content,
      })),
    );
  }, []);

  // --- health polling ---------------------------------------------------
  useEffect(() => {
    let alive = true;
    const check = async () => {
      try {
        const info = await api.health.status();
        if (!alive) return;
        setConnection('online');
        setModel(info.model || '');
      } catch {
        if (alive) setConnection('offline');
      }
    };
    check();
    const id = setInterval(check, POLL_MS);
    return () => {
      alive = false;
      clearInterval(id);
    };
  }, []);

  useEffect(() => {
    let alive = true;
    api.voice
      .capabilities()
      .then((caps) => alive && setCapabilities(caps))
      .catch(() => {});
    return () => {
      alive = false;
    };
  }, []);

  // --- sending ----------------------------------------------------------

  /** Buffered send: one request, one reply. Returns the assistant text. */
  const send = useCallback(
    async (text) => {
      addMessage({ role: 'user', content: text });
      const res = await api.chat.send(text, { conversationId });
      setConversationId(res.conversation_id);
      addMessage({ role: 'assistant', content: res.reply, tools: res.tools_used });
      return res;
    },
    [conversationId, addMessage],
  );

  /**
   * Streamed send: tokens arrive incrementally via onToken so speech can begin
   * before generation finishes. Resolves with the final reply.
   */
  const sendStreaming = useCallback(
    async ({ text, onToken, onTool, signal } = {}) => {
      addMessage({ role: 'user', content: text });
      addMessage({ role: 'assistant', content: '', tools: [], streaming: true });

      let reply = '';
      const tools = new Set();
      let resolvedId = conversationId;

      await api.chat.stream(text, {
        conversationId,
        signal,
        onEvent: (event, data) => {
          if (event === 'start' && data?.conversation_id) {
            resolvedId = data.conversation_id;
            setConversationId(resolvedId);
          } else if (event === 'tool' && data?.name) {
            tools.add(data.name);
            onTool?.(data.name);
            updateLastAssistant({ tools: [...tools] });
          } else if (event === 'token' && data?.text) {
            reply += data.text;
            onToken?.(data.text, reply);
            updateLastAssistant({ content: reply });
          } else if (event === 'done') {
            reply = data?.reply ?? reply;
            updateLastAssistant({ content: reply, streaming: false, tools: [...tools] });
          } else if (event === 'error') {
            throw new Error(data?.message || 'The stream failed.');
          }
        },
      });

      updateLastAssistant({ streaming: false });
      return { reply, conversationId: resolvedId, tools: [...tools] };
    },
    [conversationId, addMessage, updateLastAssistant],
  );

  const value = useMemo(
    () => ({
      connection,
      model,
      capabilities,
      conversationId,
      messages,
      send,
      sendStreaming,
      addMessage,
      reset,
      loadConversation,
    }),
    [
      connection,
      model,
      capabilities,
      conversationId,
      messages,
      send,
      sendStreaming,
      addMessage,
      reset,
      loadConversation,
    ],
  );

  return <AgentContext.Provider value={value}>{children}</AgentContext.Provider>;
}

export function useAgent() {
  const ctx = useContext(AgentContext);
  if (!ctx) throw new Error('useAgent must be used inside an AgentProvider');
  return ctx;
}
