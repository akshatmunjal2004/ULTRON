import { motion } from 'framer-motion';

import { prefersReducedMotion } from '../utils/browser';

// The signature element of the app: a reactive core whose colour and motion
// encode the agent's state. Keep the boldness here and everything around it
// quiet. When the user has asked for reduced motion, the orb still changes
// colour and label but stops pulsing and rotating.

const STATE_COLOR = {
  idle: '#6366f1',
  listening: '#22d3ee',
  thinking: '#a855f7',
  speaking: '#818cf8',
  error: '#f43f5e',
};

const STATE_LABEL = {
  idle: 'Standby',
  listening: 'Listening',
  thinking: 'Thinking',
  speaking: 'Responding',
  error: 'Error',
};

function motionForState(state, reduced) {
  if (reduced) return { scale: 1 };
  switch (state) {
    case 'listening':
      return { scale: [1, 1.05, 1], transition: { duration: 2, repeat: Infinity } };
    case 'thinking':
      return { rotate: 360, transition: { duration: 3, repeat: Infinity, ease: 'linear' } };
    case 'speaking':
      return {
        scale: [1, 1.08, 1.02, 1.1, 1],
        transition: { duration: 0.7, repeat: Infinity, ease: 'easeInOut' },
      };
    case 'error':
      return { x: [-6, 6, -6, 6, 0], transition: { duration: 0.4 } };
    default:
      return { scale: [1, 1.02, 1], transition: { duration: 4, repeat: Infinity } };
  }
}

export default function UltronOrb({ state = 'idle', size = 300 }) {
  const reduced = prefersReducedMotion;
  const color = STATE_COLOR[state] || STATE_COLOR.idle;

  return (
    <div
      className="relative flex items-center justify-center"
      style={{ width: size, height: size }}
      role="status"
      aria-live="polite"
      aria-label={`Assistant status: ${STATE_LABEL[state] || state}`}
    >
      {/* Ambient halo */}
      <div
        className="absolute rounded-full blur-3xl transition-colors duration-500"
        style={{ width: size * 0.9, height: size * 0.9, backgroundColor: `${color}33` }}
      />

      {/* Outer ring — only spins while thinking */}
      <motion.div
        className="absolute rounded-full border-2 border-dashed"
        style={{ width: size * 0.82, height: size * 0.82, borderColor: `${color}55` }}
        animate={
          reduced || state !== 'thinking'
            ? { rotate: 0 }
            : { rotate: -360, transition: { duration: 6, repeat: Infinity, ease: 'linear' } }
        }
      />

      {/* Core */}
      <motion.div
        className="relative rounded-full border border-white/10 overflow-hidden backdrop-blur-xl"
        style={{
          width: size * 0.58,
          height: size * 0.58,
          background:
            'radial-gradient(circle at 32% 30%, rgba(255,255,255,0.12), rgba(0,0,0,0.55))',
          boxShadow: `0 0 60px ${color}66, inset 0 0 30px ${color}44`,
        }}
        animate={motionForState(state, reduced)}
      >
        <motion.div
          className="absolute inset-1/4 rounded-full blur-lg"
          style={{ backgroundColor: color }}
          animate={reduced ? {} : { opacity: [0.7, 1, 0.7], transition: { duration: 2, repeat: Infinity } }}
        />
        <div className="absolute top-[12%] left-[16%] w-1/4 h-1/5 rounded-full bg-white/25 blur-md rotate-[-40deg]" />
      </motion.div>
    </div>
  );
}
