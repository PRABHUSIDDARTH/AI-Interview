import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import api from '../services/api';
import useSpeechRecognition, { VOICE_STATES } from '../hooks/useSpeechRecognition';
import useMicPermission from '../hooks/useMicPermission';
import useQuestionNarration from '../hooks/useQuestionNarration';
import { DEFAULT_INTERVIEW_DURATION_SECONDS } from '../config';
import { StatusBadge } from '../components/Badge';
import GlassCard from '../components/GlassCard';
import Button from '../components/Button';
import {
  IconMic,
  IconMicOff,
  IconTimer,
  IconArrowRight,
  IconArrowLeft,
  IconSparkles,
  IconVolumeUp,
  IconVolumeOff,
  IconRefresh,
} from '../components/Icons';

/* ── Format mm:ss timer ─────────────────────────────────────── */
function formatTime(seconds) {
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
}

/* ── Mic Permission Banner ───────────────────────────────────── */
function MicPermissionBanner({ status, onRequest }) {
  if (status === 'granted' || status === 'checking' || status === 'unsupported') return null;

  if (status === 'denied') {
    return (
      <div className="p-4 bg-rose-500/10 border border-rose-500/30 rounded-xl text-xs text-rose-300 flex items-start gap-3">
        <IconMicOff className="w-4 h-4 flex-shrink-0 mt-0.5" />
        <div className="space-y-1">
          <p className="font-semibold">Microphone access is required for voice answers.</p>
          <p className="text-rose-400/80">
            Please allow microphone access in your browser settings (click the lock icon in the
            address bar → Site permissions → Microphone → Allow), then refresh the page.
          </p>
          <p className="text-rose-400/70 mt-1">
            You can still type your answer below — the interview will continue normally.
          </p>
        </div>
      </div>
    );
  }

  if (status === 'prompt') {
    return (
      <div className="p-3.5 bg-amber-500/10 border border-amber-500/30 rounded-xl text-xs text-amber-300 flex items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <IconMic className="w-4 h-4 flex-shrink-0" />
          <span>Grant microphone permission for voice answers.</span>
        </div>
        <button
          type="button"
          onClick={onRequest}
          className="px-3 py-1.5 rounded-lg bg-amber-500/20 border border-amber-500/40 text-amber-200 font-semibold text-xs hover:bg-amber-500/30 transition-colors flex-shrink-0"
        >
          Allow Mic
        </button>
      </div>
    );
  }

  return null;
}

