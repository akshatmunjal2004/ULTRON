import { useCallback, useEffect, useRef, useState } from 'react';
import { Keyboard, Loader2, Mic, Send, Square } from 'lucide-react';

import { useAgent } from '../context/AgentContext';
import { useToast } from '../context/ToastContext';
import { useWebSpeech } from '../hooks/useWebSpeech';
import { useSpeechSynthesis } from '../hooks/useSpeechSynthesis';
import { useAudioRecorder } from '../hooks/useAudioRecorder';
import { voice as voiceApi } from '../api/endpoints';
import UltronOrb from '../components/UltronOrb';
import TranscriptLog from '../components/TranscriptLog';
import ResponseStream from '../components/ResponseStream';

// The voice loop is a small state machine:
//
//   idle ─(start)→ listening ─(final transcript)→ thinking ─(reply)→
//   speaking ─(spoken)→ listening  (while active)  or  idle
//
// Two input paths feed the same machine: the Web Speech API where it exists
// (Chrome, Edge), and a record-then-transcribe fallback everywhere else. A
// typed box is always available so the app is never voice-only.

const STATES = { IDLE: 'idle', LISTENING: 'listening', THINKING: 'thinking', SPEAKING: 'speaking' };

export default function AssistantPage() {
  const { connection, messages, sendStreaming, reset } = useAgent();
  const toast = useToast();

  const [state, setState] = useState(STATES.IDLE);
  const [reply, setReply] = useState('');
  const [typed, setTyped] = useState('');
  const [showKeyboard, setShowKeyboard] = useState(false);

  const activeRef = useRef(false); // is a hands-free session running?
  const stateRef = useRef(state);
  useEffect(() => {
    stateRef.current = state;
  }, [state]);

  // --- speech output ----------------------------------------------------
  const { speaking, speak, stop: stopSpeaking } = useSpeechSynthesis(() => {
    // Finished talking: resume listening if the session is still active.
    if (activeRef.current) {
      setState(STATES.LISTENING);
      startInput();
    } else {
      setState(STATES.IDLE);
    }
  });

  // --- the core send ----------------------------------------------------
  const handleCommand = useCallback(
    async (text) => {
      const clean = text.trim();
      if (!clean) return;
      stopSpeaking();
      setState(STATES.THINKING);
      setReply('');

      try {
        let spoken = false;
        const result = await sendStreaming({
          text: clean,
          onToken: (_tok, full) => {
            setReply(full);
            // Flip to speaking as soon as the first tokens land, so the orb and
            // audio start together rather than after the whole reply arrives.
            if (!spoken) {
              spoken = true;
              setState(STATES.SPEAKING);
            }
          },
        });
        setReply(result.reply);
        setState(STATES.SPEAKING);
        speak(result.reply);
      } catch (err) {
        toast.error(err.message || 'The request failed.');
        setState(activeRef.current ? STATES.LISTENING : STATES.IDLE);
        if (activeRef.current) startInput();
      }
    },
    // startInput/ speak are stable enough for this loop; see refs above.
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [sendStreaming, speak, stopSpeaking, toast],
  );

  // --- input path A: Web Speech ----------------------------------------
  const onFinalTranscript = useCallback(
    (text) => {
      if (stateRef.current !== STATES.LISTENING) return;
      handleCommand(text);
    },
    [handleCommand],
  );

  const web = useWebSpeech(onFinalTranscript);

  // --- input path B: record → transcribe -------------------------------
  const [transcribing, setTranscribing] = useState(false);
  const recorder = useAudioRecorder(async (wavBlob) => {
    setTranscribing(true);
    try {
      const { text } = await voiceApi.transcribe(wavBlob);
      if (text) handleCommand(text);
      else {
        toast.info('No speech detected in that clip.');
        setState(STATES.IDLE);
      }
    } catch (err) {
      toast.error(err.message || 'Transcription failed.');
      setState(STATES.IDLE);
    } finally {
      setTranscribing(false);
    }
  });

  const usingWebSpeech = web.supported;

  const startInput = useCallback(() => {
    if (usingWebSpeech) web.start();
    // In the fallback path the user drives recording explicitly, so nothing to
    // auto-start here.
  }, [usingWebSpeech, web]);

  const stopInput = useCallback(() => {
    web.stop();
    if (recorder.recording) recorder.stop();
  }, [web, recorder]);

  // --- session controls -------------------------------------------------
  const startSession = () => {
    if (connection !== 'online') {
      toast.error('The backend is offline. Start it with: python run.py');
      return;
    }
    activeRef.current = true;
    setState(STATES.LISTENING);
    startInput();
  };

  const stopSession = () => {
    activeRef.current = false;
    stopSpeaking();
    stopInput();
    setState(STATES.IDLE);
  };

  const submitTyped = () => {
    const clean = typed.trim();
    if (!clean) return;
    setTyped('');
    activeRef.current = false; // typing is a one-shot, not a hands-free session
    handleCommand(clean);
  };

  useEffect(() => {
    if (web.error) toast.error(web.error);
  }, [web.error, toast]);
  useEffect(() => {
    if (recorder.error) toast.error(recorder.error);
  }, [recorder.error, toast]);

  // Reset conversation when leaving the page.
  useEffect(() => () => stopSession(), []); // eslint-disable-line react-hooks/exhaustive-deps

  const orbState = state;
  const listening = state === STATES.LISTENING;

  return (
    <div className="flex-1 mx-auto w-full max-w-6xl px-4 py-6 grid gap-6 lg:grid-cols-3 min-h-0">
      <div className="hidden lg:block min-h-0">
        <TranscriptLog messages={messages} />
      </div>

      <div className="flex flex-col items-center justify-center gap-6 relative">
        <div className="min-h-[1.5rem] text-center text-sm">
          {listening && (
            <span className="text-ultron-accent italic">
              {web.partial ? `"${web.partial}"` : 'Listening — just speak'}
            </span>
          )}
          {state === STATES.THINKING && <span className="text-ultron-bright">Thinking…</span>}
          {transcribing && <span className="text-ultron-bright">Transcribing…</span>}
        </div>

        <UltronOrb state={orbState} />

        {/* Primary control */}
        {state === STATES.IDLE ? (
          <button className="btn-primary px-6" onClick={startSession}>
            <Mic className="w-4 h-4" aria-hidden />
            {usingWebSpeech ? 'Start listening' : 'Start'}
          </button>
        ) : (
          <div className="flex items-center gap-3">
            {!usingWebSpeech && !recorder.recording && !transcribing && (
              <button className="btn-primary" onClick={recorder.start}>
                <Mic className="w-4 h-4" aria-hidden /> Record
              </button>
            )}
            {!usingWebSpeech && recorder.recording && (
              <button className="btn-primary" onClick={recorder.stop}>
                <Square className="w-3.5 h-3.5" aria-hidden /> Stop &amp; send
              </button>
            )}
            <button className="btn-danger" onClick={stopSession}>
              <Square className="w-3.5 h-3.5" aria-hidden /> End
            </button>
          </div>
        )}

        {/* Typed fallback — always available */}
        <div className="w-full max-w-md">
          <button
            className="text-xs text-ultron-muted hover:text-ultron-text flex items-center gap-1.5 mx-auto"
            onClick={() => setShowKeyboard((v) => !v)}
            aria-expanded={showKeyboard}
          >
            <Keyboard className="w-3.5 h-3.5" aria-hidden />
            {showKeyboard ? 'Hide keyboard' : 'Type instead'}
          </button>

          {showKeyboard && (
            <div className="mt-3 flex items-center gap-2 glass-panel px-3 py-2">
              <label htmlFor="typed" className="sr-only">
                Message
              </label>
              <input
                id="typed"
                className="flex-1 bg-transparent text-sm outline-none placeholder-ultron-muted"
                placeholder="Ask ULTRON anything"
                value={typed}
                onChange={(e) => setTyped(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && submitTyped()}
                disabled={state === STATES.THINKING}
              />
              <button
                className="btn-primary px-3 py-1.5"
                onClick={submitTyped}
                disabled={!typed.trim() || state === STATES.THINKING}
                aria-label="Send"
              >
                {state === STATES.THINKING ? (
                  <Loader2 className="w-4 h-4 animate-spin" aria-hidden />
                ) : (
                  <Send className="w-4 h-4" aria-hidden />
                )}
              </button>
            </div>
          )}
          {messages.length > 0 && (
            <button
              className="mt-3 mx-auto block text-xs text-ultron-muted hover:text-ultron-text"
              onClick={() => {
                reset();
                setReply('');
              }}
            >
              Clear conversation
            </button>
          )}
        </div>
      </div>

      <div className="hidden lg:block min-h-0">
        <ResponseStream text={reply} speaking={speaking} streaming={state === STATES.SPEAKING && speaking === false && reply !== ''} />
      </div>

      {/* Mobile: stack the panels under the orb */}
      <div className="lg:hidden flex flex-col gap-4 h-[60vh]">
        <ResponseStream text={reply} speaking={speaking} streaming={false} />
        <TranscriptLog messages={messages} />
      </div>
    </div>
  );
}
