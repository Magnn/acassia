/**
 * hooks/useNotificationSound.ts — Reproduz som de notificação para novas mensagens
 *
 * Usa Web Audio API para gerar um tom suave sem precisar de arquivo de áudio.
 * O som é um "ding" curto e elegante (dois senos harmônicos com decay).
 */

import { useCallback, useRef } from 'react';

const STORAGE_KEY = 'meumisterio.inbox.sound_enabled';

export function useNotificationSound() {
  const ctxRef = useRef<AudioContext | null>(null);
  const lastPlayedRef = useRef(0);

  const isEnabled = () => {
    const saved = localStorage.getItem(STORAGE_KEY);
    return saved !== '0'; // enabled by default
  };

  const setEnabled = (v: boolean) => {
    localStorage.setItem(STORAGE_KEY, v ? '1' : '0');
  };

  const play = useCallback(() => {
    if (!isEnabled()) return;

    // Throttle: no máximo 1 som a cada 2s
    const now = Date.now();
    if (now - lastPlayedRef.current < 2000) return;
    lastPlayedRef.current = now;

    try {
      if (!ctxRef.current) {
        ctxRef.current = new AudioContext();
      }
      const ctx = ctxRef.current;

      // Nota fundamental (A5 = 880Hz)
      const osc1 = ctx.createOscillator();
      osc1.type = 'sine';
      osc1.frequency.setValueAtTime(880, ctx.currentTime);
      osc1.frequency.exponentialRampToValueAtTime(1320, ctx.currentTime + 0.08);

      // Harmônico (E6 = 1320Hz)
      const osc2 = ctx.createOscillator();
      osc2.type = 'sine';
      osc2.frequency.setValueAtTime(1320, ctx.currentTime + 0.08);

      // Envelope (volume decay)
      const gain = ctx.createGain();
      gain.gain.setValueAtTime(0.15, ctx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.4);

      osc1.connect(gain);
      osc2.connect(gain);
      gain.connect(ctx.destination);

      osc1.start(ctx.currentTime);
      osc2.start(ctx.currentTime + 0.08);
      osc1.stop(ctx.currentTime + 0.4);
      osc2.stop(ctx.currentTime + 0.4);
    } catch {
      // AudioContext not supported — silêncio
    }
  }, []);

  return { play, isEnabled, setEnabled };
}
