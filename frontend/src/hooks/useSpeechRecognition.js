import { useState, useEffect, useRef, useCallback } from 'react';

/**
 * Formats common technical interview terms without altering general sentence structure.
 */
export function formatTechnicalTerms(text) {
  if (!text || typeof text !== 'string') return text;
  const termsMap = {
    python: 'Python',
    javascript: 'JavaScript',
    typescript: 'TypeScript',
    react: 'React',
    fastapi: 'FastAPI',
    sqlalchemy: 'SQLAlchemy',
    postgresql: 'PostgreSQL',
    postgres: 'PostgreSQL',
    'rest api': 'REST API',
    'restful api': 'RESTful API',
    jwt: 'JWT',
    oauth: 'OAuth2',
    oauth2: 'OAuth2',
    docker: 'Docker',
    kubernetes: 'Kubernetes',
    github: 'GitHub',
    aws: 'AWS',
    azure: 'Azure',
  };

  let formatted = text;
  Object.keys(termsMap).forEach((term) => {
    const regex = new RegExp(`\\b${term}\\b`, 'gi');
    formatted = formatted.replace(regex, termsMap[term]);
  });
  return formatted;
}

const LANGUAGE_CODE_MAP = {
  English: 'en-US',
  Tamil: 'ta-IN',
  Hindi: 'hi-IN',
  Telugu: 'te-IN',
  Kannada: 'kn-IN',
  Malayalam: 'ml-IN',
};

export function getLanguageCode(lang) {
  if (!lang) return 'en-US';
  if (LANGUAGE_CODE_MAP[lang]) return LANGUAGE_CODE_MAP[lang];
  if (lang.includes('-')) return lang;
  return 'en-US';
}

/**
 * Voice state machine values.
 * idle            → Mic button not pressed
 * listening       → Actively recording speech
 * stopping        → Stop pressed; awaiting final transcript from browser
 * transcript_ready → Final transcript available for review/edit
 * error           → Recognition failed; retry or type-instead shown
 */
export const VOICE_STATES = {
  IDLE: 'idle',
  LISTENING: 'listening',
  STOPPING: 'stopping',
  TRANSCRIPT_READY: 'transcript_ready',
  ERROR: 'error',
};

// Minimum characters for a transcript to be considered meaningful
const MIN_TRANSCRIPT_CHARS = 8;

/**
 * Enhanced custom hook for browser-native Web Speech / SpeechRecognition API.
 * Adds: voiceState enum, recording duration timer, empty-transcript detection,
 * higher restart cap, retry/reset, and clear error distinction.
 */
