import { useCallback, useEffect, useRef, useState } from 'react';

import { hasSpeechSynthesis } from '../utils/browser';
import { speakableText } from '../utils/format';

/**
 * Text-to-speech via the Web Speech API's SpeechSynthesis, available in every
 * modern browser. onDone fires when an utterance finishes or fails, which is
 * how the voice loop knows to resume listening.
 */
export function useSpeechSynthesis(onDone) {
  const supported = hasSpeechSynthesis;
  const [speaking, setSpeaking] = useState(false);
  const voicesRef = useRef([]);
  const onDoneRef = useRef(onDone);

  useEffect(() => {
    onDoneRef.current = onDone;
  }, [onDone]);

  useEffect(() => {
    if (!supported) return undefined;
    const load = () => {
      voicesRef.current = window.speechSynthesis.getVoices();
    };
    load();
    window.speechSynthesis.onvoiceschanged = load;
    return () => {
      window.speechSynthesis.onvoiceschanged = null;
      window.speechSynthesis.cancel();
    };
  }, [supported]);

  const pickVoice = () => {
    const voices = voicesRef.current;
    if (!voices.length) return null;
    // A deep, deliberate voice suits the character; fall back sensibly.
    const preferred = ['Microsoft David', 'Google UK English Male', 'Daniel'];
    for (const name of preferred) {
      const match = voices.find((v) => v.name.includes(name));
      if (match) return match;
    }
    return voices.find((v) => v.lang?.startsWith('en')) || voices[0];
  };

  const speak = useCallback(
    (text) => {
      if (!supported) {
        onDoneRef.current?.();
        return;
      }
      const clean = speakableText(text);
      if (!clean) {
        onDoneRef.current?.();
        return;
      }
      window.speechSynthesis.cancel();
      const utter = new SpeechSynthesisUtterance(clean);
      const voice = pickVoice();
      if (voice) utter.voice = voice;
      utter.rate = 1.05;
      utter.pitch = 0.9;
      utter.onstart = () => setSpeaking(true);
      utter.onend = () => {
        setSpeaking(false);
        onDoneRef.current?.();
      };
      utter.onerror = () => {
        setSpeaking(false);
        onDoneRef.current?.();
      };
      window.speechSynthesis.speak(utter);
    },
    [supported],
  );

  const stop = useCallback(() => {
    if (supported) window.speechSynthesis.cancel();
    setSpeaking(false);
  }, [supported]);

  return { supported, speaking, speak, stop };
}
