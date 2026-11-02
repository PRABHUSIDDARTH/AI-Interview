import React, { useState, useEffect, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import api, { fetchAnalytics, fetchAICoach, fetchCoachSummary, askCoachChat } from '../services/api';
import { ResponsiveContainer, LineChart, Line, CartesianGrid, XAxis, YAxis, Tooltip } from 'recharts';
import { StatusBadge, DifficultyBadge } from '../components/Badge';
import GlassCard from '../components/GlassCard';
import Button from '../components/Button';
import { DashboardSkeleton } from '../components/Skeleton';
import {
  IconInterview,
  IconAnalytics,
  IconTrendingUp,
  IconPlus,
  IconCheck,
  IconSparkles,
  IconArrowRight,
  IconChat,
  IconBrain,
} from '../components/Icons';

/* ── Metric Card Helper Component ─────────────────────── */
function MetricCard({ title, value, subtitle, icon: Icon, accent = 'primary' }) {
  const accentGlow = {
    primary: 'border-primary-500/20 text-primary-400 bg-primary-500/10',
    cyan: 'border-accent-cyan/20 text-accent-cyan bg-accent-cyan/10',
    emerald: 'border-accent-emerald/20 text-accent-emerald bg-accent-emerald/10',
    purple: 'border-accent-purple/20 text-accent-purple bg-accent-purple/10',
  }[accent] || 'border-primary-500/20 text-primary-400 bg-primary-500/10';

  return (
    <GlassCard className="flex flex-col justify-between space-y-4">
      <div className="flex items-center justify-between">
        <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">{title}</span>
        {Icon && (
          <div className={`p-2.5 rounded-xl border ${accentGlow}`}>
            <Icon className="w-5 h-5" />
          </div>
        )}
      </div>
      <div>
        <div className="text-3xl font-extrabold text-white tracking-tight">{value}</div>
        {subtitle && <p className="text-xs text-slate-400 mt-1">{subtitle}</p>}
      </div>
    </GlassCard>
  );
}

/* ── AI Coach Chat Modal / Drawer Component ────────────── */
function AICoachChatDrawer({ isOpen, onClose, coachData, onStartPractice }) {
  const [messages, setMessages] = useState([
    {
      role: 'assistant',
      content:
        coachData?.summary ||
        "Hi! I'm your personalized AI Interview Coach. Ask me about your weaknesses, why certain topics were flagged, or request a targeted practice question!",
    },
  ]);
  const [input, setInput] = useState('');
  const [sending, setSending] = useState(false);
  const [practiceQuestion, setPracticeQuestion] = useState(null);

  if (!isOpen) return null;

  const handleSend = async (userMsg) => {
    const text = (userMsg || input).trim();
    if (!text || sending) return;

    setInput('');
    const newHistory = [...messages, { role: 'user', content: text }];
    setMessages(newHistory);
    setSending(true);

    try {
      const { data } = await askCoachChat(text, newHistory);
      setMessages((prev) => [...prev, { role: 'assistant', content: data.response }]);
      if (data.practice_question) {
        setPracticeQuestion(data.practice_question);
      }
    } catch {
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content:
            "I'm focusing on your actual interview history. Based on your records, practicing your weakest topic is the best next step.",
        },
      ]);
    } finally {
      setSending(false);
    }
  };

  const handleQuickPrompt = (prompt) => {
    handleSend(prompt);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-md animate-fade-in">
      <div className="w-full max-w-2xl bg-slate-900 border border-primary-500/30 rounded-3xl shadow-2xl overflow-hidden flex flex-col max-h-[85vh]">
        {/* Header */}
        <div className="p-5 bg-gradient-to-r from-primary-950/60 via-slate-900 to-slate-900 border-b border-white/10 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-primary-500/20 border border-primary-500/30 text-accent-cyan">
              <IconBrain className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-base font-extrabold text-white flex items-center gap-2">
                Conversational AI Coach
              </h3>
              <p className="text-xs text-slate-400">Grounded strictly in your interview history</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-white p-2 rounded-lg hover:bg-white/5 transition-colors"
          >
            ✕
          </button>
        </div>

        {/* Message Thread */}
        <div className="flex-1 overflow-y-auto p-5 space-y-4 text-xs">
          {messages.map((m, idx) => (
            <div
              key={idx}
              className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              <div
                className={`max-w-[85%] rounded-2xl p-4 whitespace-pre-line leading-relaxed ${
                  m.role === 'user'
                    ? 'bg-primary-600 text-white rounded-br-none shadow-glow-primary'
                    : 'glass-panel text-slate-200 border-white/10 rounded-bl-none'
                }`}
              >
                {m.content}
              </div>
            </div>
          ))}

          {sending && (
            <div className="flex justify-start">
              <div className="glass-panel text-slate-400 rounded-2xl p-3 border-white/10 flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-accent-cyan animate-ping" />
                <span>Coach is analyzing your history...</span>
              </div>
            </div>
          )}

          {practiceQuestion && (
            <div className="p-4 rounded-2xl bg-primary-950/40 border border-accent-cyan/30 space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-[11px] font-bold uppercase tracking-wider text-accent-cyan">
                  🎯 Targeted Practice Question
                </span>
                <span className="text-[10px] text-slate-400">Non-duplicate from past sessions</span>
              </div>
              <p className="text-xs text-white font-medium italic">"{practiceQuestion}"</p>
              <Button
                variant="primary"
                size="sm"
                onClick={() => {
                  onClose();
                  onStartPractice(coachData);
                }}
                icon={IconArrowRight}
                iconPosition="right"
                className="w-full shadow-glow-primary"
              >
                Start Recommended Practice Session
              </Button>
            </div>
          )}
        </div>

        {/* Quick Prompts */}
        <div className="p-3 bg-white/[0.02] border-t border-white/5 flex flex-wrap gap-2">
          <button
            type="button"
            onClick={() => handleQuickPrompt('What should I improve?')}
            className="px-3 py-1.5 rounded-lg text-[11px] font-semibold bg-white/5 hover:bg-white/10 text-slate-300 border border-white/10 transition-colors"
          >
            What should I improve?
          </button>
          <button
            type="button"
            onClick={() => handleQuickPrompt('Why?')}
            className="px-3 py-1.5 rounded-lg text-[11px] font-semibold bg-white/5 hover:bg-white/10 text-slate-300 border border-white/10 transition-colors"
          >
            Why?
          </button>
          <button
            type="button"
            onClick={() => handleQuickPrompt('Give me a practice question')}
            className="px-3 py-1.5 rounded-lg text-[11px] font-semibold bg-accent-cyan/10 hover:bg-accent-cyan/20 text-accent-cyan border border-accent-cyan/20 transition-colors"
          >
            Give me a practice question
          </button>
        </div>

        {/* Input Form */}
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleSend();
          }}
          className="p-4 bg-slate-900 border-t border-white/10 flex items-center gap-3"
        >
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask your AI Coach anything about your performance..."
            className="flex-1 bg-white/5 border border-white/10 rounded-xl px-4 py-2.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-primary-500"
          />
          <Button type="submit" variant="primary" disabled={!input.trim() || sending} size="sm">
            Send
          </Button>
        </form>
      </div>
    </div>
  );
}

