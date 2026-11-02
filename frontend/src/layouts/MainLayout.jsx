import React, { useState, useEffect } from 'react';
import { Outlet, Link, useLocation, useNavigate } from 'react-router-dom';
import {
  IconHome,
  IconDashboard,
  IconInterview,
  IconProfile,
  IconLogOut,
  IconSparkles,
  IconMenu,
  IconClose,
  IconPlus,
} from '../components/Icons';
import api from '../services/api';

export default function MainLayout() {
  const location = useLocation();
  const navigate = useNavigate();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [user, setUser] = useState(null);

  // Fetch current user info for sidebar profile pill if token exists
  useEffect(() => {
    const token = localStorage.getItem('token');
    if (token) {
      api.get('/auth/me')
        .then((res) => setUser(res.data))
        .catch(() => {
          // Token expired or invalid
          setUser(null);
        });
    } else {
      setUser(null);
    }
  }, [location.pathname]);

  // Close mobile drawer on route change
  useEffect(() => {
    setMobileOpen(false);
  }, [location.pathname]);

  const handleLogout = () => {
    localStorage.removeItem('token');
    setUser(null);
    navigate('/login');
  };

  const navItems = [
    { label: 'Home', path: '/', icon: IconHome, id: 'nav-home' },
    { label: 'Dashboard', path: '/dashboard', icon: IconDashboard, id: 'nav-dashboard' },
    { label: 'New Interview', path: '/interview/setup', icon: IconInterview, id: 'nav-new-interview' },
    { label: 'Profile', path: '/profile', icon: IconProfile, id: 'nav-profile' },
  ];

  const isAuthenticated = Boolean(localStorage.getItem('token'));

  return (
    <div className="flex min-h-screen bg-[#070A12] text-[#F8FAFC] selection:bg-primary-600/30 selection:text-white bg-radial-ambient">
      {/* ── Desktop Sidebar ─────────────────────────────── */}
      <aside className="hidden md:flex flex-col w-64 border-r border-white/[0.08] bg-[#0B1020]/90 backdrop-blur-2xl fixed inset-y-0 left-0 z-40">
        {/* Logo Branding */}
        <div className="h-20 flex items-center px-6 border-b border-white/[0.06]">
          <Link to="/" id="nav-logo" className="flex items-center gap-3 group">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-primary-600 via-indigo-500 to-accent-cyan flex items-center justify-center shadow-glow-primary group-hover:scale-105 transition-transform duration-300">
              <IconSparkles className="w-5 h-5 text-white animate-pulse-subtle" />
            </div>
            <div>
              <span className="text-base font-bold tracking-tight text-white group-hover:text-primary-300 transition-colors">
                AI Interview
              </span>
              <span className="block text-[10px] uppercase font-semibold tracking-wider text-accent-cyan/90">
                Simulator Pro
              </span>
            </div>
          </Link>
        </div>

        {/* Quick Action */}
        <div className="p-4">
          <Link
            to="/interview/setup"
            id="btn-sidebar-quick-start"
            className="flex items-center justify-center gap-2 w-full py-2.5 px-4 rounded-xl text-sm font-semibold text-white btn-primary shadow-glow-primary group transition-all"
          >
            <IconPlus className="w-4 h-4 group-hover:rotate-90 transition-transform duration-200" />
            <span>Start Interview</span>
          </Link>
        </div>

        {/* Nav Links */}
        <nav className="flex-1 px-3 py-2 space-y-1 overflow-y-auto">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive =
              item.path === '/'
                ? location.pathname === '/'
                : location.pathname.startsWith(item.path);

            return (
              <Link
                key={item.path}
                to={item.path}
                id={item.id}
                className={`flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-sm font-medium transition-all duration-200 group relative ${
                  isActive
                    ? 'text-white bg-primary-600/15 border border-primary-500/30 shadow-[0_0_15px_rgba(108,99,255,0.15)] font-semibold'
                    : 'text-slate-400 hover:text-white hover:bg-white/[0.04]'
                }`}
              >
                {isActive && (
                  <span className="absolute left-0 top-2 bottom-2 w-1 bg-gradient-to-b from-primary-500 to-accent-cyan rounded-r-full" />
                )}
                <Icon
                  className={`w-5 h-5 transition-colors ${
                    isActive
                      ? 'text-primary-400'
                      : 'text-slate-400 group-hover:text-slate-200'
                  }`}
                />
                <span>{item.label}</span>
              </Link>
            );
          })}
        </nav>

        {/* Bottom User Profile / Auth Action */}
        <div className="p-4 border-t border-white/[0.06] bg-[#070A12]/50">
          {isAuthenticated ? (
            <div className="flex items-center justify-between gap-3">
              <Link
                to="/profile"
                className="flex items-center gap-3 min-w-0 flex-1 hover:opacity-85 transition-opacity"
              >
                <div className="w-9 h-9 rounded-full bg-gradient-to-tr from-primary-600 to-accent-purple flex items-center justify-center font-bold text-xs text-white uppercase flex-shrink-0 ring-2 ring-primary-500/30">
                  {user?.full_name ? user.full_name.charAt(0) : user?.email ? user.email.charAt(0) : 'U'}
                </div>
                <div className="min-w-0 flex-1">
                  <p className="text-xs font-semibold text-white truncate">
                    {user?.full_name || 'User'}
                  </p>
                  <p className="text-[11px] text-slate-400 truncate">
                    {user?.email || 'Authenticated'}
                  </p>
                </div>
              </Link>
              <button
                id="btn-sidebar-logout"
                onClick={handleLogout}
                title="Sign Out"
                className="p-2 text-slate-400 hover:text-rose-400 hover:bg-rose-500/10 rounded-lg transition-colors flex-shrink-0"
              >
                <IconLogOut className="w-4 h-4" />
              </button>
            </div>
          ) : (
            <div className="flex flex-col gap-2">
              <Link
                to="/login"
                id="sidebar-link-login"
                className="text-center py-2 px-3 text-xs font-medium text-slate-300 hover:text-white bg-white/[0.04] hover:bg-white/[0.08] border border-white/[0.08] rounded-lg transition-colors"
              >
                Sign In
              </Link>
              <Link
                to="/register"
                id="sidebar-link-register"
                className="text-center py-2 px-3 text-xs font-semibold text-white btn-primary rounded-lg shadow-glow-primary transition-all"
              >
                Create Account
              </Link>
            </div>
          )}
        </div>
      </aside>

      {/* ── Mobile Header & Drawer ──────────────────────── */}
      <div className="md:hidden fixed top-0 inset-x-0 h-16 border-b border-white/[0.08] bg-[#0B1020]/95 backdrop-blur-2xl z-50 flex items-center justify-between px-4">
        <Link to="/" className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-primary-600 to-accent-cyan flex items-center justify-center shadow-glow-primary">
            <IconSparkles className="w-4 h-4 text-white" />
          </div>
          <span className="text-sm font-bold text-white tracking-tight">
            AI Interview Simulator
          </span>
        </Link>
        <button
          onClick={() => setMobileOpen(!mobileOpen)}
          className="p-2 text-slate-400 hover:text-white rounded-lg bg-white/[0.04] border border-white/[0.08]"
          aria-label="Toggle Menu"
        >
          {mobileOpen ? <IconClose className="w-5 h-5" /> : <IconMenu className="w-5 h-5" />}
        </button>
      </div>

      {/* Mobile Drawer Menu */}
      {mobileOpen && (
        <div className="md:hidden fixed inset-0 top-16 bg-[#070A12]/95 backdrop-blur-3xl z-40 p-6 flex flex-col justify-between border-t border-white/[0.08]">
          <nav className="space-y-2">
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive =
                item.path === '/'
                  ? location.pathname === '/'
                  : location.pathname.startsWith(item.path);

              return (
                <Link
                  key={item.path}
                  to={item.path}
                  id={`mobile-${item.id}`}
                  className={`flex items-center gap-3.5 px-4 py-3 rounded-xl text-base font-medium transition-colors ${
                    isActive
                      ? 'text-white bg-primary-600/20 border border-primary-500/30'
                      : 'text-slate-300 hover:bg-white/[0.05]'
                  }`}
                >
                  <Icon className={`w-5 h-5 ${isActive ? 'text-primary-400' : 'text-slate-400'}`} />
                  <span>{item.label}</span>
                </Link>
              );
            })}
          </nav>

          <div className="pt-6 border-t border-white/[0.08] space-y-3">
            {isAuthenticated ? (
              <button
                onClick={handleLogout}
                className="flex items-center justify-center gap-2 w-full py-2.5 px-4 text-sm font-semibold text-rose-400 bg-rose-500/10 border border-rose-500/20 rounded-xl"
              >
                <IconLogOut className="w-4 h-4" />
                <span>Sign Out</span>
              </button>
            ) : (
              <div className="grid grid-cols-2 gap-3">
                <Link
                  to="/login"
                  className="text-center py-2.5 text-sm font-medium text-slate-300 bg-white/[0.05] border border-white/[0.08] rounded-xl"
                >
                  Sign In
                </Link>
                <Link
                  to="/register"
                  className="text-center py-2.5 text-sm font-semibold text-white btn-primary rounded-xl"
                >
                  Register
                </Link>
              </div>
            )}
          </div>
        </div>
      )}

      {/* ── Main Content Area ───────────────────────────── */}
      <div className="flex-1 md:pl-64 flex flex-col min-h-screen">
        {/* Top Header Bar for Desktop */}
        <header className="hidden md:flex h-16 items-center justify-between px-8 border-b border-white/[0.06] bg-[#0B1020]/40 backdrop-blur-xl sticky top-0 z-30">
          <div className="flex items-center gap-2 text-xs text-slate-400">
            <span>AI Platform</span>
            <span>/</span>
            <span className="text-slate-200 capitalize font-medium">
              {location.pathname === '/' ? 'Home' : location.pathname.split('/')[1] || 'Dashboard'}
            </span>
          </div>

          <div className="flex items-center gap-4">
            <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 shadow-[0_0_12px_rgba(34,197,94,0.15)]">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
              AI Provider Active
            </span>
            <Link
              to="/interview/setup"
              id="btn-header-new-interview"
              className="inline-flex items-center gap-1.5 px-3.5 py-1.5 text-xs font-semibold text-white btn-primary rounded-lg shadow-glow-primary transition-all"
            >
              <IconPlus className="w-3.5 h-3.5" />
              <span>New Session</span>
            </Link>
          </div>
        </header>

        {/* Page View */}
        <main className="flex-1 p-4 sm:p-6 lg:p-8 pt-20 md:pt-8 max-w-7xl mx-auto w-full">
          <Outlet />
        </main>

        {/* Footer */}
        <footer className="border-t border-white/[0.06] bg-[#070A12]/80 py-6 text-center text-xs text-slate-500">
          <p>© {new Date().getFullYear()} AI Interview Simulator. Engineered for peak interview readiness.</p>
        </footer>
      </div>
    </div>
  );
}
