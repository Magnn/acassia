import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// Servido pelo Flask em /builder/* em produção; em dev o Vite faz proxy de /api → Flask.
export default defineConfig({
  plugins: [react()],
  base: '/builder/',
  build: {
    outDir: 'dist',
    emptyOutDir: true,
    sourcemap: true,
  },
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:5000',
        changeOrigin: true,
      },
      '/media': 'http://localhost:5000',
      '/assets': 'http://localhost:5000',
    },
  },
});
