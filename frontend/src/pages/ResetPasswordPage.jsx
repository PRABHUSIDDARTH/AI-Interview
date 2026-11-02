import React, { useState, useEffect } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import api from '../services/api';
import { IconEye, IconEyeOff } from '../components/Icons';
import Button from '../components/Button';

export default function ResetPasswordPage() {
  const [searchParams] = useSearchParams();
  const token = searchParams.get('token');

  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState('');
  const [validationError, setValidationError] = useState('');

  // Check token presence immediately on mount
  const tokenMissing = !token || token.trim() === '';

  const validate = () => {
    if (!newPassword) {
      setValidationError('Password cannot be empty.');
      return false;
    }
    if (newPassword.length < 8) {
      setValidationError('Password must be at least 8 characters long.');
      return false;
    }
    if (newPassword !== confirmPassword) {
      setValidationError('Passwords do not match. Please verify and try again.');
      return false;
    }
    setValidationError('');
    return true;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    if (!validate()) return;

    setLoading(true);
    try {
      await api.post('/auth/reset-password', {
        token: token,
        new_password: newPassword,
      });
      setSuccess(true);
    } catch (err) {
      const detail = err.response?.data?.detail;
      if (detail && detail.toLowerCase().includes('invalid or has expired')) {
        setError('invalid_or_expired');
      } else {
        setError(
          typeof detail === 'string'
            ? detail
            : 'Something went wrong. Please request a new reset link.'
        );
      }
    } finally {
      setLoading(false);
    }
  };

  // -------------------------------------------------------------------------
  // Invalid / missing token state
  // -------------------------------------------------------------------------
  if (tokenMissing || error === 'invalid_or_expired') {
    return (
      <div className="space-y-6">
        <div className="text-center space-y-3">
          <div className="mx-auto w-16 h-16 rounded-2xl bg-rose-500/20 border border-rose-500/30 flex items-center justify-center">
            <svg className="w-8 h-8 text-rose-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01M10.293 4.293a1 1 0 011.414 0L21 13.586a1 1 0 010 1.414l-7.5 7.5a1 1 0 01-1.414 0L2.707 15A1 1 0 012.707 13.586l7.586-9.293z" />
            </svg>
          </div>
          <h2 className="text-2xl font-extrabold tracking-tight text-white">Link Invalid or Expired</h2>
          <p className="text-sm text-slate-400 leading-relaxed max-w-sm mx-auto">
            This password reset link is invalid or has expired. Reset links are only valid for 30 minutes.
          </p>
        </div>

        <div className="pt-2">
          <Link
            to="/forgot-password"
            id="link-request-new-reset"
            className="flex items-center justify-center w-full py-3 rounded-xl font-semibold text-sm bg-white/[0.06] hover:bg-white/[0.1] border border-white/[0.08] text-white transition-colors"
          >
            Request a new reset link
          </Link>
        </div>

        <div className="pt-2 text-center text-xs text-slate-400 border-t border-white/[0.06]">
          <Link
            to="/login"
            id="link-back-to-signin-invalid"
            className="font-semibold text-accent-cyan hover:text-accent-cyan/80 transition-colors"
          >
            ← Back to Sign In
          </Link>
        </div>
      </div>
    );
  }

  // -------------------------------------------------------------------------
  // Success state
  // -------------------------------------------------------------------------
  if (success) {
    return (
      <div className="space-y-6">
        <div className="text-center space-y-3">
          <div className="mx-auto w-16 h-16 rounded-2xl bg-gradient-to-tr from-emerald-600 via-teal-500 to-accent-cyan flex items-center justify-center shadow-lg">
            <svg className="w-8 h-8 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
            </svg>
          </div>
          <h2 className="text-2xl font-extrabold tracking-tight text-white">Password Reset!</h2>
          <p className="text-sm text-slate-400 leading-relaxed">
            Your password has been reset successfully. You can now sign in with your new password.
          </p>
        </div>

        <div className="pt-2">
          <Link
            to="/login"
            id="link-signin-after-reset"
            className="flex items-center justify-center w-full py-3 rounded-xl font-semibold text-sm bg-gradient-to-r from-primary-600 to-indigo-500 hover:from-primary-500 hover:to-indigo-400 text-white shadow-glow-primary transition-all"
          >
            Sign In with New Password
          </Link>
        </div>
      </div>
    );
  }

  // -------------------------------------------------------------------------
  // Reset form
  // -------------------------------------------------------------------------
  return (
    <div className="space-y-6">
      {/* Card Header */}
      <div className="text-center space-y-2">
        <div className="mx-auto w-12 h-12 rounded-2xl bg-gradient-to-tr from-primary-600 via-indigo-500 to-accent-cyan flex items-center justify-center shadow-glow-primary mb-4">
          <svg className="w-6 h-6 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
          </svg>
        </div>
        <h2 className="text-2xl font-extrabold tracking-tight text-white">Create a new password</h2>
        <p className="text-sm text-slate-400 leading-relaxed">
          Choose a strong password with at least 8 characters.
        </p>
      </div>

      {/* Generic Error Alert */}
      {error && error !== 'invalid_or_expired' && (
        <div className="p-3.5 text-sm bg-rose-500/10 border border-rose-500/30 text-rose-300 rounded-xl flex items-center gap-2.5">
          <span className="w-2 h-2 rounded-full bg-rose-400 flex-shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Validation Error Alert */}
      {validationError && (
        <div className="p-3.5 text-sm bg-amber-500/10 border border-amber-500/30 text-amber-300 rounded-xl flex items-center gap-2.5">
          <span className="w-2 h-2 rounded-full bg-amber-400 flex-shrink-0" />
          <span>{validationError}</span>
        </div>
      )}

      {/* Reset Form */}
      <form className="space-y-4" onSubmit={handleSubmit}>
        {/* New Password */}
        <div>
          <label
            htmlFor="input-new-password"
            className="block text-xs font-semibold text-slate-300 mb-1.5 uppercase tracking-wider"
          >
            New Password
          </label>
          <div className="relative">
            <input
              id="input-new-password"
              name="new_password"
              type={showPassword ? 'text' : 'password'}
              autoComplete="new-password"
              required
              value={newPassword}
              onChange={(e) => { setNewPassword(e.target.value); setValidationError(''); }}
              className="block w-full rounded-xl glass-input px-3.5 py-2.5 pr-10 text-sm placeholder-slate-500 focus:border-primary-500 focus:ring-1 focus:ring-primary-500"
              placeholder="••••••••"
            />
            <button
              type="button"
              onClick={() => setShowPassword(!showPassword)}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-white transition-colors"
              aria-label={showPassword ? 'Hide password' : 'Show password'}
            >
              {showPassword ? <IconEyeOff className="w-4 h-4" /> : <IconEye className="w-4 h-4" />}
            </button>
          </div>
          {/* Strength hint */}
          {newPassword.length > 0 && newPassword.length < 8 && (
            <p className="mt-1.5 text-xs text-amber-400">
              At least {8 - newPassword.length} more character{8 - newPassword.length !== 1 ? 's' : ''} needed
            </p>
          )}
        </div>

        {/* Confirm Password */}
        <div>
          <label
            htmlFor="input-confirm-password"
            className="block text-xs font-semibold text-slate-300 mb-1.5 uppercase tracking-wider"
          >
            Confirm New Password
          </label>
          <div className="relative">
            <input
              id="input-confirm-password"
              name="confirm_password"
              type={showPassword ? 'text' : 'password'}
              autoComplete="new-password"
              required
              value={confirmPassword}
              onChange={(e) => { setConfirmPassword(e.target.value); setValidationError(''); }}
              className="block w-full rounded-xl glass-input px-3.5 py-2.5 pr-10 text-sm placeholder-slate-500 focus:border-primary-500 focus:ring-1 focus:ring-primary-500"
              placeholder="••••••••"
            />
          </div>
          {/* Inline match hint */}
          {confirmPassword.length > 0 && newPassword !== confirmPassword && (
            <p className="mt-1.5 text-xs text-rose-400">Passwords don't match</p>
          )}
          {confirmPassword.length > 0 && newPassword === confirmPassword && newPassword.length >= 8 && (
            <p className="mt-1.5 text-xs text-emerald-400 flex items-center gap-1">
              <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
              </svg>
              Passwords match
            </p>
          )}
        </div>

        <div className="pt-2">
          <Button
            id="btn-reset-password"
            type="submit"
            loading={loading}
            className="w-full py-3 rounded-xl font-semibold shadow-glow-primary"
          >
            Reset Password
          </Button>
        </div>
      </form>

      {/* Back to Sign In */}
      <div className="pt-2 text-center text-xs text-slate-400 border-t border-white/[0.06]">
        <Link
          to="/login"
          id="link-back-to-signin-reset"
          className="font-semibold text-accent-cyan hover:text-accent-cyan/80 transition-colors"
        >
          ← Back to Sign In
        </Link>
      </div>
    </div>
  );
}
