import { useCallback, useEffect, useRef, useState } from 'react';

import { hasMediaRecorder } from '../utils/browser';

// The /voice/transcribe endpoint validates 16-bit PCM WAV, so we can't just
// post the browser's native WebM/Opus. We capture raw samples through an
// AudioContext, downsample to 16 kHz mono, and encode a WAV in the browser.
// That keeps the server contract simple and avoids a server-side ffmpeg step.

const TARGET_RATE = 16000;

function downsample(input, inputRate, targetRate) {
  if (targetRate >= inputRate) return input;
  const ratio = inputRate / targetRate;
  const outLength = Math.floor(input.length / ratio);
  const output = new Float32Array(outLength);
  for (let i = 0; i < outLength; i += 1) {
    const start = Math.floor(i * ratio);
    const end = Math.min(Math.floor((i + 1) * ratio), input.length);
    let sum = 0;
    for (let j = start; j < end; j += 1) sum += input[j];
    output[i] = sum / (end - start || 1);
  }
  return output;
}

function encodeWav(samples, sampleRate) {
  const buffer = new ArrayBuffer(44 + samples.length * 2);
  const view = new DataView(buffer);
  const writeString = (offset, str) => {
    for (let i = 0; i < str.length; i += 1) view.setUint8(offset + i, str.charCodeAt(i));
  };

  writeString(0, 'RIFF');
  view.setUint32(4, 36 + samples.length * 2, true);
  writeString(8, 'WAVE');
  writeString(12, 'fmt ');
  view.setUint32(16, 16, true); // PCM chunk size
  view.setUint16(20, 1, true); // PCM format
  view.setUint16(22, 1, true); // mono
  view.setUint32(24, sampleRate, true);
  view.setUint32(28, sampleRate * 2, true); // byte rate
  view.setUint16(32, 2, true); // block align
  view.setUint16(34, 16, true); // bits per sample
  writeString(36, 'data');
  view.setUint32(40, samples.length * 2, true);

  let offset = 44;
  for (let i = 0; i < samples.length; i += 1) {
    const clamped = Math.max(-1, Math.min(1, samples[i]));
    view.setInt16(offset, clamped < 0 ? clamped * 0x8000 : clamped * 0x7fff, true);
    offset += 2;
  }
  return new Blob([view], { type: 'audio/wav' });
}

/**
 * Click-to-record. start() opens the mic; stop() resolves onRecorded(wavBlob).
 * Used as the voice path where the Web Speech API is unavailable.
 */
export function useAudioRecorder(onRecorded) {
  const supported = hasMediaRecorder;
  const [recording, setRecording] = useState(false);
  const [error, setError] = useState(null);

  const ctxRef = useRef(null);
  const streamRef = useRef(null);
  const processorRef = useRef(null);
  const sourceRef = useRef(null);
  const chunksRef = useRef([]);
  const rateRef = useRef(TARGET_RATE);
  const onRecordedRef = useRef(onRecorded);

  useEffect(() => {
    onRecordedRef.current = onRecorded;
  }, [onRecorded]);

  const teardown = useCallback(() => {
    try {
      processorRef.current?.disconnect();
    } catch {
      /* noop */
    }
    try {
      sourceRef.current?.disconnect();
    } catch {
      /* noop */
    }
    try {
      streamRef.current?.getTracks().forEach((t) => t.stop());
    } catch {
      /* noop */
    }
    try {
      ctxRef.current?.close();
    } catch {
      /* noop */
    }
    processorRef.current = null;
    sourceRef.current = null;
    streamRef.current = null;
    ctxRef.current = null;
  }, []);

  useEffect(() => () => teardown(), [teardown]);

  const start = useCallback(async () => {
    if (!supported) {
      setError('Recording is not supported in this browser.');
      return;
    }
    setError(null);
    chunksRef.current = [];
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: { channelCount: 1, echoCancellation: true, noiseSuppression: true },
      });
      streamRef.current = stream;

      const AudioCtx = window.AudioContext || window.webkitAudioContext;
      const ctx = new AudioCtx();
      ctxRef.current = ctx;
      rateRef.current = ctx.sampleRate;

      const source = ctx.createMediaStreamSource(stream);
      sourceRef.current = source;
      const processor = ctx.createScriptProcessor(4096, 1, 1);
      processor.onaudioprocess = (event) => {
        chunksRef.current.push(new Float32Array(event.inputBuffer.getChannelData(0)));
      };
      // A muted sink keeps the processor firing without echoing the mic.
      const sink = ctx.createGain();
      sink.gain.value = 0;
      source.connect(processor);
      processor.connect(sink);
      sink.connect(ctx.destination);
      processorRef.current = processor;

      setRecording(true);
    } catch (err) {
      teardown();
      setError(
        err?.name === 'NotAllowedError'
          ? 'Microphone access was blocked. Allow it and try again.'
          : 'Could not start recording.',
      );
    }
  }, [supported, teardown]);

  const stop = useCallback(() => {
    if (!recording) return;
    setRecording(false);

    const chunks = chunksRef.current;
    const inputRate = rateRef.current;
    teardown();

    const total = chunks.reduce((sum, c) => sum + c.length, 0);
    if (total === 0) return;

    const merged = new Float32Array(total);
    let offset = 0;
    for (const chunk of chunks) {
      merged.set(chunk, offset);
      offset += chunk.length;
    }
    const resampled = downsample(merged, inputRate, TARGET_RATE);
    const wav = encodeWav(resampled, TARGET_RATE);
    onRecordedRef.current?.(wav);
  }, [recording, teardown]);

  return { supported, recording, error, start, stop };
}
