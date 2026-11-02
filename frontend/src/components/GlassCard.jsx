import React from 'react';

export default function GlassCard({
  children,
  className = '',
  interactive = false,
  active = false,
  glow = false,
  onClick,
  id,
  style = {}
}) {
  const baseClasses = 'relative rounded-2xl p-6 transition-all duration-300';
  const panelStyle = interactive ? 'glass-panel-interactive cursor-pointer' : 'glass-panel';
  const activeStyle = active ? 'glass-card-active ring-1 ring-primary-500/50' : '';
  const glowStyle = glow ? 'shadow-glow-primary' : '';

  return (
    <div
      id={id}
      onClick={onClick}
      style={style}
      className={`${baseClasses} ${panelStyle} ${activeStyle} ${glowStyle} ${className}`}
    >
      {children}
    </div>
  );
}
