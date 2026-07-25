import { useEffect, useRef } from 'react';
import { Bot, Terminal, User, Wrench } from 'lucide-react';

// Left panel on the assistant screen: the running transcript of the session.
// Auto-scrolls to the newest line.
export default function TranscriptLog({ messages }) {
  const endRef = useRef(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  return (
    <section className="glass-panel h-full flex flex-col overflow-hidden" aria-label="Transcript">
      <header className="flex items-center gap-2 px-4 py-3 border-b border-ultron-border text-xs font-semibold uppercase tracking-widest text-ultron-primary">
        <Terminal className="w-4 h-4" aria-hidden /> Transcript
      </header>

      <div className="flex-1 overflow-y-auto p-4 flex flex-col gap-3">
        {messages.length === 0 && (
          <p className="text-center text-ultron-muted/70 text-sm mt-10">
            Nothing yet. Start speaking to begin.
          </p>
        )}

        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`animate-fade-in flex items-start gap-3 rounded-lg border p-3 text-sm ${
              msg.role === 'user'
                ? 'bg-white/5 border-ultron-border'
                : 'bg-ultron-accent/5 border-ultron-accent/20'
            }`}
          >
            <span className="mt-0.5 opacity-70 shrink-0">
              {msg.role === 'user' ? (
                <User className="w-4 h-4" aria-hidden />
              ) : (
                <Bot className="w-4 h-4 text-ultron-accent" aria-hidden />
              )}
            </span>
            <div className="flex-1 min-w-0">
              <p className="leading-relaxed break-words whitespace-pre-wrap">
                {msg.content || (msg.streaming ? '…' : '')}
              </p>
              {msg.tools?.length > 0 && (
                <div className="mt-2 flex flex-wrap gap-1.5">
                  {msg.tools.map((tool) => (
                    <span
                      key={tool}
                      className="inline-flex items-center gap-1 rounded-full border border-ultron-primary/25 bg-ultron-primary/10 px-2 py-0.5 text-[11px] text-ultron-bright"
                    >
                      <Wrench className="w-3 h-3" aria-hidden /> {tool}
                    </span>
                  ))}
                </div>
              )}
            </div>
          </div>
        ))}
        <div ref={endRef} />
      </div>
    </section>
  );
}
