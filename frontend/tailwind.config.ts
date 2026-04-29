import type { Config } from 'tailwindcss';

// Paleta espelha o tema atual do dashboard.html para evitar mismatch visual.
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        'cigana-purple': '#7c3aed',
        'cigana-bg': '#0f172a',
        'cigana-surface': '#1e293b',
        'cigana-border': '#334155',
      },
    },
  },
  plugins: [],
} satisfies Config;
