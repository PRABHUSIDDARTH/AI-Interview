import React, { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import api from '../services/api';
import { jsPDF } from 'jspdf';
import html2canvas from 'html2canvas';
import GlassCard from '../components/GlassCard';
import Button from '../components/Button';
import {
  IconCheck,
  IconArrowLeft,
  IconArrowRight,
  IconSparkles,
  IconDownload,
  IconRefresh,
} from '../components/Icons';

/* ── Score Ring SVG ────────────────────────────────────────── */
function ScoreRing({ value, max = 10, size = 110 }) {
  const radius = (size - 14) / 2;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (value / max) * circumference;
  const color = value >= 7 ? '#22C55E' : value >= 4 ? '#F59E0B' : '#EF4444';

  return (
    <svg width={size} height={size} className="drop-shadow-glow">
      <circle
        cx={size / 2}
        cy={size / 2}
        r={radius}
        stroke="rgba(255,255,255,0.08)"
        strokeWidth="8"
        fill="none"
      />
      <circle
        cx={size / 2}
        cy={size / 2}
        r={radius}
        stroke={color}
        strokeWidth="8"
        fill="none"
        strokeLinecap="round"
        strokeDasharray={circumference}
        strokeDashoffset={offset}
        style={{ transition: 'stroke-dashoffset 1s cubic-bezier(0.16,1,0.3,1)' }}
        transform={`rotate(-90 ${size / 2} ${size / 2})`}
      />
      <text
        x="50%"
        y="45%"
        dominantBaseline="central"
        textAnchor="middle"
        fill={color}
        fontSize="24"
        fontWeight="800"
      >
        {value}
      </text>
      <text
        x="50%"
        y="68%"
        dominantBaseline="central"
        textAnchor="middle"
        fill="#94A3B8"
        fontSize="10"
        fontWeight="600"
      >
        / {max}
      </text>
    </svg>
  );
}

/* ── Metric Bar Helper ─────────────────────────────────────── */
function MetricBar({ label, value, colorClass = 'from-primary-600 to-accent-cyan' }) {
  const pct = Math.round((value || 0) * 100);

  return (
    <div className="space-y-1.5">
      <div className="flex justify-between text-xs font-semibold">
        <span className="text-slate-300">{label}</span>
        <span className="text-white font-mono">{pct}%</span>
      </div>
      <div className="h-2 bg-white/5 rounded-full overflow-hidden">
        <div
          className={`h-full bg-gradient-to-r ${colorClass} rounded-full transition-all duration-700`}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}

export default function InterviewEvaluationPage() {
  const { interviewId } = useParams();
  const navigate = useNavigate();

  const [evalData, setEvalData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [downloading, setDownloading] = useState(false);

  const contentRef = useRef();

  useEffect(() => {
    (async () => {
      try {
        const { data } = await api.get(`/interviews/${interviewId}/evaluation`);
        setEvalData(data);
      } catch (err) {
        if (err?.response?.status === 404)
          setError('Evaluation not found. Please complete all questions first.');
        else if (err?.response?.status === 401)
          navigate('/login');
        else
          setError('Failed to load evaluation. Please try again.');
      } finally {
        setLoading(false);
      }
    })();
  }, [interviewId, navigate]);

  const handleDownloadPdf = () => {
    if (!contentRef.current) return;
    setDownloading(true);

    html2canvas(contentRef.current, { scale: 2, backgroundColor: '#070A12' })
      .then((canvas) => {
        const imgData = canvas.toDataURL('image/png');
        const pdf = new jsPDF('p', 'pt', 'a4');
        const imgProps = pdf.getImageProperties(imgData);
        const pdfWidth = pdf.internal.pageSize.getWidth();
        const pdfHeight = (imgProps.height * pdfWidth) / imgProps.width;
        pdf.addImage(imgData, 'PNG', 0, 0, pdfWidth, pdfHeight);
        pdf.save(`interview_evaluation_${new Date().toISOString().split('T')[0]}.pdf`);
      })
      .finally(() => setDownloading(false));
  };

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[50vh] space-y-4">
        <div className="w-12 h-12 rounded-full border-2 border-primary-500/30 border-t-primary-500 animate-spin" />
        <p className="text-slate-400 text-sm">Compiling multi-metric AI evaluation report...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="max-w-xl mx-auto mt-12 text-center space-y-4">
        <GlassCard className="space-y-4 p-8">
          <div className="w-14 h-14 rounded-2xl bg-rose-500/10 border border-rose-500/20 text-rose-400 flex items-center justify-center mx-auto">
            <IconArrowLeft className="w-6 h-6" />
          </div>
          <h2 className="text-xl font-bold text-white">Evaluation Unavailable</h2>
          <p className="text-slate-400 text-xs">{error}</p>
          <Button onClick={() => navigate('/dashboard')} variant="primary">
            Return to Dashboard
          </Button>
        </GlassCard>
      </div>
    );
  }

  
  
  const d = evalData;
  const scoreColor =
    d.overall_score >= 7
      ? 'text-accent-emerald'
      : d.overall_score >= 4
      ? 'text-amber-400'
      : 'text-rose-400';

  return (
    <div className="max-w-4xl mx-auto space-y-8 pb-16">
      {/* Top Header Actions */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <button
          onClick={() => navigate('/dashboard')}
          className="inline-flex items-center gap-2 text-xs font-semibold text-slate-400 hover:text-white transition-colors group"
        >
          <IconArrowLeft className="w-4 h-4 group-hover:-translate-x-1 transition-transform" />
          <span>Back to Dashboard</span>
        </button>

        <div className="flex flex-wrap gap-3">
          <Button
            onClick={handleDownloadPdf}
            loading={downloading}
            icon={IconDownload}
            variant="cyan"
            size="sm"
          >
            Export PDF Report
          </Button>
          <Button
            onClick={() => navigate('/interview/setup')}
            icon={IconRefresh}
            variant="primary"
            size="sm"
            className="shadow-glow-primary"
          >
            Start New Session
          </Button>
        </div>
      </div>

      {/* Main Printable Content Container */}
      <div ref={contentRef} className="space-y-8 p-1">
        {/* Celebration Header Card */}
        <GlassCard className="text-center space-y-4 p-8 bg-gradient-to-b from-primary-600/10 via-transparent to-transparent border-primary-500/30">
          <div className="w-16 h-16 rounded-2xl bg-gradient-to-tr from-primary-600 to-accent-cyan flex items-center justify-center mx-auto text-white shadow-glow-primary">
            <IconCheck className="w-8 h-8" />
          </div>
          <div>
            <h1 className="text-3xl font-extrabold tracking-tight text-white">Interview Complete!</h1>
            <p className="text-sm text-slate-400 mt-1 font-medium">
              {d.job_role} · {d.interview_type} Domain · {d.difficulty} Difficulty
            </p>
            <p className="text-xs text-slate-500 font-mono mt-1">
              Answered {d.answered_count} of {d.question_count} questions
            </p>
          </div>
        </GlassCard>

        {/* Overall Score Ring & Dimensional Breakdown */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <GlassCard className="flex flex-col items-center justify-center space-y-3 text-center p-8">
            <ScoreRing value={d.overall_score} />
            <div>
              <p className={`text-2xl font-extrabold ${scoreColor}`}>
                {d.overall_score} / 10
              </p>
              <p className="text-xs uppercase font-bold tracking-wider text-slate-400 mt-0.5">
                Overall AI Score
              </p>
            </div>
          </GlassCard>

          <GlassCard className="md:col-span-2 space-y-4 p-6">
            <h3 className="text-sm font-bold text-white uppercase tracking-wider">
              Dimensional Evaluation Breakdown
            </h3>
            <div className="space-y-3.5 pt-1">
              <MetricBar
                label="Answer Correctness"
                value={d.overall_correctness}
                colorClass="from-accent-emerald to-teal-400"
              />
              <MetricBar
                label="Role Relevance"
                value={d.overall_relevance}
                colorClass="from-amber-400 to-orange-500"
              />
              <MetricBar
                label="Technical Depth"
                value={d.overall_technical_depth}
                colorClass="from-primary-600 to-indigo-400"
              />
              <MetricBar
                label="Communication Quality"
                value={d.overall_communication_quality}
                colorClass="from-accent-cyan to-blue-500"
              />
            </div>
          </GlassCard>
        </div>

        {/* Executive Feedback summary */}
        <GlassCard className="space-y-3 p-6">
          <h3 className="text-sm font-bold text-white uppercase tracking-wider flex items-center gap-2">
            <IconSparkles className="w-4 h-4 text-accent-cyan" />
            <span>AI Executive Feedback</span>
          </h3>
          <p className="text-xs text-slate-300 leading-relaxed">{d.feedback}</p>
        </GlassCard>

        {/* Strengths & Weaknesses */}
        {(d.strengths?.length > 0 || d.weaknesses?.length > 0) && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {d.strengths?.length > 0 && (
              <GlassCard className="space-y-3 p-6 border-emerald-500/20 bg-emerald-500/5">
                <h3 className="text-xs font-bold text-accent-emerald uppercase tracking-wider flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full bg-accent-emerald" />
                  Key Strengths Observed
                </h3>
                <ul className="space-y-2 text-xs text-slate-300">
                  {d.strengths.map((str, idx) => (
                    <li key={idx} className="flex items-start gap-2">
                      <span className="text-accent-emerald font-bold">•</span>
                      <span>{str}</span>
                    </li>
                  ))}
                </ul>
              </GlassCard>
            )}

            {d.weaknesses?.length > 0 && (
              <GlassCard className="space-y-3 p-6 border-amber-500/20 bg-amber-500/5">
                <h3 className="text-xs font-bold text-amber-400 uppercase tracking-wider flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full bg-amber-400" />
                  Target Areas for Growth
                </h3>
                <ul className="space-y-2 text-xs text-slate-300">
                  {d.weaknesses.map((wk, idx) => (
                    <li key={idx} className="flex items-start gap-2">
                      <span className="text-amber-400 font-bold">•</span>
                      <span>{wk}</span>
                    </li>
                  ))}
                </ul>
              </GlassCard>
            )}
          </div>
        )}

        {/* Per-Question Breakdown List */}
        {d.per_question_evaluations?.length > 0 && (
          <GlassCard className="space-y-4 p-6">
            <h3 className="text-sm font-bold text-white uppercase tracking-wider">
              Per-Question Performance Log
            </h3>
            <div className="space-y-3">
              {d.per_question_evaluations.map((q, idx) => {
                const qScoreColor =
                  q.score >= 7
                    ? 'text-accent-emerald'
                    : q.score >= 4
                    ? 'text-amber-400'
                    : 'text-rose-400';

                return (
                  <div
                    key={idx}
                    className="p-4 rounded-xl glass-panel flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-white/[0.06]"
                  >
                    <div className="space-y-1 min-w-0 flex-1">
                      <div className="flex items-center gap-2">
                        <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider bg-primary-600/20 text-primary-300">
                          Q#{idx + 1}
                        </span>
                      </div>
                      <p className="text-xs text-slate-300 font-medium">{q.feedback}</p>
                    </div>

                    <div className="text-right flex-shrink-0">
                      <span className={`text-base font-extrabold ${qScoreColor}`}>
                        {q.score} / 10
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          </GlassCard>
        )}
      </div>
    </div>

  );
}
