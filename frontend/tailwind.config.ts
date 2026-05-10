import type { Config } from 'tailwindcss'

// Palette locked from decade.com. No color accent on purpose — restraint
// is the brand. Status (pass/fail/conflict) is rendered via type, icons,
// and labels, never hue.
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        bg: '#000000',
        surface: '#0A0A0A',
        'surface-2': '#141414',
        'surface-3': '#1C1C1C',
        border: '#262626',
        'border-strong': '#3A3A3A',
        ink: {
          1: '#FFFFFF',
          2: '#B5B5B5',
          3: '#6B6B6B',
          4: '#3A3A3A',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'ui-monospace', 'SFMono-Regular', 'monospace'],
      },
      letterSpacing: {
        tightest: '-0.04em',
        tighter: '-0.02em',
        tight: '-0.01em',
      },
      fontSize: {
        // Display sizes use clamp for fluid type
        'display-1': ['clamp(1.75rem, 3vw, 2.5rem)', { lineHeight: '1.1', letterSpacing: '-0.02em', fontWeight: '600' }],
        'display-2': ['clamp(1.375rem, 2.25vw, 1.875rem)', { lineHeight: '1.15', letterSpacing: '-0.02em', fontWeight: '600' }],
        'display-3': ['clamp(1.125rem, 1.75vw, 1.375rem)', { lineHeight: '1.2', letterSpacing: '-0.015em', fontWeight: '600' }],
      },
      maxWidth: {
        prose: '68ch',
        page: '76rem',
      },
      transitionTimingFunction: {
        decade: 'cubic-bezier(0.2, 0.8, 0.2, 1)',
      },
      keyframes: {
        'fade-in': {
          '0%': { opacity: '0', transform: 'translateY(4px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
      },
      animation: {
        'fade-in': 'fade-in 0.4s cubic-bezier(0.2, 0.8, 0.2, 1) both',
      },
    },
  },
  plugins: [],
} satisfies Config
