import { useEffect, useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { AlertTriangle, X } from 'lucide-react';
import { adminApi } from '../api/admin';
import { authApi } from '../api/auth';

function formatCountdown(seconds: number): string {
  if (seconds <= 0) return '0:00';
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = seconds % 60;
  if (h > 0) return `${h}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
  return `${m}:${String(s).padStart(2, '0')}`;
}

export default function ImpersonateBanner() {
  const qc = useQueryClient();

  const { data: user } = useQuery({
    queryKey: ['me'],
    queryFn: authApi.me,
    staleTime: 60_000,
    retry: false,
  });

  const { data: active } = useQuery({
    queryKey: ['impersonate-active'],
    queryFn: adminApi.activeImpersonation,
    enabled: !!user?.impersonating,
    refetchInterval: 30_000,
  });

  const [secondsLeft, setSecondsLeft] = useState<number>(0);

  useEffect(() => {
    if (!active?.active || !active.expires_in_s) return;
    setSecondsLeft(active.expires_in_s);
    const tick = setInterval(() => {
      setSecondsLeft((s) => Math.max(0, s - 1));
    }, 1000);
    return () => clearInterval(tick);
  }, [active]);

  const stopMut = useMutation({
    mutationFn: adminApi.stopImpersonate,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['me'] });
      qc.invalidateQueries({ queryKey: ['impersonate-active'] });
      window.location.href = '/admin/tenants';
    },
  });

  if (!user?.impersonating) return null;

  return (
    <div
      role="alert"
      aria-live="polite"
      className="fixed top-0 left-0 right-0 z-[60] bg-red-600 text-white px-6 py-2.5 flex items-center justify-between shadow-2xl border-b-2 border-red-900"
    >
      <div className="flex items-center gap-3 min-w-0">
        <AlertTriangle className="w-4 h-4 flex-shrink-0 animate-pulse" />
        <div className="text-xs font-black uppercase tracking-widest min-w-0 flex items-center gap-3 flex-wrap">
          <span>⚠️ MODO IMPERSONATE</span>
          <span className="font-mono text-white/80 truncate">
            vendo como {user.email}
          </span>
          <span className="bg-red-900/60 px-2 py-0.5 rounded font-mono text-[11px]">
            {formatCountdown(secondsLeft)}
          </span>
          <span className="text-white/60 text-[10px]">
            (admin: {user.impersonator?.email})
          </span>
        </div>
      </div>
      <button
        onClick={() => stopMut.mutate()}
        disabled={stopMut.isPending}
        className="ml-3 flex items-center gap-1 bg-red-900 hover:bg-red-950 disabled:opacity-30 px-3 py-1.5 rounded-lg text-[10px] font-black uppercase tracking-widest transition-all"
      >
        <X className="w-3 h-3" />
        Sair desse modo
      </button>
    </div>
  );
}
