import { useEffect, useState } from 'react';
import { KeyRound, X } from 'lucide-react';

import { getApiKey, setApiKey } from '../api/client';
import { useToast } from '../context/ToastContext';

// The backend only requires a key when API_KEY is configured (production, or
// whenever code execution is switched on). This modal lets the user paste it
// once; it is stored in localStorage and sent as X-API-Key thereafter.
export default function SettingsModal({ open, onClose }) {
  const [value, setValue] = useState('');
  const toast = useToast();

  useEffect(() => {
    if (open) setValue(getApiKey());
  }, [open]);

  useEffect(() => {
    if (!open) return undefined;
    const onKey = (e) => e.key === 'Escape' && onClose();
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [open, onClose]);

  if (!open) return null;

  const save = () => {
    setApiKey(value.trim());
    toast.success(value.trim() ? 'API key saved.' : 'API key cleared.');
    onClose();
  };

  return (
    <div
      className="fixed inset-0 z-[90] flex items-center justify-center bg-black/70 backdrop-blur-sm p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="settings-title"
      onClick={onClose}
    >
      <div className="glass-panel w-full max-w-md p-6" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between mb-4">
          <h2 id="settings-title" className="flex items-center gap-2 text-lg font-semibold">
            <KeyRound className="w-5 h-5 text-ultron-accent" aria-hidden /> API key
          </h2>
          <button onClick={onClose} className="text-ultron-muted hover:text-ultron-text" aria-label="Close">
            <X className="w-5 h-5" aria-hidden />
          </button>
        </div>

        <p className="text-sm text-ultron-muted mb-3">
          Needed only when the backend has authentication turned on. Leave it blank for local
          development.
        </p>

        <label htmlFor="api-key" className="sr-only">
          API key
        </label>
        <input
          id="api-key"
          type="password"
          className="input font-mono"
          placeholder="paste your API key"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && save()}
          autoFocus
        />

        <div className="mt-5 flex justify-end gap-3">
          <button className="btn-ghost" onClick={onClose}>
            Cancel
          </button>
          <button className="btn-primary" onClick={save}>
            Save
          </button>
        </div>
      </div>
    </div>
  );
}
