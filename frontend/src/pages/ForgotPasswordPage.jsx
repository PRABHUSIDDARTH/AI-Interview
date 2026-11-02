import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import api from '../services/api';
import { IconSparkles } from '../components/Icons';
import Button from '../components/Button';

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState('');
  const [loading, setLoading] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      await api.post('/auth/forgot-password', { email: email.trim() });
      // Always show success regardless of whether email exists (anti-enumeration)
      setSubmitted(true);
    } catch (err) {
      // Only show a generic error for network/server failures
      setError('Something went wrong. Please try again later.');
    } finally {
      setLoading(false);
    }
  };

  if (submitted) {
    return (
      <div className="space-y-6">
        {/* Success State */}
        <div className="text-center space-y-3">
          {/* Animated checkmark icon */}
          <div className="mx-auto w-16 h-16 rounded-2xl bg-gradient-to-tr from-emerald-600 via-teal-500 to-accent-cyan flex items-center justify-center shadow-lg">
            <svg className="w-8 h-8 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
            </svg>
          </div>
          <h2 className="text-2xl font-extrabold tracking-tight text-white">Check your email</h2>
          <p className="text-sm text-slate-400 leading-relaxed max-w-sm mx-auto">
            If an account with <span className="text-white font-medium">{email}</span> exists, 
            password reset instructions have been sent. Check your inbox (and spam folder).
          </p>
        </div>

        <div className="p-4 bg-emerald-500/10 border border-emerald-500/20 rounded-xl text-sm text-emerald-300">
          The link will expire in <span className="font-semibold">30 minutes</span>.
        </div>

        <div className="pt-2 text-center text-xs text-slate-400 border-t border-white/[0.06]">
          <Link
            to="/login"
            id="link-back-to-signin-success"
            className="font-semibold text-accent-cyan hover:text-accent-cyan/80 transition-colors"
          >
            ← Back to Sign In
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Card Header */}
      <div className="text-center space-y-2">
        <div className="mx-auto w-12 h-12 rounded-2xl bg-gradient-to-tr from-primary-600 via-indigo-500 to-accent-cyan flex items-center justify-center shadow-glow-primary mb-4">
          <svg className="w-6 h-6 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z" />
          </svg>
        </div>
        <h2 className="text-2xl font-extrabold tracking-tight text-white">Forgot your password?</h2>
        <p className="text-sm text-slate-400 leading-relaxed">
          Enter your registered email and we'll send you instructions to reset your password.
        </p>
      </div>

      {/* Error Alert */}
      {error && (
        <div className="p-3.5 text-sm bg-rose-500/10 border border-rose-500/30 text-rose-300 rounded-xl flex items-center gap-2.5">
          <span className="w-2 h-2 rounded-full bg-rose-400 flex-shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Forgot Password Form */}
      <form className="space-y-4" onSubmit={handleSubmit}>
        <div>
          <label
            htmlFor="input-email"
            className="block text-xs font-semibold text-slate-300 mb-1.5 uppercase tracking-wider"
          >
            Email Address
          </label>
          <input
            id="input-email"
            name="email"
            type="email"
            autoComplete="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="block w-full rounded-xl glass-input px-3.5 py-2.5 text-sm placeholder-slate-500 focus:border-primary-500 focus:ring-1 focus:ring-primary-500"
            placeholder="you@example.com"
          />
        </div>

        <div className="pt-2">
          <Button
            id="btn-send-reset-link"
            type="submit"
            loading={loading}
            className="w-full py-3 rounded-xl font-semibold shadow-glow-primary"
          >
            Send Reset Link
          </Button>
        </div>
      </form>

      {/* Back to Sign In */}
      <div className="pt-2 text-center text-xs text-slate-400 border-t border-white/[0.06]">
        <Link
          to="/login"
          id="link-back-to-signin"
          className="font-semibold text-accent-cyan hover:text-accent-cyan/80 transition-colors"
        >
          ← Back to Sign In
        </Link>
      </div>
    </div>
  );
}
