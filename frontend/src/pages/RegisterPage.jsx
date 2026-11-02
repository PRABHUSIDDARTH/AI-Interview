import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import api from '../services/api';
import { IconEye, IconEyeOff, IconCheck } from '../components/Icons';
import Button from '../components/Button';

export default function RegisterPage() {
  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');

    if (password !== confirmPassword) {
      setError('Passwords do not match. Please verify and try again.');
      return;
    }

    if (password.length < 6) {
      setError('Password must be at least 6 characters long.');
      return;
    }

    setLoading(true);
    try {
      // Backend expects { full_name, email, password }
      await api.post('/auth/register', {
        full_name: fullName.trim(),
        email: email.trim(),
        password: password,
      });

      // Redirect to login upon successful registration
      navigate('/login');
    } catch (err) {
      const detail = err.response?.data?.detail;
      setError(
        typeof detail === 'string'
          ? detail
          : 'Registration failed. Please verify your details or use a different email.'
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Card Header */}
      <div className="text-center space-y-2">
        <h2 className="text-2xl font-extrabold tracking-tight text-white">Create Your Account</h2>
        <p className="text-sm text-slate-400">
          Start practicing with customized AI interview sessions in seconds.
        </p>
      </div>

      {/* Error Alert */}
      {error && (
        <div className="p-3.5 text-sm bg-rose-500/10 border border-rose-500/30 text-rose-300 rounded-xl flex items-center gap-2.5">
          <span className="w-2 h-2 rounded-full bg-rose-400 flex-shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Register Form */}
      <form className="space-y-4" onSubmit={handleSubmit}>
        <div>
          <label htmlFor="input-fullname" className="block text-xs font-semibold text-slate-300 mb-1.5 uppercase tracking-wider">
            Full Name
          </label>
          <input
            id="input-fullname"
            name="fullName"
            type="text"
            required
            value={fullName}
            onChange={(e) => setFullName(e.target.value)}
            className="block w-full rounded-xl glass-input px-3.5 py-2.5 text-sm placeholder-slate-500 focus:border-primary-500 focus:ring-1 focus:ring-primary-500"
            placeholder="Jane Doe"
          />
        </div>

        <div>
          <label htmlFor="input-email" className="block text-xs font-semibold text-slate-300 mb-1.5 uppercase tracking-wider">
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

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5">
          <div>
            <label htmlFor="input-password" className="block text-xs font-semibold text-slate-300 mb-1.5 uppercase tracking-wider">
              Password
            </label>
            <div className="relative">
              <input
                id="input-password"
                name="password"
                type={showPassword ? 'text' : 'password'}
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

          <div>
            <label htmlFor="input-confirm-password" className="block text-xs font-semibold text-slate-300 mb-1.5 uppercase tracking-wider">
              Confirm Password
            </label>
            <input
              id="input-confirm-password"
              name="confirmPassword"
              type={showPassword ? 'text' : 'password'}
              required
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              className="block w-full rounded-xl glass-input px-3.5 py-2.5 text-sm placeholder-slate-500 focus:border-primary-500 focus:ring-1 focus:ring-primary-500"
              placeholder="••••••••"
            />
          </div>
        </div>

        <div className="pt-2">
          <Button
            id="btn-register-submit"
            type="submit"
            loading={loading}
            className="w-full py-3 rounded-xl font-semibold shadow-glow-primary"
          >
            Create Your Free Account
          </Button>
        </div>
      </form>

      {/* Switch to Login */}
      <div className="pt-2 text-center text-xs text-slate-400 border-t border-white/[0.06]">
        Already have an account?{' '}
        <Link
          to="/login"
          id="link-to-login"
          className="font-semibold text-accent-cyan hover:text-accent-cyan/80 transition-colors"
        >
          Sign in instead
        </Link>
      </div>
    </div>
  );
}
