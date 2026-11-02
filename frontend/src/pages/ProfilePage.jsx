import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../services/api';
import GlassCard from '../components/GlassCard';
import Button from '../components/Button';
import {
  IconArrowLeft,
  IconProfile,
  IconShield,
  IconCheck,
  IconLock,
} from '../components/Icons';

export default function ProfilePage() {
  const navigate = useNavigate();

  /* profile data */
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState('');

  /* name form */
  const [fullName, setFullName] = useState('');
  const [nameLoading, setNameLoading] = useState(false);
  const [nameMsg, setNameMsg] = useState({ type: '', text: '' });

  /* password form */
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [pwLoading, setPwLoading] = useState(false);
  const [pwMsg, setPwMsg] = useState({ type: '', text: '' });

  /* Load user profile on mount */
  useEffect(() => {
    (async () => {
      try {
        const { data } = await api.get('/auth/me');
        setUser(data);
        setFullName(data.full_name || '');
      } catch (err) {
        if (err?.response?.status === 401) navigate('/login');
        else setLoadError('Failed to load your profile. Please try again.');
      } finally {
        setLoading(false);
      }
    })();
  }, [navigate]);

  /* Update display name */
  const handleNameSave = async (e) => {
    e.preventDefault();
    setNameMsg({ type: '', text: '' });
    setNameLoading(true);
    try {
      const { data } = await api.put('/auth/me', { full_name: fullName.trim() || null });
      setUser(data);
      setFullName(data.full_name || '');
      setNameMsg({ type: 'success', text: 'Display name updated successfully.' });
    } catch (err) {
      const detail = err?.response?.data?.detail;
      setNameMsg({ type: 'error', text: typeof detail === 'string' ? detail : 'Failed to update name.' });
    } finally {
      setNameLoading(false);
    }
  };

  /* Change password */
  const handlePasswordChange = async (e) => {
    e.preventDefault();
    setPwMsg({ type: '', text: '' });
    if (newPassword.length < 8) {
      setPwMsg({ type: 'error', text: 'New password must be at least 8 characters.' });
      return;
    }
    if (newPassword !== confirmPassword) {
      setPwMsg({ type: 'error', text: 'New passwords do not match.' });
      return;
    }
    setPwLoading(true);
    try {
      await api.put('/auth/me', {
        current_password: currentPassword,
        new_password: newPassword,
      });
      setCurrentPassword('');
      setNewPassword('');
      setConfirmPassword('');
      setPwMsg({ type: 'success', text: 'Password changed successfully.' });
    } catch (err) {
      const detail = err?.response?.data?.detail;
      setPwMsg({ type: 'error', text: typeof detail === 'string' ? detail : 'Failed to change password.' });
    } finally {
      setPwLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[50vh] space-y-4">
        <div className="w-12 h-12 rounded-full border-2 border-primary-500/30 border-t-primary-500 animate-spin" />
        <p className="text-slate-400 text-sm">Loading user profile...</p>
      </div>
    );
  }

  if (loadError) {
    return (
      <div className="max-w-xl mx-auto mt-12 text-center space-y-4">
        <GlassCard className="p-8 space-y-4">
          <p className="text-rose-400 text-sm">{loadError}</p>
          <Button onClick={() => navigate('/dashboard')} variant="primary">
            Return to Dashboard
          </Button>
        </GlassCard>
      </div>
    );
  }

  const initials = (user?.full_name || user?.email || 'U')
    .split(' ')
    .map((w) => w[0])
    .join('')
    .slice(0, 2)
    .toUpperCase();

  return (
    <div className="max-w-3xl mx-auto space-y-8 pb-16">
      {/* Top Navigation */}
      <button
        onClick={() => navigate('/dashboard')}
        className="inline-flex items-center gap-2 text-xs font-semibold text-slate-400 hover:text-white transition-colors group"
      >
        <IconArrowLeft className="w-4 h-4 group-hover:-translate-x-1 transition-transform" />
        <span>Back to Dashboard</span>
      </button>

      {/* Header Profile Badge Card */}
      <GlassCard className="p-8 flex flex-col sm:flex-row items-center gap-6 bg-gradient-to-r from-primary-600/10 via-transparent to-transparent border-primary-500/20">
        <div className="w-20 h-20 rounded-full bg-gradient-to-tr from-primary-600 to-accent-purple flex items-center justify-center font-extrabold text-2xl text-white flex-shrink-0 shadow-glow-primary ring-4 ring-primary-500/20">
          {initials}
        </div>
        <div className="space-y-1 text-center sm:text-left min-w-0 flex-1">
          <h1 className="text-2xl font-extrabold tracking-tight text-white truncate">
            {user?.full_name || 'User Profile'}
          </h1>
          <p className="text-sm text-slate-400 font-mono truncate">{user?.email}</p>
          <div className="pt-2">
            <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold border ${
              user?.is_active
                ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20 shadow-[0_0_12px_rgba(34,197,94,0.15)]'
                : 'bg-rose-500/10 text-rose-400 border-rose-500/20'
            }`}>
              <span className={`w-1.5 h-1.5 rounded-full ${user?.is_active ? 'bg-emerald-400' : 'bg-rose-400'}`} />
              {user?.is_active ? 'Account Active & Verified' : 'Account Inactive'}
            </span>
          </div>
        </div>
      </GlassCard>

      {/* Display Name Section */}
      <GlassCard className="space-y-6 p-6">
        <div className="flex items-center gap-3 border-b border-white/[0.08] pb-4">
          <div className="p-2 rounded-xl bg-primary-600/20 text-primary-400">
            <IconProfile className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-base font-bold text-white">Personal Information</h2>
            <p className="text-xs text-slate-400">Update your public display name</p>
          </div>
        </div>

        <form onSubmit={handleNameSave} className="space-y-4">
          <div>
            <label htmlFor="full-name" className="block text-xs font-bold text-slate-300 uppercase tracking-wider mb-1.5">
              Full Display Name
            </label>
            <input
              id="full-name"
              type="text"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              placeholder="e.g. Alex Smith"
              disabled={nameLoading}
              className="w-full px-4 py-2.5 rounded-xl glass-input text-sm placeholder-slate-500"
            />
            <p className="text-[11px] text-slate-500 mt-1">This name will be displayed across evaluation reports.</p>
          </div>

          {nameMsg.text && (
            <div className={`p-3 rounded-xl text-xs font-medium border ${
              nameMsg.type === 'success'
                ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-300'
                : 'bg-rose-500/10 border-rose-500/30 text-rose-300'
            }`}>
              {nameMsg.text}
            </div>
          )}

          <div className="flex justify-end">
            <Button
              id="btn-save-name"
              type="submit"
              loading={nameLoading}
              variant="primary"
              size="sm"
              className="shadow-glow-primary"
            >
              Save Name Changes
            </Button>
          </div>
        </form>
      </GlassCard>

      {/* Account Info Readonly */}
      <GlassCard className="space-y-4 p-6">
        <div className="flex items-center gap-3 border-b border-white/[0.08] pb-4">
          <div className="p-2 rounded-xl bg-accent-cyan/20 text-accent-cyan">
            <IconShield className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-base font-bold text-white">Account Details</h2>
            <p className="text-xs text-slate-400">Primary authentication credentials</p>
          </div>
        </div>

        <div className="space-y-2">
          <label htmlFor="profile-email" className="block text-xs font-bold text-slate-300 uppercase tracking-wider">
            Email Address
          </label>
          <input
            id="profile-email"
            type="email"
            value={user?.email || ''}
            disabled
            readOnly
            className="w-full px-4 py-2.5 rounded-xl glass-input text-sm opacity-60 cursor-not-allowed font-mono"
          />
          <p className="text-[11px] text-slate-500">Your email address is your unique system identifier.</p>
        </div>
      </GlassCard>

      {/* Security & Password */}
      <GlassCard className="space-y-6 p-6">
        <div className="flex items-center gap-3 border-b border-white/[0.08] pb-4">
          <div className="p-2 rounded-xl bg-accent-purple/20 text-accent-purple">
            <IconLock className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-base font-bold text-white">Security & Password</h2>
            <p className="text-xs text-slate-400">Update your access password securely</p>
          </div>
        </div>

        <form onSubmit={handlePasswordChange} className="space-y-4">
          <div>
            <label htmlFor="current-password" className="block text-xs font-bold text-slate-300 uppercase tracking-wider mb-1.5">
              Current Password
            </label>
            <input
              id="current-password"
              type="password"
              value={currentPassword}
              onChange={(e) => setCurrentPassword(e.target.value)}
              placeholder="Enter current password"
              disabled={pwLoading}
              className="w-full px-4 py-2.5 rounded-xl glass-input text-sm placeholder-slate-500"
            />
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label htmlFor="new-password" className="block text-xs font-bold text-slate-300 uppercase tracking-wider mb-1.5">
                New Password
              </label>
              <input
                id="new-password"
                type="password"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                placeholder="Min 8 characters"
                disabled={pwLoading}
                className="w-full px-4 py-2.5 rounded-xl glass-input text-sm placeholder-slate-500"
              />
            </div>

            <div>
              <label htmlFor="confirm-password" className="block text-xs font-bold text-slate-300 uppercase tracking-wider mb-1.5">
                Confirm New Password
              </label>
              <input
                id="confirm-password"
                type="password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                placeholder="Re-enter new password"
                disabled={pwLoading}
                className="w-full px-4 py-2.5 rounded-xl glass-input text-sm placeholder-slate-500"
              />
            </div>
          </div>

          {pwMsg.text && (
            <div className={`p-3 rounded-xl text-xs font-medium border ${
              pwMsg.type === 'success'
                ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-300'
                : 'bg-rose-500/10 border-rose-500/30 text-rose-300'
            }`}>
              {pwMsg.text}
            </div>
          )}

          <div className="flex justify-end pt-2">
            <Button
              id="btn-change-password"
              type="submit"
              loading={pwLoading}
              disabled={!currentPassword || !newPassword || !confirmPassword}
              variant="cyan"
              size="sm"
            >
              Update Password
            </Button>
          </div>
        </form>
      </GlassCard>
    </div>
  );
}
