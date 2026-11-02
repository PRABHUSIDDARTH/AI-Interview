import React from 'react';

export function Skeleton({ className = 'h-4 w-full' }) {
  return (
    <div className={`animate-pulse rounded-lg bg-slate-800/60 border border-slate-700/30 ${className}`} />
  );
}

export function DashboardSkeleton() {
  return (
    <div className="space-y-8 animate-pulse">
      {/* Header skeleton */}
      <div className="flex justify-between items-center">
        <div className="space-y-2">
          <Skeleton className="h-8 w-48" />
          <Skeleton className="h-4 w-72" />
        </div>
        <Skeleton className="h-10 w-32 rounded-xl" />
      </div>

      {/* Metric Cards Skeleton */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="glass-panel p-6 rounded-2xl space-y-3">
            <Skeleton className="h-4 w-24" />
            <Skeleton className="h-8 w-16" />
            <Skeleton className="h-3 w-32" />
          </div>
        ))}
      </div>

      {/* Chart Skeleton */}
      <div className="glass-panel p-6 rounded-2xl space-y-4">
        <Skeleton className="h-6 w-40" />
        <Skeleton className="h-64 w-full rounded-xl" />
      </div>
    </div>
  );
}
