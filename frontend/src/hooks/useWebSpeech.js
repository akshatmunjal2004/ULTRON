import { useCallback, useEffect, useRef, useState } from 'react';

import { hasWebSpeechRecognition } from '../utils/browser';

/**
 * Browser speech recognition via the Web Speech API (Chrome and Edge only).
 *
 * `continuous = false` so the browser finalises a phrase at each natural pause;
 * we surface that finalised text through onFinal and, while the caller still
 * wants to listen, restart automatically for the next phrase. This is more
 * reliable than continuous mode, which tends to accumulate one endless result.
 *
 * onFinal is kept in a ref so changing the callback never tears down the
 * recognition instance.
 */
export function useWebSpeech(onFinal) {
  const supported = hasWebSpeechRecognition;
  const [listening, setListening] = useState(false);
  const [partial, setPartial] = useState('');
  const [error, setError] = useState(null);

  const recognitionRef = useRef(null);
  const onFinalRef = useRef(onFinal);
  const wantRef = useRef(false); // does the caller still want to be listening?
  const finalRef = useRef('');

  useEffect(() => {
    onFinalRef.current = onFinal;
  }, [onFinal]);

  useEffect(() => {
    if (!supported) {
      setError('Voice input needs Chrome or Edge. Use the record button instead.');
      return undefined;
    }

    const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    const rec = new Recognition();
    rec.continuous = false;
    rec.interimResults = true;
    rec.lang = 'en-US';

    rec.onstart = () => {
      finalRef.current = '';
      setListening(true);
      setError(null);
      setPartial('');
    };

    rec.onresult = (event) => {
      let interim = '';
      finalRef.current = '';
      for (let i = 0; i < event.results.length; i += 1) {
        const segment = event.results[i][0].transcript;
        if (event.results[i].isFinal) finalRef.current += segment;
        else interim += segment;
      }
      setPartial(finalRef.current || interim);
    };

    rec.onerror = (event) => {
      // Silence and manual aborts are normal control flow, not errors.
      if (event.error === 'no-speech' || event.error === 'aborted') return;
      if (event.error === 'not-allowed' || event.error === 'service-not-allowed') {
        wantRef.current = false;
        setError('Microphone access was blocked. Allow it for this site and reload.');
      } else if (event.error === 'network') {
        setError('The speech service is unreachable. Check your connection.');
      } else {
        setError(`Voice error: ${event.error}`);
      }
    };

    rec.onend = () => {
      setListening(false);
      const text = finalRef.current.trim();
      finalRef.current = '';
      setPartial('');
      if (text) {
        onFinalRef.current?.(text);
      } else if (wantRef.current) {
        // Nothing captured (a pause). Keep the mic open for the next phrase.
        safeStart(rec);
      }
    };

    recognitionRef.current = rec;
    return () => {
      wantRef.current = false;
      try {
        rec.abort();
      } catch {
        /* already stopped */
      }
    };
  }, [supported]);

  const safeStart = (rec) => {
    try {
      rec.start();
    } catch {
      // start() throws if called while already starting; retry shortly.
      setTimeout(() => {
        try {
          rec.start();
        } catch {
          /* give up quietly */
        }
      }, 200);
    }
  };

  const start = useCallback(() => {
    wantRef.current = true;
    const rec = recognitionRef.current;
    if (rec) safeStart(rec);
  }, []);

  const stop = useCallback(() => {
    wantRef.current = false;
    try {
      recognitionRef.current?.abort();
    } catch {
      /* already stopped */
    }
    setListening(false);
    setPartial('');
  }, []);

  return { supported, listening, partial, error, start, stop };
}
