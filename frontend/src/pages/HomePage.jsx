import React from 'react';
import { Link } from 'react-router-dom';
import {
  IconSparkles,
  IconInterview,
  IconAnalytics,
  IconShield,
  IconArrowRight,
  IconMic,
  IconFilePdf,
} from '../components/Icons';
import GlassCard from '../components/GlassCard';

export default function HomePage() {
  const isAuthenticated = Boolean(localStorage.getItem('token'));

  return (
    <div className="flex flex-col items-center justify-center py-6 lg:py-12 max-w-5xl mx-auto space-y-16">
      {/* ── Hero Section ─────────────────────────────────── */}
      <div className="space-y-6 text-center max-w-3xl">
        <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full text-xs font-semibold bg-primary-600/15 text-primary-300 border border-primary-500/30 shadow-[0_0_20px_rgba(108,99,255,0.2)] animate-pulse-subtle">
          <IconSparkles className="w-4 h-4 text-accent-cyan" />
          <span>Next-Gen AI Interview Coaching & Simulation</span>
        </div>

        <h1 className="text-4xl sm:text-6xl lg:text-7xl font-extrabold tracking-tight leading-[1.1]">
          Master Your Next Interview with{' '}
          <span className="bg-gradient-to-r from-primary-400 via-indigo-300 to-accent-cyan bg-clip-text text-transparent">
            Adaptive AI
          </span>
        </h1>

        <p className="text-base sm:text-lg text-slate-400 max-w-2xl mx-auto font-normal leading-relaxed">
          Simulate rigorous mock interviews customized to your target role, experience level, and resume. Receive instantaneous, multi-metric evaluations powered by intelligent AI scoring.
        </p>

        <div className="pt-4 flex flex-wrap justify-center items-center gap-4">
          <Link
            to={isAuthenticated ? "/dashboard" : "/register"}
            id="btn-get-started"
            className="inline-flex items-center gap-2 px-8 py-3.5 text-sm sm:text-base font-semibold text-white btn-primary rounded-xl shadow-glow-primary hover:scale-[1.02] active:scale-100 transition-all"
          >
            <span>{isAuthenticated ? 'Go to Dashboard' : 'Get Started Free'}</span>
            <IconArrowRight className="w-4 h-4" />
          </Link>
          <Link
            to={isAuthenticated ? "/interview/setup" : "/login"}
            id="btn-view-demo"
            className="inline-flex items-center gap-2 px-7 py-3.5 text-sm sm:text-base font-medium text-slate-300 btn-secondary rounded-xl hover:text-white transition-all"
          >
            <span>{isAuthenticated ? 'New Interview Session' : 'Sign In'}</span>
          </Link>
        </div>
      </div>

      {/* ── Key Highlights Grid ──────────────────────────── */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 w-full pt-6">
        <GlassCard interactive className="space-y-4">
          <div className="w-12 h-12 rounded-xl bg-primary-600/20 border border-primary-500/30 flex items-center justify-center text-primary-400 shadow-glow-primary">
            <IconInterview className="w-6 h-6" />
          </div>
          <h3 className="text-lg font-bold text-white tracking-tight">Adaptive Questioning</h3>
          <p className="text-sm text-slate-400 leading-relaxed">
            Tailor sessions by role, seniority, and difficulty. Upload your PDF resume and target job description for contextualized questioning.
          </p>
        </GlassCard>

        <GlassCard interactive className="space-y-4">
          <div className="w-12 h-12 rounded-xl bg-accent-cyan/20 border border-accent-cyan/30 flex items-center justify-center text-accent-cyan shadow-glow-cyan">
            <IconMic className="w-6 h-6" />
          </div>
          <h3 className="text-lg font-bold text-white tracking-tight">Real-Time Voice Studio</h3>
          <p className="text-sm text-slate-400 leading-relaxed">
            Speak your answers naturally using browser speech-to-text with live audio feedback, or type comfortably in a distraction-free environment.
          </p>
        </GlassCard>

        <GlassCard interactive className="space-y-4">
          <div className="w-12 h-12 rounded-xl bg-accent-emerald/20 border border-accent-emerald/30 flex items-center justify-center text-accent-emerald shadow-glow-emerald">
            <IconAnalytics className="w-6 h-6" />
          </div>
          <h3 className="text-lg font-bold text-white tracking-tight">Comprehensive Analytics</h3>
          <p className="text-sm text-slate-400 leading-relaxed">
            Get 4-dimensional scoring (Correctness, Relevance, Depth, Communication) with actionable feedback and one-click PDF performance reports.
          </p>
        </GlassCard>
      </div>

      {/* ── 3-Step Workflow ──────────────────────────────── */}
      <div className="w-full space-y-8 pt-8">
        <div className="text-center space-y-2">
          <h2 className="text-2xl sm:text-3xl font-bold tracking-tight text-white">How It Works</h2>
          <p className="text-sm text-slate-400">Three simple steps to accelerate your career readiness</p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="glass-panel p-6 rounded-2xl relative space-y-3">
            <span className="text-4xl font-extrabold text-primary-500/30">01</span>
            <h4 className="text-base font-bold text-white">Configure Profile</h4>
            <p className="text-xs text-slate-400 leading-relaxed">
              Select your domain (Technical, HR, Behavioral), enter your target position, and optionally attach your resume.
            </p>
          </div>

          <div className="glass-panel p-6 rounded-2xl relative space-y-3">
            <span className="text-4xl font-extrabold text-accent-cyan/30">02</span>
            <h4 className="text-base font-bold text-white">Live Mock Simulation</h4>
            <p className="text-xs text-slate-400 leading-relaxed">
              Answer simulated interview questions one-by-one with intelligent pacing, voice recognition, and real-time response capture.
            </p>
          </div>

          <div className="glass-panel p-6 rounded-2xl relative space-y-3">
            <span className="text-4xl font-extrabold text-accent-emerald/30">03</span>
            <h4 className="text-base font-bold text-white">Actionable Feedback</h4>
            <p className="text-xs text-slate-400 leading-relaxed">
              Review strengths, weaknesses, question breakdowns, and export professional PDF evaluations to track your improvement.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
