import React from 'react';
import { Outlet, Link } from 'react-router-dom';
import { IconSparkles } from '../components/Icons';

export default function AuthLayout() {
  return (
    <div className="flex min-h-screen flex-col justify-center py-12 sm:px-6 lg:px-8 bg-[#070A12] text-[#F8FAFC] relative overflow-hidden bg-radial-ambient bg-grid-pattern selection:bg-primary-600/30 selection:text-white">
      {/* Background ambient orbs */}
      <div className="absolute top-1/4 left-1/2 -translate-x-1/2 -translate-y-1/2 w-96 h-96 bg-primary-600/10 rounded-full blur-3xl pointer-events-none" />
      <div className="absolute bottom-10 right-10 w-80 h-80 bg-accent-cyan/10 rounded-full blur-3xl pointer-events-none" />

      {/* Top Branding */}
      <div className="sm:mx-auto sm:w-full sm:max-w-md text-center relative z-10">
        <Link to="/" id="auth-logo" className="inline-flex items-center gap-3 group">
          <div className="w-12 h-12 rounded-2xl bg-gradient-to-tr from-primary-600 via-indigo-500 to-accent-cyan flex items-center justify-center shadow-glow-primary group-hover:scale-105 transition-transform duration-300">
            <IconSparkles className="w-6 h-6 text-white" />
          </div>
          <div className="text-left">
            <span className="text-xl font-extrabold tracking-tight text-white block group-hover:text-primary-300 transition-colors">
              AI Interview
            </span>
            <span className="text-xs uppercase font-bold tracking-widest text-accent-cyan">
              Simulator SaaS
            </span>
          </div>
        </Link>
      </div>

      {/* Card Container */}
      <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-xl px-4 relative z-10">
        <div className="glass-panel p-6 sm:p-10 rounded-3xl shadow-glass border border-white/[0.08] relative">
          <Outlet />
        </div>
      </div>
    </div>
  );
}
