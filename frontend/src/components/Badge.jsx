import React from 'react';

export function StatusBadge({ status }) {
  const map = {
    created: {
      label: 'Created',
      dot: 'bg-cyan-400',
      cls: 'bg-cyan-500/10 text-cyan-400 border-cyan-500/20 shadow-[0_0_12px_rgba(34,211,238,0.15)]',
    },
    in_progress: {
      label: 'In Progress',
      dot: 'bg-amber-400 animate-pulse',
      cls: 'bg-amber-500/10 text-amber-300 border-amber-500/20 shadow-[0_0_12px_rgba(245,158,11,0.15)]',
    },
    completed: {
      label: 'Completed',
      dot: 'bg-emerald-400',
      cls: 'bg-emerald-500/10 text-emerald-300 border-emerald-500/20 shadow-[0_0_12px_rgba(34,197,94,0.15)]',
    },
    cancelled: {
      label: 'Cancelled',
      dot: 'bg-rose-400',
      cls: 'bg-rose-500/10 text-rose-400 border-rose-500/20',
    },
  };

  const current = map[status] || {
    label: status || 'Unknown',
    dot: 'bg-slate-400',
    cls: 'bg-slate-800/60 text-slate-300 border-slate-700',
  };

  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold border ${current.cls} backdrop-blur-md`}>
      <span className={`w-1.5 h-1.5 rounded-full ${current.dot}`} />
      {current.label}
    </span>
  );
}

export function DifficultyBadge({ difficulty }) {
  const map = {
    Easy: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20',
    Medium: 'bg-amber-500/10 text-amber-400 border-amber-500/20',
    Hard: 'bg-rose-500/10 text-rose-400 border-rose-500/20',
  };

  const cls = map[difficulty] || 'bg-slate-800 text-slate-300 border-slate-700';

  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-md text-xs font-medium border ${cls}`}>
      {difficulty}
    </span>
  );
}