/* ── AI Coach Card Helper Component ────────────────────── */
function AICoachCard({ coachData, loadingCoach, errorCoach, onStartPractice }) {
  const [chatOpen, setChatOpen] = useState(false);

  const weakTopics = coachData?.weak_topics || [];
  const strongTopics = coachData?.strong_topics || [];
  const strongestSkill = coachData?.strongest_skill;
  const weakestSkill = coachData?.weakest_skill;
  const trend = coachData?.improvement_trend;
  const recInterview = coachData?.recommended_interview;

  // Group topics by parent skill for Section 17 topic breakdown (unconditionally at top)
  const topicsBySkill = useMemo(() => {
    if (!coachData) return {};
    const all =
      coachData.all_topics && coachData.all_topics.length > 0
        ? coachData.all_topics
        : [...weakTopics, ...strongTopics];
    const grouped = {};
    all.forEach((t) => {
      const s = t.skill || 'Technical';
      if (!grouped[s]) grouped[s] = [];
      if (!grouped[s].some((x) => x.topic === t.topic)) {
        grouped[s].push(t);
      }
    });
    return grouped;
  }, [coachData, weakTopics, strongTopics]);

  if (loadingCoach) {
    return (
      <GlassCard className="p-6 space-y-4 animate-pulse">
        <div className="flex items-center justify-between">
          <div className="h-6 w-48 bg-white/10 rounded-md" />
          <div className="h-5 w-24 bg-white/10 rounded-full" />
        </div>
        <div className="h-4 w-3/4 bg-white/10 rounded-md" />
        <div className="h-24 w-full bg-white/5 rounded-xl" />
      </GlassCard>
    );
  }

  if (errorCoach) {
    return (
      <GlassCard className="p-6 border-amber-500/30">
        <div className="flex items-center gap-3 text-amber-400">
          <IconSparkles className="w-5 h-5" />
          <p className="text-sm font-semibold">AI Coach is temporarily unavailable.</p>
        </div>
      </GlassCard>
    );
  }

  if (!coachData) return null;

  // Trend direction styling
  const trendBadge =
    {
      improving: { text: '↑ Improving', bg: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' },
      declining: { text: '↓ Needs Attention', bg: 'bg-rose-500/10 text-rose-400 border-rose-500/20' },
      consistent: { text: '↔ Consistent', bg: 'bg-accent-cyan/10 text-accent-cyan border-accent-cyan/20' },
      baseline: { text: '● Baseline Set', bg: 'bg-primary-500/10 text-primary-400 border-primary-500/20' },
    }[trend?.direction] || { text: '● Baseline Set', bg: 'bg-primary-500/10 text-primary-400 border-primary-500/20' };

  return (
    <GlassCard className="p-6 md:p-8 relative overflow-hidden border border-primary-500/30 bg-gradient-to-br from-slate-900/95 via-primary-950/25 to-slate-900/95 shadow-2xl">
      <div className="absolute -top-24 -right-24 w-80 h-80 bg-primary-600/15 rounded-full blur-3xl pointer-events-none" />
      <div className="absolute -bottom-24 -left-24 w-80 h-80 bg-accent-cyan/10 rounded-full blur-3xl pointer-events-none" />

      <div className="relative space-y-6">
        {/* Card Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-white/[0.06] pb-4">
          <div className="flex items-center gap-3">
            <div className="p-3 rounded-2xl bg-gradient-to-br from-primary-500/20 to-accent-cyan/20 border border-primary-500/30 text-accent-cyan shadow-glow-primary">
              <IconSparkles className="w-6 h-6" />
            </div>
            <div>
              <h2 className="text-xl font-extrabold text-white tracking-tight flex items-center gap-2">
                AI INTERVIEW COACH 🧠
              </h2>
              <p className="text-xs text-slate-400">
                Personalized guidance grounded in your authenticated interview performance & technical sources
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2 self-start sm:self-auto">
            {trend && (
              <span className={`px-3 py-1 text-[11px] font-bold tracking-wider rounded-full border ${trendBadge.bg}`}>
                {trendBadge.text}
              </span>
            )}
            <button
              onClick={() => setChatOpen(true)}
              className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-[11px] font-bold bg-primary-500/20 hover:bg-primary-500/30 text-accent-cyan border border-primary-500/40 shadow-glow-primary transition-all"
            >
              <IconChat className="w-3.5 h-3.5" />
              <span>Ask Coach</span>
            </button>
          </div>
        </div>

        {/* Cold Start State */}
        {!coachData.has_enough_data ? (
          <div className="p-5 rounded-2xl bg-white/[0.03] border border-white/[0.08] space-y-4">
            <p className="text-sm text-slate-300 leading-relaxed">
              {coachData.summary ||
                "Welcome! Complete your first interview session to establish baseline metrics and unlock personalized AI coaching."}
            </p>
            <Button
              onClick={() => onStartPractice()}
              icon={IconArrowRight}
              iconPosition="right"
              variant="primary"
              className="shadow-glow-primary"
            >
              Start First Interview to Unlock Coaching
            </Button>
          </div>
        ) : (
          /* Grounded Personalized Guidance State */
          <div className="space-y-6">
            {/* Quick Greeting & Summary */}
            <div className="p-4 rounded-xl bg-white/[0.02] border border-white/[0.06] text-xs text-slate-200 leading-relaxed font-normal">
              {coachData.summary}
            </div>

            {/* Performance Analysis Strip (Overall, Strongest, Weakest, Recent, Trend) */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              <div className="p-3.5 rounded-xl bg-white/[0.03] border border-white/[0.06]">
                <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Overall Score</span>
                <div className="text-xl font-extrabold text-white mt-0.5">{coachData.overall_score || '--'}/10</div>
                <span className="text-[10px] text-slate-400">All sessions avg</span>
              </div>
              <div className="p-3.5 rounded-xl bg-emerald-500/10 border border-emerald-500/20">
                <span className="text-[10px] font-bold uppercase tracking-wider text-emerald-400">Strongest Skill</span>
                <div className="text-xl font-extrabold text-white mt-0.5">
                  {strongestSkill ? `${strongestSkill.skill}` : '--'}
                </div>
                <span className="text-[10px] text-emerald-300/80">{strongestSkill ? `${strongestSkill.score}/10` : 'Solid'}</span>
              </div>
              <div className="p-3.5 rounded-xl bg-amber-500/10 border border-amber-500/20">
                <span className="text-[10px] font-bold uppercase tracking-wider text-amber-400">Needs Improvement</span>
                {weakTopics.length > 0 ? (
                  <div className="mt-1 space-y-1">
                    {weakTopics.slice(0, 2).map((wt, i) => (
                      <div key={i} className="flex items-center justify-between text-xs">
                        <span className="font-bold text-white truncate mr-1">{wt.topic}</span>
                        <span className="text-amber-300 font-extrabold whitespace-nowrap">{wt.score}/10</span>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="mt-1">
                    <div className="text-sm font-extrabold text-white">{weakestSkill ? weakestSkill.skill : 'None detected'}</div>
                    <span className="text-[10px] text-amber-300/80">{weakestSkill ? `${weakestSkill.score}/10` : 'Solid performance'}</span>
                  </div>
                )}
              </div>
              <div className="p-3.5 rounded-xl bg-accent-cyan/10 border border-accent-cyan/20">
                <span className="text-[10px] font-bold uppercase tracking-wider text-accent-cyan">Recent Score</span>
                <div className="text-xl font-extrabold text-white mt-0.5">{coachData.recent_score || '--'}/10</div>
                <span className="text-[10px] text-slate-400">{trend?.description?.slice(0, 30) || 'Latest performance'}...</span>
              </div>
            </div>

            {/* Two Column Grid: Topic Breakdown & Recommended Next Step */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
              {/* Left Column: Topics Breakdown & Pitfalls */}
              <div className="space-y-4">
                {/* Topic Breakdown Card */}
                <div className="p-4 rounded-xl bg-white/[0.03] border border-white/[0.06] space-y-3">
                  <div className="flex items-center justify-between">
                    <h4 className="text-xs font-bold uppercase tracking-wider text-slate-300">
                      Topic Performance Breakdown
                    </h4>
                    <span className="text-[10px] text-slate-400">Evidence-based scores</span>
                  </div>

                  <div className="space-y-3">
                    {Object.keys(topicsBySkill).length === 0 ? (
                      <p className="text-xs text-slate-400">Complete more sessions to populate detailed topic breakdown.</p>
                    ) : (
                      Object.entries(topicsBySkill).map(([skillName, topics]) => (
                        <div key={skillName} className="space-y-2 pt-2 first:pt-0 border-t first:border-t-0 border-white/5">
                          <div className="flex items-center justify-between">
                            <span className="text-xs font-bold text-accent-cyan uppercase tracking-wider">{skillName}</span>
                            <span className="text-[10px] text-slate-400">{topics.length} topics</span>
                          </div>
                          <div className="space-y-2">
                            {topics.map((t, idx) => {
                              const isWeak = t.status === 'weak' || t.score < 6.5;
                              const isStrong = t.status === 'strong' || t.score >= 7.5;
                              const colorClass = isWeak
                                ? 'text-amber-400'
                                : isStrong
                                ? 'text-emerald-400'
                                : 'text-accent-cyan';
                              const barClass = isWeak
                                ? 'bg-amber-400'
                                : isStrong
                                ? 'bg-emerald-400'
                                : 'bg-accent-cyan';

                              return (
                                <div key={idx} className="space-y-1">
                                  <div className="flex items-center justify-between text-xs">
                                    <span className="font-semibold text-slate-200">{t.topic}</span>
                                    <span className={`font-bold ${colorClass}`}>{t.score}/10</span>
                                  </div>
                                  <div className="w-full h-1.5 bg-white/10 rounded-full overflow-hidden">
                                    <div
                                      className={`h-full ${barClass} rounded-full transition-all duration-500`}
                                      style={{ width: `${Math.min(100, (t.score / 10) * 100)}%` }}
                                    />
                                  </div>
                                </div>
                              );
                            })}
                          </div>
                        </div>
                      ))
                    )}
                  </div>
                </div>

                {/* Common Pitfalls / Focus needed */}
                {weakTopics[0]?.common_pitfalls && weakTopics[0].common_pitfalls.length > 0 && (
                  <div className="p-4 rounded-xl bg-amber-500/10 border border-amber-500/20 space-y-2">
                    <span className="text-[11px] font-bold uppercase tracking-wider text-amber-400">
                      ⚠ Frequently Missed Pitfalls in {weakTopics[0].topic}
                    </span>
                    <ul className="text-xs text-amber-200/90 space-y-1 list-disc list-inside">
                      {weakTopics[0].common_pitfalls.slice(0, 3).map((pf, i) => (
                        <li key={i} className="line-clamp-1">{pf}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>

              {/* Right Column: Recommended Next Step & Start Button */}
              <div className="space-y-4 flex flex-col justify-between">
                <div className="p-5 rounded-2xl bg-gradient-to-br from-primary-950/40 via-slate-900 to-slate-900 border border-primary-500/30 space-y-3.5">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold uppercase tracking-wider text-accent-cyan flex items-center gap-1.5">
                      <IconSparkles className="w-4 h-4 text-accent-cyan" />
                      Recommended Next Step
                    </span>
                    <span className="px-2 py-0.5 text-[10px] font-bold bg-primary-500/20 text-primary-300 rounded border border-primary-500/30">
                      {recInterview?.difficulty || 'Medium'}
                    </span>
                  </div>

                  <div>
                    <h3 className="text-base font-extrabold text-white">
                      {recInterview?.title || `Practice ${weakTopics[0]?.topic || 'Technical Fundamentals'}`}
                    </h3>
                    <p className="text-xs text-slate-300 mt-1">
                      {recInterview?.reason || coachData.next_action}
                    </p>
                  </div>

                  {/* Actionable recommendations */}
                  {coachData.recommended_actions && coachData.recommended_actions.length > 0 && (
                    <div className="space-y-1.5 pt-2 border-t border-white/10">
                      <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Action Plan:</span>
                      <ol className="text-xs text-slate-300 space-y-1 list-decimal list-inside">
                        {coachData.recommended_actions.slice(0, 3).map((act, i) => (
                          <li key={i} className="line-clamp-1">{act}</li>
                        ))}
                      </ol>
                    </div>
                  )}

                  {/* Actions Buttons */}
                  <div className="pt-3 flex flex-col sm:flex-row items-center gap-3">
                    <Button
                      onClick={() => onStartPractice(coachData)}
                      icon={IconArrowRight}
                      iconPosition="right"
                      variant="primary"
                      className="w-full shadow-glow-primary py-3 text-xs"
                    >
                      Start Recommended Interview
                    </Button>
                    <button
                      type="button"
                      onClick={() => setChatOpen(true)}
                      className="w-full sm:w-auto px-4 py-3 rounded-xl text-xs font-bold text-slate-300 hover:text-white bg-white/5 hover:bg-white/10 border border-white/10 transition-all flex items-center justify-center gap-2"
                    >
                      <IconChat className="w-4 h-4" />
                      <span>Chat with Coach</span>
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Embedded Conversational AI Coach Drawer */}
      <AICoachChatDrawer
        isOpen={chatOpen}
        onClose={() => setChatOpen(false)}
        coachData={coachData}
        onStartPractice={onStartPractice}
      />
    </GlassCard>
  );
}

export default function DashboardPage() {
  const navigate = useNavigate();

  const [interviews, setInterviews] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [analytics, setAnalytics] = useState(null);
  const [loadingAnalytics, setLoadingAnalytics] = useState(true);
  const [errorAnalytics, setErrorAnalytics] = useState('');

  const [coachData, setCoachData] = useState(null);
  const [loadingCoach, setLoadingCoach] = useState(true);
  const [errorCoach, setErrorCoach] = useState('');

  /* ── Fetch data on mount ───────────────────────────── */
  useEffect(() => {
    const fetchData = async () => {
      try {
        const { data } = await api.get('/interviews/');
        setInterviews(data.interviews || []);
      } catch (err) {
        if (err?.response?.status === 401) {
          navigate('/login');
        } else {
          setError('Failed to load your interview sessions.');
        }
      } finally {
        setLoading(false);
      }

      try {
        const { data: analyticsData } = await fetchAnalytics();
        setAnalytics(analyticsData);
      } catch (err) {
        if (err?.response?.status === 401) {
          navigate('/login');
        } else {
          setErrorAnalytics('Failed to load analytics data.');
        }
      } finally {
        setLoadingAnalytics(false);
      }

      try {
        const { data: coachRes } = await fetchCoachSummary();
        setCoachData(coachRes);
      } catch {
        // Fallback to legacy coach endpoint if summary endpoint fails
        try {
          const { data: legacyRes } = await fetchAICoach();
          setCoachData(legacyRes);
        } catch (err) {
          if (err?.response?.status === 401) {
            navigate('/login');
          } else {
            setErrorCoach('Failed to load AI Coach guidance.');
          }
        }
      } finally {
        setLoadingCoach(false);
      }
    };

    fetchData();
  }, [navigate]);

  /* ── Derived metrics ───────────────────────────────── */
  const totalInterviews = interviews.length;
  const completedInterviews = interviews.filter((s) => s.status === 'completed');
  const inProgressCount = interviews.filter((s) => s.status === 'in_progress').length;
  const completionRate =
    totalInterviews > 0
      ? `${Math.round((completedInterviews.length / totalInterviews) * 100)}%`
      : '--';

  /* ── Dynamic greeting ──────────────────────────────── */
  const getGreeting = () => {
    const hour = new Date().getHours();
    if (hour < 12) return 'Good morning 👋';
    if (hour < 18) return 'Good afternoon 👋';
    return 'Good evening 👋';
  };

  /* ── Row click handler ────────────────────────────── */
  const handleRowClick = (session) => {
    if (session.status === 'completed') {
      navigate(`/interview/${session.id}/evaluation`);
    } else {
      navigate(`/interview/${session.id}`);
    }
  };

  /* ── Quick start interview navigation ─────────────── */
  const handleQuickStart = (type) => {
    navigate('/interview/setup', { state: { interview_type: type } });
  };

  const handleStartRecommendedPractice = (coachInfo) => {
    const rec = coachInfo?.recommended_interview;
    if (rec) {
      navigate('/interview/setup', {
        state: {
          interview_type: rec.interview_type || 'Technical',
          job_role: rec.job_role || 'Software Developer',
          experience_level: rec.experience_level || 'Intermediate',
          difficulty: rec.difficulty || 'Medium',
          selected_skills: rec.selected_skills || [],
          focus_topic: rec.focus_topic || '',
          is_recommended: true,
        },
      });
    } else {
      navigate('/interview/setup');
    }
  };

  if (loading || loadingAnalytics) {
    return <DashboardSkeleton />;
  }

  return (
    <div className="space-y-10 pb-12">
      {/* ── Header Greeting ──────────────────────────────── */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-extrabold tracking-tight text-white">{getGreeting()}</h1>
          <p className="text-sm text-slate-400 mt-1">
            Track your interview performance, analyze key metrics, and sharpen your skills.
          </p>
        </div>
        <Button
          id="btn-new-interview-top"
          onClick={() => navigate('/interview/setup')}
          icon={IconPlus}
          variant="primary"
          className="shadow-glow-primary self-start md:self-auto"
        >
          Start New Interview
        </Button>
      </div>

      {/* ── Top Metric Cards ─────────────────────────────── */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard
          title="Overall Score"
          value={analytics?.average_score !== null && analytics?.average_score !== undefined ? `${analytics.average_score} / 10` : '--'}
          subtitle={analytics?.completed_interviews ? `Based on ${analytics.completed_interviews} completed sessions` : 'No evaluations yet'}
          icon={IconSparkles}
          accent="primary"
        />
        <MetricCard
          title="Completed Sessions"
          value={completedInterviews.length}
          subtitle={`Total created: ${totalInterviews}`}
          icon={IconCheck}
          accent="emerald"
        />
        <MetricCard
          title="Completion Rate"
          value={completionRate}
          subtitle={`${inProgressCount} currently in progress`}
          icon={IconTrendingUp}
          accent="cyan"
        />
        <MetricCard
          title="Best Score"
          value={analytics?.best_score !== null && analytics?.best_score !== undefined ? `${analytics.best_score} / 10` : '--'}
          subtitle={`Latest score: ${analytics?.latest_score !== null && analytics?.latest_score !== undefined ? analytics.latest_score : '--'}`}
          icon={IconAnalytics}
          accent="purple"
        />
      </div>

      {/* ── AI Coach Section ─────────────────────────────── */}
      <AICoachCard
        coachData={coachData}
        loadingCoach={loadingCoach}
        errorCoach={errorCoach}
        onStartPractice={handleStartRecommendedPractice}
      />

      {/* ── Quick Start Section ──────────────────────────── */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-bold tracking-tight text-white">Start a New Interview</h2>
          <span className="text-xs text-slate-400">Choose a simulation mode</span>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <GlassCard
            interactive
            onClick={() => handleQuickStart('Technical')}
            className="group flex flex-col justify-between space-y-3"
          >
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-accent-cyan uppercase tracking-wider">Technical</span>
              <IconArrowRight className="w-4 h-4 text-slate-400 group-hover:text-accent-cyan group-hover:translate-x-1 transition-all" />
            </div>
            <div>
              <h3 className="text-base font-bold text-white group-hover:text-accent-cyan transition-colors">Technical Mock</h3>
              <p className="text-xs text-slate-400 mt-1">Algorithms, system design, coding & backend architecture.</p>
            </div>
          </GlassCard>

          <GlassCard
            interactive
            onClick={() => handleQuickStart('HR')}
            className="group flex flex-col justify-between space-y-3"
          >
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-accent-purple uppercase tracking-wider">HR & Cultural</span>
              <IconArrowRight className="w-4 h-4 text-slate-400 group-hover:text-accent-purple group-hover:translate-x-1 transition-all" />
            </div>
            <div>
              <h3 className="text-base font-bold text-white group-hover:text-accent-purple transition-colors">HR Screener</h3>
              <p className="text-xs text-slate-400 mt-1">Background, career goals, culture fit & expectations.</p>
            </div>
          </GlassCard>

          <GlassCard
            interactive
            onClick={() => handleQuickStart('Behavioral')}
            className="group flex flex-col justify-between space-y-3"
          >
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-accent-emerald uppercase tracking-wider">Behavioral</span>
              <IconArrowRight className="w-4 h-4 text-slate-400 group-hover:text-accent-emerald group-hover:translate-x-1 transition-all" />
            </div>
            <div>
              <h3 className="text-base font-bold text-white group-hover:text-accent-emerald transition-colors">STAR Method</h3>
              <p className="text-xs text-slate-400 mt-1">Leadership, conflict resolution & project management.</p>
            </div>
          </GlassCard>

          <GlassCard
            interactive
            onClick={() => handleQuickStart('Mixed')}
            className="group flex flex-col justify-between space-y-3"
          >
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-primary-400 uppercase tracking-wider">Comprehensive</span>
              <IconArrowRight className="w-4 h-4 text-slate-400 group-hover:text-primary-400 group-hover:translate-x-1 transition-all" />
            </div>
            <div>
              <h3 className="text-base font-bold text-white group-hover:text-primary-400 transition-colors">Full Mixed Loop</h3>
              <p className="text-xs text-slate-400 mt-1">Combination of technical depth and behavioral response.</p>
            </div>
          </GlassCard>
        </div>
      </div>

      {/* ── Performance & Chart Section ──────────────────── */}
      {analytics && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Score Trend Chart */}
            <GlassCard className="lg:col-span-2 space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-base font-bold text-white">Score Performance Trend</h3>
                  <p className="text-xs text-slate-400">Historical evaluation scores over time</p>
                </div>
                <span className="text-xs text-primary-400 font-semibold px-2.5 py-1 bg-primary-600/10 border border-primary-500/20 rounded-full">
                  Real-time AI Metrics
                </span>
              </div>
              <div className="h-64 w-full pt-2">
                {analytics.trend && analytics.trend.length > 0 ? (
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={analytics.trend}>
                      <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
                      <XAxis dataKey="date" stroke="#64748B" fontSize={11} />
                      <YAxis domain={[0, 10]} stroke="#64748B" fontSize={11} />
                      <Tooltip
                        contentStyle={{
                          backgroundColor: '#0B1020',
                          borderColor: 'rgba(255,255,255,0.1)',
                          borderRadius: '12px',
                          color: '#F8FAFC',
                        }}
                      />
                      <Line
                        type="monotone"
                        dataKey="score"
                        stroke="#6C63FF"
                        strokeWidth={3}
                        dot={{ r: 4, fill: '#22D3EE', strokeWidth: 0 }}
                        activeDot={{ r: 6, fill: '#6C63FF' }}
                      />
                    </LineChart>
                  </ResponsiveContainer>
                ) : (
                  <div className="h-full flex items-center justify-center text-xs text-slate-500">
                    Complete your first interview to generate score trends.
                  </div>
                )}
              </div>
            </GlassCard>

            {/* Performance Breakdown */}
            <GlassCard className="space-y-4">
              <h3 className="text-base font-bold text-white">Skill Breakdown</h3>
              <p className="text-xs text-slate-400">Dimension averages across all evaluations</p>

              <div className="space-y-3 pt-2">
                <div>
                  <div className="flex justify-between text-xs font-semibold mb-1">
                    <span className="text-slate-300">Technical Depth</span>
                    <span className="text-primary-400">{analytics.average_technical_depth ?? '--'} / 10</span>
                  </div>
                  <div className="h-2 w-full bg-white/5 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-gradient-to-r from-primary-600 to-indigo-400 rounded-full"
                      style={{ width: `${((analytics.average_technical_depth || 0) / 10) * 100}%` }}
                    />
                  </div>
                </div>

                <div>
                  <div className="flex justify-between text-xs font-semibold mb-1">
                    <span className="text-slate-300">Communication Quality</span>
                    <span className="text-accent-cyan">{analytics.average_communication_quality ?? '--'} / 10</span>
                  </div>
                  <div className="h-2 w-full bg-white/5 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-gradient-to-r from-accent-cyan to-blue-500 rounded-full"
                      style={{ width: `${((analytics.average_communication_quality || 0) / 10) * 100}%` }}
                    />
                  </div>
                </div>

                <div>
                  <div className="flex justify-between text-xs font-semibold mb-1">
                    <span className="text-slate-300">Answer Correctness</span>
                    <span className="text-accent-emerald">{analytics.average_correctness ?? '--'} / 10</span>
                  </div>
                  <div className="h-2 w-full bg-white/5 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-gradient-to-r from-accent-emerald to-teal-400 rounded-full"
                      style={{ width: `${((analytics.average_correctness || 0) / 10) * 100}%` }}
                    />
                  </div>
                </div>

                <div>
                  <div className="flex justify-between text-xs font-semibold mb-1">
                    <span className="text-slate-300">Role Relevance</span>
                    <span className="text-amber-400">{analytics.average_relevance ?? '--'} / 10</span>
                  </div>
                  <div className="h-2 w-full bg-white/5 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-gradient-to-r from-amber-500 to-orange-400 rounded-full"
                      style={{ width: `${((analytics.average_relevance || 0) / 10) * 100}%` }}
                    />
                  </div>
                </div>
              </div>
            </GlassCard>
          </div>

          {/* Strengths & Weaknesses Badges */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <GlassCard className="space-y-3">
              <h4 className="text-sm font-bold text-accent-emerald flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-accent-emerald" />
                Key Demonstrated Strengths
              </h4>
              <div className="flex flex-wrap gap-2 pt-1">
                {analytics.strengths && analytics.strengths.length > 0 ? (
                  analytics.strengths.slice(0, 6).map((str, idx) => (
                    <span
                      key={idx}
                      className="px-2.5 py-1 text-xs font-medium text-emerald-300 bg-emerald-500/10 border border-emerald-500/20 rounded-lg"
                    >
                      {str}
                    </span>
                  ))
                ) : (
                  <span className="text-xs text-slate-500">No strengths recorded yet.</span>
                )}
              </div>
            </GlassCard>

            <GlassCard className="space-y-3">
              <h4 className="text-sm font-bold text-amber-400 flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-amber-400" />
                Areas for Growth & Focus
              </h4>
              <div className="flex flex-wrap gap-2 pt-1">
                {analytics.weaknesses && analytics.weaknesses.length > 0 ? (
                  analytics.weaknesses.slice(0, 6).map((wk, idx) => (
                    <span
                      key={idx}
                      className="px-2.5 py-1 text-xs font-medium text-amber-300 bg-amber-500/10 border border-amber-500/20 rounded-lg"
                    >
                      {wk}
                    </span>
                  ))
                ) : (
                  <span className="text-xs text-slate-500">No growth areas recorded yet.</span>
                )}
              </div>
            </GlassCard>
          </div>
        </div>
      )}

      {/* ── Interview Sessions Table ─────────────────────── */}
      <GlassCard className="overflow-hidden p-0 border border-white/[0.08]">
        <div className="p-6 border-b border-white/[0.06] flex items-center justify-between">
          <div>
            <h3 className="text-lg font-bold text-white">Interview Sessions History</h3>
            <p className="text-xs text-slate-400">All created and completed mock sessions</p>
          </div>
          <Button
            id="btn-new-interview-table"
            onClick={() => navigate('/interview/setup')}
            icon={IconPlus}
            size="sm"
            variant="primary"
          >
            New Session
          </Button>
        </div>

        {interviews.length === 0 ? (
          /* Empty State */
          <div className="p-12 text-center space-y-4">
            <div className="w-16 h-16 rounded-2xl bg-primary-600/10 border border-primary-500/20 flex items-center justify-center mx-auto text-primary-400">
              <IconInterview className="w-8 h-8" />
            </div>
            <div className="space-y-1 max-w-sm mx-auto">
              <h4 className="text-base font-bold text-white">Your first interview is waiting</h4>
              <p className="text-xs text-slate-400">
                Create a customized mock session to practice answering questions with AI evaluation.
              </p>
            </div>
            <Button
              onClick={() => navigate('/interview/setup')}
              icon={IconArrowRight}
              iconPosition="right"
              variant="primary"
              className="shadow-glow-primary"
            >
              Start First Interview
            </Button>
          </div>
        ) : (
          /* Table */
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-white/[0.02] text-slate-400 text-[11px] font-bold uppercase tracking-wider border-b border-white/[0.06]">
                  <th className="px-6 py-3.5">Target Role</th>
                  <th className="px-6 py-3.5">Domain</th>
                  <th className="px-6 py-3.5">Difficulty</th>
                  <th className="px-6 py-3.5">Progress</th>
                  <th className="px-6 py-3.5">Status</th>
                  <th className="px-6 py-3.5">Date</th>
                  <th className="px-6 py-3.5 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/[0.04] text-slate-300 text-xs">
                {interviews.map((session) => (
                  <tr
                    key={session.id}
                    onClick={() => handleRowClick(session)}
                    className="hover:bg-white/[0.03] cursor-pointer transition-colors"
                  >
                    <td className="px-6 py-4 font-semibold text-white">{session.job_role}</td>
                    <td className="px-6 py-4 text-slate-300">{session.interview_type}</td>
                    <td className="px-6 py-4">
                      <DifficultyBadge difficulty={session.difficulty} />
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-2.5">
                        <div className="w-24 h-1.5 bg-white/5 rounded-full overflow-hidden">
                          <div
                            className="h-full bg-gradient-to-r from-primary-500 to-accent-cyan rounded-full transition-all"
                            style={{
                              width: `${session.question_count > 0 ? (session.answered_count / session.question_count) * 100 : 0}%`,
                            }}
                          />
                        </div>
                        <span className="text-[11px] font-mono text-slate-400">
                          {session.answered_count}/{session.question_count}
                        </span>
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <StatusBadge status={session.status} />
                    </td>
                    <td className="px-6 py-4 text-slate-400 font-mono text-[11px]">
                      {new Date(session.created_at).toLocaleDateString('en-US', {
                        month: 'short',
                        day: 'numeric',
                        year: 'numeric',
                      })}
                    </td>
                    <td className="px-6 py-4 text-right">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          handleRowClick(session);
                        }}
                        className="font-semibold text-primary-400 hover:text-accent-cyan transition-colors"
                      >
                        {session.status === 'completed'
                          ? 'View Results →'
                          : session.status === 'in_progress'
                          ? 'Resume →'
                          : 'Open →'}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </GlassCard>
    </div>
  );
}
