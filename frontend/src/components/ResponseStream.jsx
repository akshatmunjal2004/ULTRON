import { motion } from 'framer-motion';
import { Cpu } from 'lucide-react';

import VoiceBars from './VoiceBars';

// Right panel: the assistant's latest reply, shown large. When streaming, the
// text is the live-growing string, so a typing cursor is enough — no separate
// per-character animation that could desync from the real tokens.
export default function ResponseStream({ text, speaking, streaming }) {
  return (
    <section className="glass-panel h-full flex flex-col overflow-hidden" aria-label="Latest response">
      <header className="flex items-center justify-between px-4 py-3 border-b border-ultron-border">
        <span className="flex items-center gap-2 text-xs font-semibold uppercase tracking-widest text-ultron-accent">
          <Cpu className="w-4 h-4" aria-hidden /> Response
        </span>
        {speaking && <VoiceBars active />}
      </header>

      <div className="flex-1 overflow-y-auto p-6">
        {!text ? (
          <p className="h-full grid place-items-center text-ultron-muted/60 text-sm italic">
            Awaiting a command…
          </p>
        ) : (
          <motion.p
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className={`text-lg leading-relaxed font-light tracking-wide ${
              streaming ? 'typing-cursor' : ''
            }`}
          >
            {text}
          </motion.p>
        )}
      </div>
    </section>
  );
}
