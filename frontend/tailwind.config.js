/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        dark: {
          950: '#070A12', // Main background
          900: '#0B1020', // Secondary background
          850: '#0F172A', // Card background
          800: '#1E293B',
          700: '#334155',
        },
        primary: {
          DEFAULT: '#6C63FF',
          50: '#F5F3FF',
          100: '#EDE9FE',
          200: '#DDD6FE',
          300: '#C4B5FD',
          400: '#A78BFA',
          500: '#8B5CF6',
          600: '#6C63FF',
          700: '#5B21B6',
          800: '#4C1D95',
          900: '#2E1065',
        },
        accent: {
          cyan: '#22D3EE',
          blue: '#38BDF8',
          purple: '#A855F7',
          emerald: '#22C55E',
          amber: '#F59E0B',
          rose: '#EF4444',
        }
      },
      boxShadow: {
        'glass': '0 20px 50px 0 rgba(0, 0, 0, 0.45)',
        'glass-hover': '0 25px 60px -10px rgba(108, 99, 255, 0.18)',
        'glow-primary': '0 0 25px -5px rgba(108, 99, 255, 0.45)',
        'glow-cyan': '0 0 25px -5px rgba(34, 211, 238, 0.4)',
        'glow-emerald': '0 0 25px -5px rgba(34, 197, 94, 0.4)',
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Roboto', 'sans-serif'],
      },
      animation: {
        'pulse-subtle': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'float': 'float 6s ease-in-out infinite',
      },
      keyframes: {
        float: {
          '0%, 100%': { transform: 'translateY(0)' },
          '50%': { transform: 'translateY(-8px)' },
        }
      }
    },
  },
  plugins: [],
}
