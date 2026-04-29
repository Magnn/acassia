import type { Config } from 'tailwindcss';

/**
 * Sibila brand tokens — "Noite Considerada".
 *
 * Os tokens cigana-* são preservados como aliases para os mesmos valores
 * (compat retroativo enquanto o codebase migra). Use sibila-* em código novo.
 */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        // ── Sibila (canonical) ──────────────────────────────────────
        sibila: {
          onyx: '#0b0817',
          obsidian: '#14101e',
          veil: '#1c1828',
          mist: '#2a2538',
          stone: '#3a3447',
          amethyst: '#7c6a99',
          'amethyst-dim': '#5a4d72',
          ember: '#d4a574',
          'ember-deep': '#a8845c',
          rose: '#b46e7c',
          sage: '#7a9b88',
          crimson: '#a93c3c',
          moonlight: '#f3eee5',
          fog: '#a8a3b3',
          smoke: '#6b6677',
        },
        // ── Cigana (aliases legados) ────────────────────────────────
        'cigana-bg': '#0b0817',
        'cigana-surface': '#14101e',
        'cigana-border': '#2a2538',
        'cigana-purple': '#7c6a99',
      },
      fontFamily: {
        sans: ['Inter', 'ui-sans-serif', 'system-ui', '-apple-system', 'Segoe UI', 'sans-serif'],
        display: ['Fraunces', 'Georgia', 'ui-serif', 'serif'],
      },
      letterSpacing: {
        'wider-2': '0.08em',
        'widest-2': '0.18em',
      },
      boxShadow: {
        'glow-amethyst': '0 0 24px -4px rgba(124, 106, 153, 0.45)',
        'glow-ember': '0 0 24px -4px rgba(212, 165, 116, 0.4)',
        'inset-veil': 'inset 0 1px 0 rgba(255, 255, 255, 0.04)',
      },
      animation: {
        'pulse-soft': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
      },
    },
  },
  plugins: [],
} satisfies Config;
