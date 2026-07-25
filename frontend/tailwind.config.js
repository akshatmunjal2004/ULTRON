/** @type {import('tailwindcss').Config} */

// One token system, defined once. The previous config referenced classes that
// didn't exist here (ultron-border, ultron-accent2), so half the components
// rendered unstyled. Every colour a component uses is declared below.
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        ultron: {
          bg: '#05060f',
          surface: '#0d0f22',
          raised: '#14162e',
          border: 'rgba(148, 163, 255, 0.14)',
          primary: '#6366f1',
          bright: '#818cf8',
          accent: '#22d3ee',
          danger: '#f43f5e',
          success: '#34d399',
          warning: '#fbbf24',
          text: '#e7e9f5',
          muted: '#8a8fb5',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'Segoe UI', 'Roboto', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'ui-monospace', 'SFMono-Regular', 'monospace'],
      },
      boxShadow: {
        panel: '0 8px 32px rgba(0, 0, 0, 0.45), inset 0 0 20px rgba(99, 102, 241, 0.04)',
        glow: '0 0 40px rgba(99, 102, 241, 0.35)',
      },
      keyframes: {
        'pulse-bar': {
          '0%, 100%': { transform: 'scaleY(0.4)', opacity: '0.5' },
          '50%': { transform: 'scaleY(1)', opacity: '1' },
        },
        blink: { '0%, 100%': { opacity: '1' }, '50%': { opacity: '0' } },
        'fade-in': {
          from: { opacity: '0', transform: 'translateY(4px)' },
          to: { opacity: '1', transform: 'translateY(0)' },
        },
      },
      animation: {
        'pulse-bar': 'pulse-bar 1s ease-in-out infinite',
        blink: 'blink 1s step-end infinite',
        'fade-in': 'fade-in 0.25s ease-out',
      },
    },
  },
  plugins: [],
};