/* ── Voice Control Panel ─────────────────────────────────────── */
function VoiceControlPanel({
  voiceState,
  error,
  lowQualityWarning,
  interimText,
  recordingSeconds,
  isSupported,
  micPermissionStatus,
  onStart,
  onStop,
  onRetry,
  onTypeInstead,
  showTypeInstead,
}) {
  if (!isSupported) {
    return (
      <div className="p-3 bg-amber-500/10 border border-amber-500/20 rounded-xl text-xs text-amber-300">
        Voice input is not supported in this browser. Please use Chrome or Edge.
      </div>
    );
  }

  if (micPermissionStatus === 'denied') {
    return (
      <div className="text-xs text-slate-500 italic px-1">
        Microphone access denied — using text input only.
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {/* State-specific controls */}
      {voiceState === VOICE_STATES.IDLE && (
        <button
          type="button"
          id="btn-start-recording"
          onClick={onStart}
          className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl text-xs font-semibold glass-panel hover:bg-white/10 text-slate-200 border-white/15 transition-all hover:border-primary-500/40"
        >
          <IconMic className="w-4 h-4 text-accent-cyan" />
          <span>🎤 Start Recording</span>
        </button>
      )}

      {voiceState === VOICE_STATES.LISTENING && (
        <div className="flex items-center gap-3 flex-wrap">
          {/* Animated recording indicator */}
          <div className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-rose-500/15 border border-rose-500/40 text-rose-300 text-xs font-semibold animate-pulse">
            <span className="w-2.5 h-2.5 rounded-full bg-rose-500 animate-ping" />
            <span>🔴 Recording...</span>
            <span className="font-mono text-rose-400">{formatTime(recordingSeconds)}</span>
          </div>

          {/* Stop button */}
          <button
            type="button"
            id="btn-stop-recording"
            onClick={onStop}
            className="px-4 py-2 rounded-xl bg-rose-600/20 border border-rose-500/50 text-rose-200 text-xs font-bold hover:bg-rose-600/30 transition-colors"
          >
            ⏹ Stop
          </button>

          {/* Live interim text */}
          {interimText && (
            <p className="text-xs italic text-slate-400 max-w-sm truncate">
              {interimText}
            </p>
          )}
        </div>
      )}

      {voiceState === VOICE_STATES.STOPPING && (
        <div className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-amber-500/10 border border-amber-500/30 text-amber-300 text-xs font-semibold">
          <span className="animate-spin">⏳</span>
          <span>Converting speech to text...</span>
        </div>
      )}

      {voiceState === VOICE_STATES.TRANSCRIPT_READY && (
        <div className="flex items-center gap-3 flex-wrap">
          <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg bg-emerald-500/10 border border-emerald-500/30 text-emerald-300 text-xs font-semibold">
            <span className="w-2 h-2 rounded-full bg-emerald-400" />
            Transcript ready
          </div>
          <button
            type="button"
            onClick={onRetry}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-white/5 border border-white/10 text-slate-300 hover:bg-white/10 transition-colors"
          >
            <IconRefresh className="w-3.5 h-3.5" />
            Re-record
          </button>
        </div>
      )}

      {voiceState === VOICE_STATES.ERROR && (
        <div className="space-y-2">
          <div className="p-3 bg-rose-500/10 border border-rose-500/30 text-rose-300 rounded-xl text-xs flex items-start gap-2">
            <span className="w-2 h-2 rounded-full bg-rose-400 flex-shrink-0 mt-1" />
            <span>{error || 'Speech recognition failed.'}</span>
          </div>
          <div className="flex items-center gap-2 flex-wrap">
            <button
              type="button"
              id="btn-retry-recording"
              onClick={onRetry}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-primary-600/20 border border-primary-500/30 text-primary-300 hover:bg-primary-600/30 transition-colors"
            >
              <IconRefresh className="w-3.5 h-3.5" />
              🔄 Retry Recording
            </button>
            {!showTypeInstead && (
              <button
                type="button"
                id="btn-type-instead"
                onClick={onTypeInstead}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-white/5 border border-white/10 text-slate-300 hover:bg-white/10 transition-colors"
              >
                ✏️ Type Answer Instead
              </button>
            )}
          </div>
        </div>
      )}

      {/* Low-quality warning (non-blocking) */}
      {lowQualityWarning && voiceState !== VOICE_STATES.ERROR && (
        <div className="p-3 bg-amber-500/10 border border-amber-500/30 text-amber-300 rounded-xl text-xs flex items-start gap-2">
          <span className="w-2 h-2 rounded-full bg-amber-400 flex-shrink-0 mt-1" />
          <span>{lowQualityWarning}</span>
        </div>
      )}
    </div>
  );
}

/* ── Main Component ─────────────────────────────────────────── */
export default function InterviewRoomPage() {
  const { interviewId } = useParams();
  const navigate = useNavigate();

  /* session metadata */
  const [interview, setInterview] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  /* question / answer flow */
  const [question, setQuestion] = useState(null);
  const [answer, setAnswer] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [fetchingQuestion, setFetchingQuestion] = useState(false);
  const [apiError, setApiError] = useState('');

  /* voice UX */
  const [showTypeInstead, setShowTypeInstead] = useState(false);

  /* progress tracking */
  const [questionNumber, setQuestionNumber] = useState(1);
  const [remainingTime, setRemainingTime] = useState(DEFAULT_INTERVIEW_DURATION_SECONDS);
  const timerRef = useRef(null);
  const timerInitialized = useRef(false);
  const [isComplete, setIsComplete] = useState(false);

  /* Mic permission */
  const { status: micPermissionStatus, requestPermission } = useMicPermission();

  /* Question TTS narration */
  const {
    isSupported: isNarrationSupported,
    isNarrationEnabled,
    isSpeaking: isQuestionSpeaking,
    toggleNarration,
    replay: replayQuestionNarration,
    stop: stopQuestionNarration,
  } = useQuestionNarration(question?.text);

  /* Voice recognition */
  const handleTranscript = useCallback(({ fullText }) => {
    if (fullText !== undefined) {
      setAnswer(fullText);
    }
  }, []);

  const {
    voiceState,
    isSupported: isSpeechSupported,
    isListening,
    interimText,
    recordingSeconds,
    error: speechError,
    lowQualityWarning,
    startListening,
    stopListening,
    resetVoice,
    resetTranscript,
  } = useSpeechRecognition({
    onTranscript: handleTranscript,
    lang: interview?.interview_language || 'English',
  });

  /* Handle voice start */
  const handleStartVoice = () => {
    if (isQuestionSpeaking) stopQuestionNarration();
    startListening(answer);
  };

  /* Handle voice stop */
  const handleStopVoice = () => {
    stopListening();
  };

  /* Handle retry */
  const handleRetry = () => {
    resetVoice();
    setAnswer('');
  };

  /* Handle type-instead */
  const handleTypeInstead = () => {
    resetVoice();
    setShowTypeInstead(true);
    setAnswer('');
  };

  /* Submit current answer */
  const submitCurrentAnswer = async () => {
    if (!answer.trim() || submitting) return;
    setSubmitting(true);
    setApiError('');

    stopListening();
    stopQuestionNarration();

    try {
      await api.post(`/interviews/${interviewId}/answer`, { answer: answer.trim() });
      if (questionNumber >= (interview?.question_count || 0)) {
        navigate(`/interview/${interviewId}/evaluation`);
      } else {
        setQuestionNumber((prev) => prev + 1);
        setQuestion(null);
        setAnswer('');
        resetVoice();
        setShowTypeInstead(false);
      }
    } catch (err) {
      const detail = err?.response?.data?.detail || 'Failed to submit answer.';
      setApiError(typeof detail === 'string' ? detail : JSON.stringify(detail));
    } finally {
      setSubmitting(false);
    }
  };

  /* Load session details */
  useEffect(() => {
    if (!interviewId) {
      setError('Invalid interview session ID.');
      setLoading(false);
      return;
    }
    (async () => {
      try {
        const { data } = await api.get(`/interviews/${interviewId}`);
        if (!data) {
          setError('Interview session data is empty.');
        } else {
          setInterview(data);
          setQuestionNumber((data.answered_count || 0) + 1);
          if (data.status === 'completed') setIsComplete(true);
        }
      } catch (err) {
        if (err?.response?.status === 404)
          setError('Interview session not found or you do not have access.');
        else if (err?.response?.status === 401)
          navigate('/login');
        else
          setError('Failed to load interview session. Please try again.');
      } finally {
        setLoading(false);
      }
    })();
  }, [interviewId, navigate]);

  /* Timer effect */
  useEffect(() => {
    if (!interview || isComplete) return;
    if (timerInitialized.current) return;
    timerInitialized.current = true;
    setRemainingTime(DEFAULT_INTERVIEW_DURATION_SECONDS);

    timerRef.current = setInterval(() => {
      setRemainingTime((prev) => {
        if (prev <= 1) {
          clearInterval(timerRef.current);
          if (answer.trim()) {
            submitCurrentAnswer();
          } else {
            navigate(`/interview/${interviewId}/evaluation`);
          }
          return 0;
        }
        return prev - 1;
      });
    }, 1000);

    return () => clearInterval(timerRef.current);
  }, [interview, isComplete, answer, interviewId, navigate]);

  /* Fetch next question */
  const fetchNextQuestion = useCallback(async () => {
    if (!interviewId) return;
    setFetchingQuestion(true);
    setApiError('');
    stopListening();
    resetVoice();
    try {
      const { data } = await api.get(`/interviews/${interviewId}/next`);
      if (data && data.question) {
        setQuestion(data.question);
      } else {
        setApiError('No question data returned from backend.');
      }
      setAnswer('');
    } catch (err) {
      const detail = err?.response?.data?.detail || 'Failed to fetch next question.';
      setApiError(typeof detail === 'string' ? detail : JSON.stringify(detail));
    } finally {
      setFetchingQuestion(false);
    }
  }, [interviewId, stopListening, resetVoice]);

  useEffect(() => {
    if (interview && !question && !isComplete) fetchNextQuestion();
  }, [interview, question, isComplete, fetchNextQuestion]);

  const handleSubmitAnswer = (e) => {
    e.preventDefault();
    submitCurrentAnswer();
  };

  /* ── Render States ── */
  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[50vh] space-y-4">
        <div className="w-12 h-12 rounded-full border-2 border-primary-500/30 border-t-primary-500 animate-spin" />
        <p className="text-slate-400 text-sm">Initializing AI Interview Studio...</p>
      </div>
    );
  }

  if (error || !interview) {
    return (
      <div className="max-w-xl mx-auto mt-12 text-center space-y-4">
        <GlassCard className="space-y-4 p-8">
          <div className="w-14 h-14 rounded-2xl bg-rose-500/10 border border-rose-500/20 text-rose-400 flex items-center justify-center mx-auto">
            <IconArrowLeft className="w-6 h-6" />
          </div>
          <h2 className="text-xl font-bold text-white">Session Unavailable</h2>
          <p className="text-slate-400 text-xs">{error || 'Unable to load interview session context.'}</p>
          <Button onClick={() => navigate('/dashboard')} variant="primary">
            Return to Dashboard
          </Button>
        </GlassCard>
      </div>
    );
  }

  const questionCount = interview?.question_count || 1;
  const progressPercentage = Math.min((questionNumber / questionCount) * 100, 100);

  /* Determine if voice panel should be shown */
  const showVoicePanel =
    isSpeechSupported &&
    micPermissionStatus !== 'denied' &&
    !showTypeInstead;

  return (
    <div className="max-w-4xl mx-auto space-y-6 pb-12">
      {/* Top Header Controls */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <button
          type="button"
          onClick={() => {
            stopListening();
            stopQuestionNarration();
            navigate('/dashboard');
          }}
          className="inline-flex items-center gap-2 text-xs font-semibold text-slate-400 hover:text-white transition-colors group self-start"
        >
          <IconArrowLeft className="w-4 h-4 group-hover:-translate-x-1 transition-transform" />
          <span>Exit to Dashboard</span>
        </button>

        {/* Live Timer Pill */}
        <div className="flex items-center gap-4">
          <div className={`inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full text-xs font-mono font-bold border backdrop-blur-md ${remainingTime <= 60
            ? 'bg-rose-500/15 border-rose-500/30 text-rose-400 animate-pulse'
            : 'bg-primary-600/15 border-primary-500/30 text-primary-300'
            }`}>
            <IconTimer className="w-4 h-4" />
            <span>{formatTime(remainingTime)}</span>
          </div>
          <StatusBadge status={isComplete ? 'completed' : (interview?.status || 'in_progress')} />
        </div>
      </div>

      {/* Session Context Bar */}
      <GlassCard className="p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-white/[0.02]">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-primary-600 to-accent-cyan flex items-center justify-center text-white shadow-glow-primary">
            <IconSparkles className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-sm font-bold text-white tracking-tight">{interview?.job_role || 'Software Engineer'}</h2>
            <p className="text-[11px] text-slate-400">
              {interview?.interview_type || 'Technical'} Domain · {interview?.difficulty || 'Medium'} Difficulty
            </p>
          </div>
        </div>

        {/* Question Counter Progress */}
        <div className="flex items-center gap-3 min-w-[200px]">
          <div className="flex-1 space-y-1">
            <div className="flex justify-between text-[11px] font-semibold text-slate-400">
              <span>Question {questionNumber} of {questionCount}</span>
              <span>{Math.round(progressPercentage)}%</span>
            </div>
            <div className="h-2 w-full bg-white/5 rounded-full overflow-hidden">
              <div
                className="h-full bg-gradient-to-r from-primary-500 to-accent-cyan rounded-full transition-all duration-500"
                style={{ width: `${progressPercentage}%` }}
              />
            </div>
          </div>
        </div>
      </GlassCard>

      {/* Mic Permission Banner (proactive) */}
      <MicPermissionBanner
        status={micPermissionStatus}
        onRequest={requestPermission}
      />

      {/* API Error Display */}
      {apiError && (
        <div className="p-3.5 bg-rose-500/10 border border-rose-500/30 text-rose-300 rounded-xl text-xs flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-rose-400 flex-shrink-0" />
          <span>{apiError}</span>
        </div>
      )}

      {/* Loading Question Placeholder */}
      {!isComplete && fetchingQuestion && !question && (
        <GlassCard className="p-12 text-center space-y-4">
          <div className="w-10 h-10 rounded-full border-2 border-primary-500/30 border-t-primary-500 animate-spin mx-auto" />
          <p className="text-xs text-slate-400">AI is tailoring your next question...</p>
        </GlassCard>
      )}

      {/* Fallback Question Retry Card */}
      {!isComplete && !fetchingQuestion && !question && (
        <GlassCard className="p-12 text-center space-y-4">
          <h3 className="text-base font-bold text-white">No Question Available</h3>
          <p className="text-xs text-slate-400">Click below to fetch your next interview question.</p>
          <Button onClick={fetchNextQuestion} variant="primary">
            Load Question
          </Button>
        </GlassCard>
      )}

      {/* Main Question & Answer Card */}
      {!isComplete && question && (
        <GlassCard className="space-y-6 border-primary-500/20 shadow-glow-primary/10 p-6 sm:p-8">
          {/* Question Display Header */}
          <div className="space-y-4 border-b border-white/[0.08] pb-6">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div className="flex flex-wrap items-center gap-2">
                <span className="px-2.5 py-1 rounded-md text-[11px] font-extrabold uppercase tracking-wider bg-primary-600/20 text-primary-300 border border-primary-500/30">
                  Question #{questionNumber}
                </span>
                <span className="text-xs text-slate-400 font-mono">
                  {interview?.interview_type || 'Technical'}
                </span>
                {question?.metadata?.current_difficulty && (
                  <span className={`px-2 py-0.5 rounded text-[10px] font-semibold border ${question.metadata.current_difficulty.toLowerCase() === 'hard'
                    ? 'bg-rose-500/15 text-rose-300 border-rose-500/30'
                    : question.metadata.current_difficulty.toLowerCase() === 'easy'
                      ? 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30'
                      : 'bg-amber-500/15 text-amber-300 border-amber-500/30'
                    }`}>
                    {question.metadata.current_difficulty}
                  </span>
                )}
                {question?.metadata?.topic && (
                  <span className="px-2 py-0.5 rounded text-[10px] font-medium bg-white/5 text-slate-300 border border-white/10">
                    {question.metadata.topic}
                  </span>
                )}
              </div>

              {/* ── QUESTION VOICE NARRATION CONTROL BAR ── */}
              {isNarrationSupported ? (
                <div className="flex items-center gap-3 bg-white/[0.03] border border-white/[0.08] px-3 py-1.5 rounded-xl">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-semibold text-slate-300 flex items-center gap-1.5">
                      {isQuestionSpeaking ? (
                        <IconVolumeUp className="w-4 h-4 text-accent-cyan animate-pulse" />
                      ) : (
                        <IconVolumeUp className="w-4 h-4 text-slate-400" />
                      )}
                      <span>Read Aloud</span>
                    </span>

                    <button
                      type="button"
                      onClick={toggleNarration}
                      aria-label="Read interview questions aloud"
                      title={isNarrationEnabled ? 'Turn narration OFF' : 'Turn narration ON'}
                      className={`relative inline-flex h-6 w-11 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none focus:ring-2 focus:ring-primary-500 ${isNarrationEnabled ? 'bg-primary-600' : 'bg-slate-700'
                        }`}
                    >
                      <span
                        className={`pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out ${isNarrationEnabled ? 'translate-x-5' : 'translate-x-0'
                          }`}
                      />
                    </button>
                    <span className="text-[11px] font-mono font-bold text-slate-300 w-7">
                      {isNarrationEnabled ? 'ON' : 'OFF'}
                    </span>
                  </div>

                  {isNarrationEnabled && (
                    <div className="flex items-center gap-2 pl-2 border-l border-white/10">
                      {isQuestionSpeaking ? (
                        <span className="text-xs font-semibold text-accent-cyan flex items-center gap-1.5 animate-pulse">
                          <span className="w-2 h-2 rounded-full bg-accent-cyan" />
                          Speaking...
                        </span>
                      ) : (
                        <button
                          type="button"
                          onClick={replayQuestionNarration}
                          aria-label="Replay current question"
                          className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs font-medium bg-primary-600/20 text-primary-300 border border-primary-500/30 hover:bg-primary-600/30 transition-colors"
                        >
                          <IconRefresh className="w-3.5 h-3.5" />
                          <span>Replay</span>
                        </button>
                      )}
                    </div>
                  )}
                </div>
              ) : (
                <span className="text-xs text-slate-500 italic">
                  Voice narration is not supported in this browser.
                </span>
              )}
            </div>

            {/* Question Text */}
            <h3 className="text-lg sm:text-xl font-bold text-white leading-relaxed tracking-tight">
              {question.text}
            </h3>
          </div>

          {/* Answer Area Form */}
          <form onSubmit={handleSubmitAnswer} className="space-y-5">

            {/* Voice Control Panel */}
            {showVoicePanel && (
              <div className="space-y-3">
                <p className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
                  Voice Answer
                </p>
                <VoiceControlPanel
                  voiceState={voiceState}
                  error={speechError}
                  lowQualityWarning={lowQualityWarning}
                  interimText={interimText}
                  recordingSeconds={recordingSeconds}
                  isSupported={isSpeechSupported}
                  micPermissionStatus={micPermissionStatus}
                  onStart={handleStartVoice}
                  onStop={handleStopVoice}
                  onRetry={handleRetry}
                  onTypeInstead={handleTypeInstead}
                  showTypeInstead={showTypeInstead}
                />
              </div>
            )}

            {/* Transcript / Text Answer Area */}
            <div className="space-y-2">
              <div className="flex justify-between items-center text-xs text-slate-400">
                <label htmlFor="answer-input" className="font-semibold text-slate-300 uppercase tracking-wider text-[11px]">
                  {voiceState === VOICE_STATES.TRANSCRIPT_READY && !showTypeInstead
                    ? 'Transcript — Review & Edit Before Submitting'
                    : 'Your Answer'}
                </label>
                <span className="font-mono">{answer.length} characters</span>
              </div>

              <div className="relative">
                <textarea
                  id="answer-input"
                  required
                  disabled={submitting}
                  rows={6}
                  value={answer}
                  onChange={(e) => setAnswer(e.target.value)}
                  placeholder={
                    isListening
                      ? 'Listening... speak your answer clearly'
                      : voiceState === VOICE_STATES.TRANSCRIPT_READY
                        ? 'Review and edit your transcript here before submitting...'
                        : showVoicePanel
                          ? 'Click Start Recording above, or type your response here...'
                          : 'Type your response here...'
                  }
                  className={`w-full p-4 rounded-xl glass-input text-sm leading-relaxed placeholder-slate-500 resize-y transition-all ${voiceState === VOICE_STATES.TRANSCRIPT_READY
                    ? 'border-emerald-500/30 ring-1 ring-emerald-500/20'
                    : isListening
                      ? 'border-rose-500/30 ring-1 ring-rose-500/20'
                      : ''
                    }`}
                />
                {/* Live listening indicator overlay */}
                {isListening && (
                  <div className="absolute top-2 right-2 flex items-center gap-1.5 px-2 py-1 rounded-md bg-rose-500/20 border border-rose-500/30">
                    <span className="w-1.5 h-1.5 rounded-full bg-rose-400 animate-ping" />
                    <span className="text-[10px] font-bold text-rose-300">LIVE</span>
                  </div>
                )}
              </div>

              {/* Type-instead toggle when voice is visible */}
              {showVoicePanel && !showTypeInstead && voiceState === VOICE_STATES.IDLE && (
                <p className="text-[11px] text-slate-500">
                  Prefer typing?{' '}
                  <button
                    type="button"
                    onClick={handleTypeInstead}
                    className="text-slate-400 underline underline-offset-2 hover:text-white transition-colors"
                  >
                    Switch to text input
                  </button>
                </p>
              )}
              {showTypeInstead && (
                <p className="text-[11px] text-slate-500">
                  <button
                    type="button"
                    onClick={() => { setShowTypeInstead(false); resetVoice(); }}
                    className="text-slate-400 underline underline-offset-2 hover:text-white transition-colors"
                  >
                    Switch back to voice
                  </button>
                </p>
              )}
            </div>

            {/* Submit Row */}
            <div className="flex items-center justify-end pt-1">
              <Button
                id="btn-submit-answer"
                type="submit"
                loading={submitting}
                disabled={!answer.trim() || isListening}
                icon={IconArrowRight}
                iconPosition="right"
                variant="primary"
                className="px-6 py-2.5 shadow-glow-primary"
              >
                Submit Response
              </Button>
            </div>
          </form>
        </GlassCard>
      )}
    </div>
  );
}