export function useSpeechRecognition({ onTranscript, lang = 'English' } = {}) {
  const [voiceState, setVoiceState] = useState(VOICE_STATES.IDLE);
  const [error, setError] = useState('');
  const [interimText, setInterimText] = useState('');
  const [recordingSeconds, setRecordingSeconds] = useState(0);
  const [lowQualityWarning, setLowQualityWarning] = useState('');

  const recognitionRef = useRef(null);
  const isRecordingRef = useRef(false);
  const restartCountRef = useRef(0);
  const lastRestartTimeRef = useRef(0);
  const finalTranscriptRef = useRef('');
  const onTranscriptRef = useRef(onTranscript);
  const timerRef = useRef(null);

  // Keep onTranscript callback fresh in ref
  useEffect(() => {
    onTranscriptRef.current = onTranscript;
  }, [onTranscript]);

  const isSupported =
    typeof window !== 'undefined' &&
    Boolean(window.SpeechRecognition || window.webkitSpeechRecognition);

  // ── Recording Timer ──────────────────────────────────────────────
  const startTimer = useCallback(() => {
    setRecordingSeconds(0);
    if (timerRef.current) clearInterval(timerRef.current);
    timerRef.current = setInterval(() => {
      setRecordingSeconds((prev) => prev + 1);
    }, 1000);
  }, []);

  const stopTimer = useCallback(() => {
    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }
  }, []);

  // ── Cleanup ──────────────────────────────────────────────────────
  const cleanupRecognition = useCallback(() => {
    if (recognitionRef.current) {
      try {
        recognitionRef.current.onstart = null;
        recognitionRef.current.onresult = null;
        recognitionRef.current.onerror = null;
        recognitionRef.current.onend = null;
        recognitionRef.current.abort();
      } catch (_) {
        // Ignore abort errors
      }
      recognitionRef.current = null;
    }
  }, []);

  // ── Stop Listening ───────────────────────────────────────────────
  const stopListening = useCallback(() => {
    isRecordingRef.current = false;
    stopTimer();
    cleanupRecognition();
    setInterimText('');

    // Check transcript quality on stop
    const transcript = finalTranscriptRef.current.trim();
    if (transcript.length === 0) {
      setLowQualityWarning(
        'No speech detected. Please try recording again or type your answer below.'
      );
      setVoiceState(VOICE_STATES.ERROR);
    } else if (transcript.length < MIN_TRANSCRIPT_CHARS) {
      setLowQualityWarning(
        'Your answer seems very short. Please review the transcript below and edit if needed.'
      );
      setVoiceState(VOICE_STATES.TRANSCRIPT_READY);
    } else {
      setLowQualityWarning('');
      setVoiceState(VOICE_STATES.TRANSCRIPT_READY);
    }
  }, [cleanupRecognition, stopTimer]);

  // ── Start Listening ──────────────────────────────────────────────
  const startListening = useCallback(
    (initialText = '') => {
      if (!isSupported) {
        setError('Voice input is not supported in this browser. Please use Chrome or Edge.');
        setVoiceState(VOICE_STATES.ERROR);
        return;
      }

      setError('');
      setLowQualityWarning('');
      isRecordingRef.current = true;
      restartCountRef.current = 0;
      if (initialText !== undefined) {
        finalTranscriptRef.current = initialText;
      }

      cleanupRecognition();
      startTimer();

      const SpeechRecognitionAPI =
        window.SpeechRecognition || window.webkitSpeechRecognition;

      try {
        const recognition = new SpeechRecognitionAPI();
        recognition.continuous = true;
        recognition.interimResults = true;
        recognition.lang = getLanguageCode(lang);
        // maxAlternatives: 1 is the default, keep it
        recognition.maxAlternatives = 1;

        recognition.onstart = () => {
          setVoiceState(VOICE_STATES.LISTENING);
          setError('');
        };

        recognition.onresult = (event) => {
          let currentInterim = '';

          for (let i = event.resultIndex; i < event.results.length; i++) {
            const result = event.results[i];
            const transcriptChunk = result[0]?.transcript || '';

            if (result.isFinal) {
              const currentFinal = finalTranscriptRef.current.trim();
              const chunk = transcriptChunk.trim();
              if (chunk) {
                const formattedChunk = formatTechnicalTerms(chunk);
                finalTranscriptRef.current = currentFinal
                  ? `${currentFinal} ${formattedChunk}`
                  : formattedChunk;
              }
            } else {
              currentInterim += transcriptChunk;
            }
          }

          setInterimText(currentInterim);

          if (onTranscriptRef.current) {
            const fullText = [finalTranscriptRef.current, currentInterim.trim()]
              .filter(Boolean)
              .join(' ');

            onTranscriptRef.current({
              finalTranscript: finalTranscriptRef.current,
              interimTranscript: currentInterim.trim(),
              fullText,
            });
          }
        };

        recognition.onerror = (event) => {
          const errType = event.error;

          if (errType === 'no-speech') {
            // Non-fatal: browser paused because of silence → will auto-restart
            return;
          }

          if (errType === 'not-allowed' || errType === 'service-not-allowed') {
            isRecordingRef.current = false;
            stopTimer();
            setError(
              'Microphone access is required for voice answers. Please allow microphone access in your browser settings, then try again.'
            );
            setVoiceState(VOICE_STATES.ERROR);
          } else if (errType === 'audio-capture') {
            isRecordingRef.current = false;
            stopTimer();
            setError(
              'No microphone found. Please check your audio input device and try again.'
            );
            setVoiceState(VOICE_STATES.ERROR);
          } else if (errType === 'network') {
            setError(
              'Network issue with speech recognition. Please check your connection.'
            );
            // Not setting ERROR state — will auto-restart
          } else if (errType !== 'aborted') {
            setError(
              'Speech recognition encountered an issue. You can type your answer instead.'
            );
            setVoiceState(VOICE_STATES.ERROR);
          }
        };

        recognition.onend = () => {
          // Auto-restart if user did NOT explicitly click stop
          // Increased cap from 5 → 12 to support long answers (each segment ~30s)
          if (isRecordingRef.current) {
            const now = Date.now();
            if (now - lastRestartTimeRef.current < 2000) {
              restartCountRef.current += 1;
            } else {
              restartCountRef.current = 1;
            }
            lastRestartTimeRef.current = now;

            if (restartCountRef.current <= 12) {
              try {
                recognition.start();
                return;
              } catch (_) {
                // Ignore start failure
              }
            }
          }

          // Natural end or restart cap exceeded
          if (isRecordingRef.current) {
            // Restart cap hit — finalize transcript
            isRecordingRef.current = false;
            stopTimer();
            const transcript = finalTranscriptRef.current.trim();
            if (transcript.length >= MIN_TRANSCRIPT_CHARS) {
              setVoiceState(VOICE_STATES.TRANSCRIPT_READY);
            } else {
              setError('Recording ended. Please type your answer or try again.');
              setVoiceState(VOICE_STATES.ERROR);
            }
          }
          setInterimText('');
        };

        recognitionRef.current = recognition;
        recognition.start();
      } catch (err) {
        stopTimer();
        setError(
          'Microphone permission is required for voice answers. Please allow microphone access and try again.'
        );
        setVoiceState(VOICE_STATES.ERROR);
      }
    },
    [isSupported, lang, cleanupRecognition, startTimer, stopTimer]
  );

  // ── Reset (clears transcript + state, for retry) ─────────────────
  const resetVoice = useCallback(() => {
    isRecordingRef.current = false;
    stopTimer();
    cleanupRecognition();
    finalTranscriptRef.current = '';
    setInterimText('');
    setError('');
    setLowQualityWarning('');
    setRecordingSeconds(0);
    setVoiceState(VOICE_STATES.IDLE);
    if (onTranscriptRef.current) {
      onTranscriptRef.current({ finalTranscript: '', interimTranscript: '', fullText: '' });
    }
  }, [cleanupRecognition, stopTimer]);

  // ── Legacy: resetTranscript (keeps compatibility) ─────────────────
  const resetTranscript = useCallback(() => {
    resetVoice();
  }, [resetVoice]);

  // ── Derived booleans for backward compat ─────────────────────────
  const isListening = voiceState === VOICE_STATES.LISTENING;
  const isStopping = voiceState === VOICE_STATES.STOPPING;

  // ── Cleanup on unmount ───────────────────────────────────────────
  useEffect(() => {
    return () => {
      isRecordingRef.current = false;
      stopTimer();
      cleanupRecognition();
    };
  }, [cleanupRecognition, stopTimer]);

  return {
    // State machine
    voiceState,
    // Derived booleans (backward-compat)
    isSupported,
    isListening,
    isStopping,
    // Live interim text while speaking
    interimText,
    // Elapsed recording seconds
    recordingSeconds,
    // Errors and warnings
    error,
    lowQualityWarning,
    clearError: () => { setError(''); setLowQualityWarning(''); },
    // Actions
    startListening,
    stopListening,
    resetVoice,
    resetTranscript,  // backward-compat alias
  };
}

export default useSpeechRecognition;
