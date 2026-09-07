import { AlertCircle, AlertTriangle, CheckCircle2, Info, X } from 'lucide-react';
import { useToastStore, type ToastKind } from '../lib/toast';

interface KindMeta {
  Icon: typeof CheckCircle2;
  cls: string;
}

const KIND: Record<ToastKind, KindMeta> = {
  success: {
    Icon: CheckCircle2,
    cls: 'border-emerald-500/40 bg-emerald-950/60 text-emerald-100',
  },
  error: {
    Icon: AlertCircle,
    cls: 'border-red-500/40 bg-red-950/60 text-red-100',
  },
  warning: {
    Icon: AlertTriangle,
    cls: 'border-amber-500/40 bg-amber-950/60 text-amber-100',
  },
  info: {
    Icon: Info,
    cls: 'border-sky-500/40 bg-sky-950/60 text-sky-100',
  },
};

export default function Toaster() {
  const toasts = useToastStore((s) => s.toasts);
  const dismiss = useToastStore((s) => s.dismiss);

  return (
    <div className="fixed top-4 right-4 z-[1000] space-y-2 max-w-sm pointer-events-none">
      {toasts.map((t) => {
        const meta = KIND[t.kind];
        return (
          <div
            key={t.id}
            className={`pointer-events-auto rounded-lg border px-3 py-2.5 shadow-xl backdrop-blur-sm flex items-start gap-2 text-sm animate-slide-in-right ${meta.cls}`}
          >
            <meta.Icon className="w-4 h-4 mt-0.5 flex-shrink-0" />
            <span className="flex-1 break-words">{t.message}</span>
            <button
              onClick={() => dismiss(t.id)}
              className="opacity-60 hover:opacity-100 -mr-1 -mt-1 p-0.5"
              title="Fechar"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          </div>
        );
      })}
    </div>
  );
}
