import { useState, useEffect, useRef, useCallback } from 'react';

/**
 * Custom hook for AI Question Voice Narration using native Web SpeechSynthesis API.
 * Provides optional text-to-speech narration of interview questions with automatic
 * deduplication, voice selection, stop-on-toggle, and unmount cleanup.
 */
export function useQuestionNarration(currentQuestionText) {
  const [isNarrationEnabled, setIsNarrationEnabled] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);

  const isSupported =
    typeof window !== 'undefined' && Boolean(window.speechSynthesis);

  const lastSpokenTextRef = useRef('');
  const utteranceRef = useRef(null);

  // Helper to find best English voice safely
  const getEnglishVoice = useCallback(() => {
    if (!isSupported || typeof window === 'undefined' || !window.speechSynthesis) return null;
    try {
      const voices = window.speechSynthesis.getVoices() || [];
      return (
        voices.find((v) => v && (v.lang === 'en-US' || v.lang === 'en-GB')) ||
        voices.find((v) => v && v.lang && v.lang.startsWith('en')) ||
        voices[0] ||
        null
      );
    } catch (err) {
      return null;
    }
  }, [isSupported]);

  // Stop any active speech immediately
  const stop = useCallback(() => {
    if (isSupported && typeof window !== 'undefined' && window.speechSynthesis) {
      try {
        window.speechSynthesis.cancel();
      } catch (err) {
        // Ignore cancel error
      }
    }
    setIsSpeaking(false);
  }, [isSupported]);

  // Core speak method
  const speak = useCallback(
    (textToSpeak) => {
      if (!isSupported || !textToSpeak) return;

      // Cancel previous speech to prevent queuing
      window.speechSynthesis.cancel();

      try {
        const utterance = new SpeechSynthesisUtterance(textToSpeak);
        utterance.rate = 0.95;
        utterance.pitch = 1.0;
        utterance.volume = 1.0;

        const voice = getEnglishVoice();
        if (voice) {
          utterance.voice = voice;
        }

        utterance.onstart = () => setIsSpeaking(true);
        utterance.onend = () => setIsSpeaking(false);
        utterance.onerror = (event) => {
          // Ignore normal interruptions when switching questions or toggling OFF
          if (event.error !== 'interrupted' && event.error !== 'canceled') {
            console.warn('Question narration speech error:', event.error);
          }
          setIsSpeaking(false);
        };

        utteranceRef.current = utterance;
        window.speechSynthesis.speak(utterance);
      } catch (err) {
        console.warn('Failed to speak question:', err);
        setIsSpeaking(false);
      }
    },
    [getEnglishVoice, isSupported]
  );

  // Replay current question manually
  const replay = useCallback(() => {
    if (!currentQuestionText) return;
    lastSpokenTextRef.current = currentQuestionText;
    speak(currentQuestionText);
  }, [currentQuestionText, speak]);

  // Toggle narration ON/OFF
  const toggleNarration = useCallback(() => {
    setIsNarrationEnabled((prev) => {
      const nextState = !prev;
      if (!nextState) {
        // Turning OFF -> stop immediately
        stop();
        lastSpokenTextRef.current = '';
      } else if (currentQuestionText) {
        // Turning ON -> speak current question
        lastSpokenTextRef.current = currentQuestionText;
        speak(currentQuestionText);
      }
      return nextState;
    });
  }, [currentQuestionText, speak, stop]);

  // Handle automatic narration when currentQuestionText changes
  useEffect(() => {
    if (!isSupported) return;

    if (isNarrationEnabled && currentQuestionText) {
      // Deduplicate: speak only if question text has changed
      if (lastSpokenTextRef.current !== currentQuestionText) {
        lastSpokenTextRef.current = currentQuestionText;
        speak(currentQuestionText);
      }
    } else if (!isNarrationEnabled) {
      stop();
    }
  }, [currentQuestionText, isNarrationEnabled, isSupported, speak, stop]);

  // Clean up on unmount or page navigation (MANDATORY)
  useEffect(() => {
    return () => {
      if (typeof window !== 'undefined' && window.speechSynthesis) {
        window.speechSynthesis.cancel();
      }
    };
  }, []);

  return {
    isSupported,
    isNarrationEnabled,
    isSpeaking,
    toggleNarration,
    replay,
    stop,
  };
}

export default useQuestionNarration;
