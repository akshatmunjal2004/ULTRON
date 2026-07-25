import { useMemo } from 'react';
import { motion } from 'framer-motion';

import { prefersReducedMotion } from '../utils/browser';

// Ambient atmosphere: a receding grid and a few drifting motes. The particle
// count is modest (heavy particle fields are an AI-design tell and cost frames),
// and everything holds still under reduced-motion.
export default function BackgroundEffects() {
  const reduced = prefersReducedMotion;
  const particles = useMemo(
    () =>
      Array.from({ length: 14 }, (_, i) => ({
        id: i,
        size: Math.random() * 3 + 1,
        x: Math.random() * 100,
        duration: Math.random() * 16 + 12,
        delay: Math.random() * 8,
      })),
    [],
  );

  return (
    <div className="fixed inset-0 -z-10 overflow-hidden bg-ultron-bg" aria-hidden>
      <div
        className="absolute inset-[-40%] opacity-20"
        style={{
          backgroundImage:
            'linear-gradient(rgba(99,102,241,0.35) 1px, transparent 1px),' +
            'linear-gradient(90deg, rgba(99,102,241,0.35) 1px, transparent 1px)',
          backgroundSize: '44px 44px',
          transform: 'perspective(600px) rotateX(60deg) translateY(-120px)',
        }}
      />
      <div className="absolute inset-0 bg-gradient-to-t from-ultron-bg via-ultron-bg/70 to-transparent" />

      <div className="absolute top-0 left-1/4 w-[480px] h-[480px] rounded-full blur-[150px] bg-ultron-primary/10" />
      <div className="absolute bottom-0 right-1/4 w-[520px] h-[520px] rounded-full blur-[150px] bg-ultron-accent/10" />

      {!reduced &&
        particles.map((p) => (
          <motion.span
            key={p.id}
            className="absolute rounded-full bg-ultron-accent/40 blur-[1px]"
            style={{ width: p.size, height: p.size, left: `${p.x}%`, bottom: '-5%' }}
            animate={{ y: ['0%', '-1100%'], opacity: [0, 0.7, 0] }}
            transition={{ duration: p.duration, delay: p.delay, repeat: Infinity, ease: 'linear' }}
          />
        ))}
    </div>
  );
}
