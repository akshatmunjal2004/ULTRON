import { useCallback, useEffect, useState } from 'react';
import { Bot, MessagesSquare, Trash2, User } from 'lucide-react';

import { conversations as convApi } from '../api/endpoints';
import { useToast } from '../context/ToastContext';
import { relativeTime } from '../utils/format';

export default function ConversationsPage() {
  const toast = useToast();
  const [list, setList] = useState([]);
  const [selected, setSelected] = useState(null);
  const [detail, setDetail] = useState(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const res = await convApi.list({ limit: 50 });
      setList(res.items);
      if (res.items.length && !selected) setSelected(res.items[0].id);
    } catch (err) {
      toast.error(err.message);
    } finally {
      setLoading(false);
    }
  }, [toast, selected]);

  useEffect(() => {
    load();
    // Only on mount; selecting a row is handled separately.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (!selected) {
      setDetail(null);
      return;
    }
    let alive = true;
    convApi
      .get(selected)
      .then((d) => alive && setDetail(d))
      .catch((err) => alive && toast.error(err.message));
    return () => {
      alive = false;
    };
  }, [selected, toast]);

  const remove = async (id, event) => {
    event.stopPropagation();
    try {
      await convApi.remove(id);
      toast.success('Conversation deleted.');
      setList((current) => current.filter((c) => c.id !== id));
      if (selected === id) setSelected(null);
    } catch (err) {
      toast.error(err.message);
    }
  };

  return (
    <div className="mx-auto w-full max-w-6xl px-4 py-6 flex-1 grid gap-6 md:grid-cols-[320px_1fr] min-h-0">
      <aside className="glass-panel flex flex-col overflow-hidden min-h-0">
        <header className="px-4 py-3 border-b border-ultron-border text-xs font-semibold uppercase tracking-widest text-ultron-primary flex items-center gap-2">
          <MessagesSquare className="w-4 h-4" aria-hidden /> Conversations
        </header>
        <div className="flex-1 overflow-y-auto">
          {loading && <p className="p-4 text-sm text-ultron-muted">Loading…</p>}
          {!loading && list.length === 0 && (
            <p className="p-4 text-sm text-ultron-muted">
              No conversations yet. Talk to the assistant and they will appear here.
            </p>
          )}
          <ul>
            {list.map((conv) => (
              <li key={conv.id}>
                <button
                  onClick={() => setSelected(conv.id)}
                  className={`w-full text-left px-4 py-3 border-b border-ultron-border/50 flex items-start justify-between gap-2 group transition-colors ${
                    selected === conv.id ? 'bg-ultron-primary/10' : 'hover:bg-white/5'
                  }`}
                >
                  <span className="min-w-0">
                    <span className="block truncate text-sm text-ultron-text">{conv.title}</span>
                    <span className="block text-xs text-ultron-muted mt-0.5">
                      {conv.message_count} messages · {relativeTime(conv.updated_at)}
                    </span>
                  </span>
                  <span
                    onClick={(e) => remove(conv.id, e)}
                    className="opacity-0 group-hover:opacity-100 text-ultron-muted hover:text-ultron-danger transition-opacity"
                    role="button"
                    aria-label={`Delete ${conv.title}`}
                    tabIndex={0}
                    onKeyDown={(e) => e.key === 'Enter' && remove(conv.id, e)}
                  >
                    <Trash2 className="w-4 h-4" aria-hidden />
                  </span>
                </button>
              </li>
            ))}
          </ul>
        </div>
      </aside>

      <section className="glass-panel flex flex-col overflow-hidden min-h-0">
        {!detail ? (
          <p className="flex-1 grid place-items-center text-ultron-muted text-sm">
            Select a conversation to read it.
          </p>
        ) : (
          <>
            <header className="px-5 py-3 border-b border-ultron-border">
              <h2 className="font-semibold truncate">{detail.title}</h2>
              <p className="text-xs text-ultron-muted">{relativeTime(detail.updated_at)}</p>
            </header>
            <div className="flex-1 overflow-y-auto p-5 flex flex-col gap-4">
              {detail.messages.map((msg) => (
                <div
                  key={msg.id}
                  className={`flex gap-3 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
                >
                  {msg.role !== 'user' && (
                    <Bot className="w-5 h-5 text-ultron-accent shrink-0 mt-1" aria-hidden />
                  )}
                  <div
                    className={`max-w-[75%] rounded-2xl px-4 py-2.5 text-sm leading-relaxed whitespace-pre-wrap break-words ${
                      msg.role === 'user'
                        ? 'bg-ultron-primary text-white rounded-br-sm'
                        : 'bg-ultron-raised border border-ultron-border rounded-bl-sm'
                    }`}
                  >
                    {msg.content}
                  </div>
                  {msg.role === 'user' && (
                    <User className="w-5 h-5 text-ultron-muted shrink-0 mt-1" aria-hidden />
                  )}
                </div>
              ))}
            </div>
          </>
        )}
      </section>
    </div>
  );
}
