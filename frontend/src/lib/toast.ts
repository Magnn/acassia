import { create } from 'zustand';

export type ToastKind = 'success' | 'error' | 'info' | 'warning';

export interface Toast {
  id: number;
  kind: ToastKind;
  message: string;
}

interface ToastStore {
  toasts: Toast[];
  push: (kind: ToastKind, message: string, ms?: number) => number;
  dismiss: (id: number) => void;
}

let _seq = 0;

export const useToastStore = create<ToastStore>((set) => ({
  toasts: [],
  push: (kind, message, ms = 3500) => {
    _seq += 1;
    const id = _seq;
    set((s) => ({ toasts: [...s.toasts, { id, kind, message }] }));
    if (ms > 0) {
      window.setTimeout(() => {
        set((s) => ({ toasts: s.toasts.filter((t) => t.id !== id) }));
      }, ms);
    }
    return id;
  },
  dismiss: (id) =>
    set((s) => ({ toasts: s.toasts.filter((t) => t.id !== id) })),
}));

/** Helper imperativo — uso fora de componentes (mutations, errors, etc). */
export const toast = {
  success: (m: string, ms?: number) => useToastStore.getState().push('success', m, ms),
  error: (m: string, ms?: number) => useToastStore.getState().push('error', m, ms),
  info: (m: string, ms?: number) => useToastStore.getState().push('info', m, ms),
  warning: (m: string, ms?: number) => useToastStore.getState().push('warning', m, ms),
};
