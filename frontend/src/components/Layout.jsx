import { useState } from 'react';
import { NavLink } from 'react-router-dom';
import { Brain, MessagesSquare, Mic, Settings } from 'lucide-react';

import { useAgent } from '../context/AgentContext';
import BackgroundEffects from './BackgroundEffects';
import SettingsModal from './SettingsModal';

const CONNECTION = {
  checking: { color: 'bg-ultron-warning', label: 'Connecting' },
  online: { color: 'bg-ultron-success', label: 'Online' },
  offline: { color: 'bg-ultron-danger', label: 'Offline' },
};

const LINKS = [
  { to: '/', label: 'Assistant', icon: Mic, end: true },
  { to: '/conversations', label: 'History', icon: MessagesSquare },
  { to: '/memory', label: 'Memory', icon: Brain },
];

export default function Layout({ children }) {
  const { connection, model } = useAgent();
  const [settingsOpen, setSettingsOpen] = useState(false);
  const status = CONNECTION[connection];

  return (
    <div className="min-h-screen flex flex-col">
      <BackgroundEffects />

      <header className="sticky top-0 z-40 border-b border-ultron-border bg-ultron-bg/70 backdrop-blur-md">
        <div className="mx-auto max-w-6xl px-4 h-14 flex items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-ultron-primary to-ultron-accent grid place-items-center font-bold text-black">
              U
            </div>
            <span className="font-semibold tracking-[0.2em] text-sm hidden sm:block">ULTRON</span>
          </div>

          <nav className="flex items-center gap-1" aria-label="Primary">
            {LINKS.map(({ to, label, icon: Icon, end }) => (
              <NavLink
                key={to}
                to={to}
                end={end}
                className={({ isActive }) =>
                  `flex items-center gap-2 rounded-lg px-3 py-1.5 text-sm transition-colors ${
                    isActive
                      ? 'bg-ultron-primary/15 text-ultron-bright'
                      : 'text-ultron-muted hover:text-ultron-text'
                  }`
                }
              >
                <Icon className="w-4 h-4" aria-hidden />
                <span className="hidden sm:block">{label}</span>
              </NavLink>
            ))}
          </nav>

          <div className="flex items-center gap-3">
            <div
              className="flex items-center gap-2 text-xs text-ultron-muted"
              title={model ? `Model: ${model}` : status.label}
            >
              <span
                className={`w-2 h-2 rounded-full ${status.color} ${
                  connection === 'online' ? 'animate-pulse' : ''
                }`}
                aria-hidden
              />
              <span className="hidden md:block">{status.label}</span>
            </div>
            <button
              onClick={() => setSettingsOpen(true)}
              className="text-ultron-muted hover:text-ultron-text"
              aria-label="Settings"
            >
              <Settings className="w-5 h-5" aria-hidden />
            </button>
          </div>
        </div>
      </header>

      <main className="flex-1 flex flex-col">{children}</main>

      <SettingsModal open={settingsOpen} onClose={() => setSettingsOpen(false)} />
    </div>
  );
}
