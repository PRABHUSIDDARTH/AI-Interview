import React from 'react';

export default function Button({
  children,
  id,
  onClick,
  type = 'button',
  variant = 'primary',
  size = 'md',
  disabled = false,
  loading = false,
  icon: Icon = null,
  iconPosition = 'left',
  className = '',
}) {
  const sizeStyles = {
    sm: 'px-3 py-1.5 text-xs rounded-lg gap-1.5',
    md: 'px-4 py-2 text-sm rounded-xl gap-2',
    lg: 'px-6 py-3 text-base rounded-xl gap-2.5 font-semibold',
  };

  const variantStyles = {
    primary: 'btn-primary',
    secondary: 'btn-secondary',
    cyan: 'btn-cyan',
    danger: 'bg-rose-600/20 border border-rose-500/30 text-rose-400 hover:bg-rose-600/30 hover:border-rose-500/50 hover:text-white',
    ghost: 'text-slate-300 hover:text-white hover:bg-white/5 rounded-lg',
  };

  return (
    <button
      id={id}
      type={type}
      onClick={onClick}
      disabled={disabled || loading}
      className={`inline-flex items-center justify-center font-medium transition-all duration-200 focus:outline-none focus-visible:ring-2 focus-visible:ring-primary-500 disabled:opacity-50 disabled:cursor-not-allowed disabled:transform-none select-none ${sizeStyles[size] || sizeStyles.md} ${variantStyles[variant] || variantStyles.primary} ${className}`}
    >
      {loading ? (
        <>
          <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-current" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
          </svg>
          <span>Loading...</span>
        </>
      ) : (
        <>
          {Icon && iconPosition === 'left' && <Icon className="w-4 h-4 flex-shrink-0" />}
          {children}
          {Icon && iconPosition === 'right' && <Icon className="w-4 h-4 flex-shrink-0" />}
        </>
      )}
    </button>
  );
}
