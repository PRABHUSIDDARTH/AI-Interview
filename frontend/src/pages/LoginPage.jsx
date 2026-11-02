import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import api from '../services/api';
import { IconSparkles, IconEye, IconEyeOff, IconLock, IconShield } from '../components/Icons';
import Button from '../components/Button';

export default function LoginPage() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      // Call backend OAuth2 form-urlencoded endpoint
      const formData = new URLSearchParams();
      formData.append('username', email.trim());
      formData.append('password', password);

      const response = await api.post('/auth/login', formData, {
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      });

      const { access_token } = response.data;
      localStorage.setItem('token', access_token);
      navigate('/dashboard');
    } catch (err) {
      const detail = err.response?.data?.detail;
      setError(
        typeof detail === 'string'
          ? detail
          : 'Authentication failed. Please check your credentials.'
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Card Header */}
      <div className="text-center space-y-2">
        <h2 className="text-2xl font-extrabold tracking-tight text-white">Welcome Back</h2>
        <p className="text-sm text-slate-400">
          Sign in to access your interview dashboard & evaluations.
        </p>
      </div>

      {/* Error Alert */}
      {error && (
        <div className="p-3.5 text-sm bg-rose-500/10 border border-rose-500/30 text-rose-300 rounded-xl flex items-center gap-2.5 animate-pulse">
          <span className="w-2 h-2 rounded-full bg-rose-400 flex-shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Login Form */}
      <form className="space-y-4" onSubmit={handleSubmit}>
        <div>
          <label htmlFor="input-email" className="block text-xs font-semibold text-slate-300 mb-1.5 uppercase tracking-wider">
            Email Address
          </label>
          <div className="relative">
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
        </div>

        <div>
          <div className="flex items-center justify-between mb-1.5">
            <label htmlFor="input-password" className="block text-xs font-semibold text-slate-300 uppercase tracking-wider">
              Password
            </label>
            <Link
              to="/forgot-password"
              id="link-forgot-password"
              className="text-xs font-semibold text-accent-cyan hover:text-accent-cyan/80 transition-colors"
            >
              Forgot password?
            </Link>
          </div>
          <div className="relative">
            <input
              id="input-password"
              name="password"
              type={showPassword ? 'text' : 'password'}
              autoComplete="current-password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="block w-full rounded-xl glass-input px-3.5 py-2.5 pr-10 text-sm placeholder-slate-500 focus:border-primary-500 focus:ring-1 focus:ring-primary-500"
              placeholder="••••••••"
            />
            <button
              type="button"
              onClick={() => setShowPassword(!showPassword)}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-white transition-colors"
              aria-label={showPassword ? "Hide password" : "Show password"}
            >
              {showPassword ? <IconEyeOff className="w-4 h-4" /> : <IconEye className="w-4 h-4" />}
            </button>
          </div>
        </div>

        <div className="pt-2">
          <Button
            id="btn-login-submit"
            type="submit"
            loading={loading}
            className="w-full py-3 rounded-xl font-semibold shadow-glow-primary"
          >
            Sign In to Account
          </Button>
        </div>
      </form>

      {/* Switch to Register */}
      <div className="pt-2 text-center text-xs text-slate-400 border-t border-white/[0.06]">
        Don't have an account yet?{' '}
        <Link
          to="/register"
          id="link-to-register"
          className="font-semibold text-accent-cyan hover:text-accent-cyan/80 transition-colors"
        >
          Create an account
        </Link>
      </div>
    </div>
  );
}
