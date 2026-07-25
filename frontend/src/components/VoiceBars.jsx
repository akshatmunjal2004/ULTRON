// Purely decorative equalizer, driven by the `active` prop. It never touches
// the microphone, so it cannot desync from real audio state.
export default function VoiceBars({ active }) {
  const bars = [0.3, 0.6, 0.9, 0.5, 0.75, 0.4, 0.65];
  return (
    <div className="flex items-end gap-[3px] h-5" aria-hidden>
      {bars.map((h, i) => (
        <span
          key={i}
          className="w-[3px] rounded-full bg-ultron-accent origin-bottom"
          style={{
            height: '100%',
            transform: active ? undefined : `scaleY(${h * 0.35})`,
            opacity: active ? 1 : 0.4,
            animation: active ? 'pulse-bar 0.9s ease-in-out infinite' : 'none',
            animationDelay: `${i * 0.08}s`,
          }}
        />
      ))}
    </div>
  );
}
