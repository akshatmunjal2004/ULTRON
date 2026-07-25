import { useCallback, useEffect, useState } from 'react';
import { Brain, Plus, Search, Trash2 } from 'lucide-react';

import { memory as memoryApi } from '../api/endpoints';
import { ApiError } from '../api/client';
import { useToast } from '../context/ToastContext';
import { relativeTime } from '../utils/format';

export default function MemoryPage() {
  const toast = useToast();
  const [items, setItems] = useState([]);
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(true);
  const [newKey, setNewKey] = useState('');
  const [newValue, setNewValue] = useState('');
  const [saving, setSaving] = useState(false);

  const load = useCallback(
    async (q = '') => {
      setLoading(true);
      try {
        const res = await memoryApi.list({ q, limit: 100 });
        setItems(res.items);
      } catch (err) {
        toast.error(err.message);
      } finally {
        setLoading(false);
      }
    },
    [toast],
  );

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Debounce the search so we don't fire a request per keystroke.
  useEffect(() => {
    const id = setTimeout(() => load(query.trim()), 300);
    return () => clearTimeout(id);
  }, [query, load]);

  const add = async () => {
    const key = newKey.trim();
    const value = newValue.trim();
    if (!key || !value) {
      toast.info('Both a key and a value are needed.');
      return;
    }
    setSaving(true);
    try {
      await memoryApi.upsert(key, value);
      toast.success(`Saved "${key}".`);
      setNewKey('');
      setNewValue('');
      load(query.trim());
    } catch (err) {
      // A 401 here means the backend has auth on but no key is set locally.
      if (err instanceof ApiError && err.status === 401) {
        toast.error('Saving needs an API key. Add it in settings (top right).');
      } else {
        toast.error(err.message);
      }
    } finally {
      setSaving(false);
    }
  };

  const remove = async (key) => {
    try {
      await memoryApi.remove(key);
      setItems((current) => current.filter((i) => i.key !== key));
      toast.success(`Removed "${key}".`);
    } catch (err) {
      toast.error(err.message);
    }
  };

  return (
    <div className="mx-auto w-full max-w-3xl px-4 py-6 flex-1 flex flex-col gap-5 min-h-0">
      <header>
        <h1 className="flex items-center gap-2 text-xl font-semibold">
          <Brain className="w-6 h-6 text-ultron-accent" aria-hidden /> Memory
        </h1>
        <p className="text-sm text-ultron-muted mt-1">
          Facts ULTRON remembers across conversations. The assistant reads and writes these too.
        </p>
      </header>

      {/* Add */}
      <div className="glass-panel p-4 grid gap-2 sm:grid-cols-[1fr_2fr_auto]">
        <label htmlFor="mem-key" className="sr-only">
          Key
        </label>
        <input
          id="mem-key"
          className="input"
          placeholder="key (e.g. flight date)"
          value={newKey}
          onChange={(e) => setNewKey(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && add()}
        />
        <label htmlFor="mem-value" className="sr-only">
          Value
        </label>
        <input
          id="mem-value"
          className="input"
          placeholder="value (e.g. the 12th at 6pm)"
          value={newValue}
          onChange={(e) => setNewValue(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && add()}
        />
        <button className="btn-primary" onClick={add} disabled={saving}>
          <Plus className="w-4 h-4" aria-hidden /> Add
        </button>
      </div>

      {/* Search */}
      <div className="relative">
        <Search
          className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-ultron-muted"
          aria-hidden
        />
        <label htmlFor="mem-search" className="sr-only">
          Search memory
        </label>
        <input
          id="mem-search"
          className="input pl-9"
          placeholder="Search stored facts"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
      </div>

      {/* List */}
      <div className="glass-panel flex-1 overflow-y-auto min-h-0">
        {loading && <p className="p-4 text-sm text-ultron-muted">Loading…</p>}
        {!loading && items.length === 0 && (
          <p className="p-6 text-center text-sm text-ultron-muted">
            {query ? 'No facts match that search.' : 'Nothing stored yet.'}
          </p>
        )}
        <ul>
          {items.map((item) => (
            <li
              key={item.id}
              className="flex items-start justify-between gap-3 px-4 py-3 border-b border-ultron-border/50 last:border-0"
            >
              <div className="min-w-0">
                <p className="text-sm font-medium text-ultron-text break-words">{item.key}</p>
                <p className="text-sm text-ultron-muted break-words">{item.value}</p>
                <p className="text-xs text-ultron-muted/60 mt-0.5">
                  updated {relativeTime(item.updated_at)}
                </p>
              </div>
              <button
                onClick={() => remove(item.key)}
                className="text-ultron-muted hover:text-ultron-danger shrink-0"
                aria-label={`Delete ${item.key}`}
              >
                <Trash2 className="w-4 h-4" aria-hidden />
              </button>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
