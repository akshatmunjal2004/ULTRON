// Capability checks, evaluated once at module load.

export const hasWebSpeechRecognition =
  typeof window !== 'undefined' &&
  Boolean(window.SpeechRecognition || window.webkitSpeechRecognition);

export const hasSpeechSynthesis =
  typeof window !== 'undefined' && 'speechSynthesis' in window;

export const hasMediaRecorder =
  typeof window !== 'undefined' &&
  typeof navigator !== 'undefined' &&
  Boolean(navigator.mediaDevices?.getUserMedia) &&
  typeof window.MediaRecorder !== 'undefined';

export const prefersReducedMotion =
  typeof window !== 'undefined' &&
  window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;
