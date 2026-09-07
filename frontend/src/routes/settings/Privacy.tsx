import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Cookie, Download, Trash2, Smartphone,
  AlertTriangle, ShieldCheck, X, MapPin, Clock,
} from 'lucide-react';
import { api } from '../../api/client';
import { ApiError } from '../../api/client';
import { toast } from '../../lib/toast';

interface Session {
  id: number;
  ip_address: string | null;
  user_agent: string;
  geo_country: string | null;
  geo_city: string | null;
  is_current: boolean;
  created_at: string;
  last_activity_at: string;
  expires_at: string | null;
}

export default function PrivacySettings() {
  const qc = useQueryClient();
  const [showDeletion, setShowDeletion] = useState(false);
  const [confirmEmail, setConfirmEmail] = useState('');
  const [deletionReason, setDeletionReason] = useState('');

  const { data: consent } = useQuery({
    queryKey: ['consent'],
    queryFn: () => api.get<{ consents: Record<string, boolean> | null; policy_version: string; recorded_at?: string }>('/saas/consent'),
  });

  const { data: sessionsData, isLoading: sessionsLoading } = useQuery({
    queryKey: ['user-sessions'],
    queryFn: () => api.get<{ sessions: Session[] }>('/saas/sessions'),
  });

  const exportMut = useMutation({
    mutationFn: async () => {
      const res = await fetch('/saas/data-export', {
        method: 'POST',
        credentials: 'include',
      });
      if (!res.ok) throw new Error('export_failed');
      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `meumisterio-export-${new Date().toISOString().slice(0, 10)}.json`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    },
    onSuccess: () => toast.success('Download iniciado'),
    onError: () => toast.error('Erro ao exportar dados'),
  });

  const deletionMut = useMutation({
    mutationFn: () =>
      api.post<{ ok: boolean; hard_delete_after_days: number }>('/saas/data-deletion', {
        confirm_email: confirmEmail,
        reason: deletionReason,
      }),
    onSuccess: (data) => {
      toast.success(`Conta marcada pra deleção (${data.hard_delete_after_days}d window)`);
      setTimeout(() => { window.location.href = '/saas/login'; }, 2000);
    },
    onError: (e: unknown) => {
      const body = e instanceof ApiError ? (e.body as { error?: string }) : null;
      const msgs: Record<string, string> = {
        confirm_email_mismatch: 'Email não bate',
        already_deleted: 'Conta já marcada pra deleção',
      };
      toast.error(msgs[body?.error || ''] || 'Erro');
    },
  });

  const revokeSessionMut = useMutation({
    mutationFn: (id: number) =>
      api.post<{ ok: boolean }>(`/saas/sessions/${id}/revoke`),
    onSuccess: () => {
      toast.success('Sessão revogada');
      qc.invalidateQueries({ queryKey: ['user-sessions'] });
    },
  });

  const revokeAllMut = useMutation({
    mutationFn: () =>
      api.post<{ ok: boolean; revoked_count: number }>('/saas/sessions/revoke-all-others'),
    onSuccess: (data) => {
      toast.success(`${data.revoked_count} sessões revogadas`);
      qc.invalidateQueries({ queryKey: ['user-sessions'] });
    },
  });

  const sessions = sessionsData?.sessions ?? [];

  return (
    <div className="p-10 max-w-3xl mx-auto space-y-8">
      <div>
        <h1 className="text-2xl font-black tracking-tight">Privacidade</h1>
        <p className="text-secondary text-sm font-medium mt-1">
          LGPD: seus direitos sobre os dados que coletamos
        </p>
      </div>

      {/* Consent management */}
      <div className="bg-bg-surface border border-border rounded-3xl p-6 space-y-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-2xl bg-accent-amethyst/10 flex items-center justify-center">
            <Cookie className="w-5 h-5 text-accent-amethyst" />
          </div>
          <div>
            <h2 className="text-base font-black">Consentimentos</h2>
            <p className="text-xs text-secondary">
              Política versão: <span className="font-mono">{consent?.policy_version || '—'}</span>
            </p>
          </div>
        </div>
        {consent?.consents ? (
          <div className="grid grid-cols-2 gap-2">
            {Object.entries(consent.consents).map(([key, val]) => (
              <div
                key={key}
                className={`flex items-center justify-between p-3 rounded-xl border text-xs ${
                  val ? 'bg-emerald-500/5 border-emerald-500/20' : 'bg-bg-primary border-border'
                }`}
              >
                <span className="font-bold capitalize">{key.replace(/_/g, ' ')}</span>
                <span className={`font-mono ${val ? 'text-emerald-500' : 'text-secondary'}`}>
                  {val ? 'ON' : 'OFF'}
                </span>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-sm text-secondary">Nenhum consentimento registrado.</p>
        )}
        <p className="text-[11px] text-secondary">
          Reconfigure clicando no banner de cookies (atualize a página pra ver).
        </p>
      </div>

      {/* Sessions */}
      <div className="bg-bg-surface border border-border rounded-3xl p-6 space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-2xl bg-accent-amethyst/10 flex items-center justify-center">
              <Smartphone className="w-5 h-5 text-accent-amethyst" />
            </div>
            <div>
              <h2 className="text-base font-black">Sessões Ativas</h2>
              <p className="text-xs text-secondary">Dispositivos onde você está logado</p>
            </div>
          </div>
          {sessions.length > 1 && (
            <button
              onClick={() => revokeAllMut.mutate()}
              disabled={revokeAllMut.isPending}
              className="px-3 py-1.5 bg-red-500/10 hover:bg-red-500/20 border border-red-500/30 rounded-lg text-[10px] font-black uppercase tracking-widest text-red-400"
            >
              Revogar outras
            </button>
          )}
        </div>
        {sessionsLoading ? (
          <div className="text-secondary text-sm text-center py-4">Carregando...</div>
        ) : sessions.length === 0 ? (
          <div className="text-secondary text-sm text-center py-4">Nenhuma sessão</div>
        ) : (
          <div className="space-y-2">
            {sessions.map((s) => (
              <div
                key={s.id}
                className={`p-3 border rounded-xl flex items-center justify-between ${
                  s.is_current ? 'bg-accent-amethyst/5 border-accent-amethyst/20' : 'bg-bg-primary border-border'
                }`}
              >
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-xs font-bold">
                      {parseUserAgent(s.user_agent)}
                    </span>
                    {s.is_current && (
                      <span className="px-1.5 py-0.5 bg-emerald-500/20 rounded text-[9px] font-black uppercase tracking-widest text-emerald-500">
                        ATUAL
                      </span>
                    )}
                  </div>
                  <div className="flex items-center gap-3 text-[10px] text-secondary">
                    <span className="flex items-center gap-1">
                      <MapPin className="w-3 h-3" />
                      {s.ip_address || '?'}
                      {s.geo_city && ` · ${s.geo_city}`}
                    </span>
                    <span className="flex items-center gap-1">
                      <Clock className="w-3 h-3" />
                      {fmtRelative(s.last_activity_at)}
                    </span>
                  </div>
                </div>
                {!s.is_current && (
                  <button
                    onClick={() => revokeSessionMut.mutate(s.id)}
                    className="text-secondary hover:text-red-400"
                    title="Revogar"
                  >
                    <X className="w-4 h-4" />
                  </button>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* LGPD actions */}
      <div className="bg-bg-surface border border-border rounded-3xl p-6 space-y-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-2xl bg-accent-amethyst/10 flex items-center justify-center">
            <ShieldCheck className="w-5 h-5 text-accent-amethyst" />
          </div>
          <div>
            <h2 className="text-base font-black">Seus Direitos LGPD</h2>
            <p className="text-xs text-secondary">Exporte ou exclua seus dados</p>
          </div>
        </div>

        <button
          onClick={() => exportMut.mutate()}
          disabled={exportMut.isPending}
          className="w-full flex items-center justify-between p-4 bg-bg-primary hover:bg-accent-amethyst/5 border border-border hover:border-accent-amethyst/30 rounded-2xl transition-all group"
        >
          <div className="flex items-center gap-3">
            <Download className="w-4 h-4 text-secondary group-hover:text-accent-amethyst" />
            <div className="text-left">
              <div className="text-sm font-bold">Baixar meus dados</div>
              <div className="text-[11px] text-secondary">
                JSON com todos os dados pessoais associados à sua conta
              </div>
            </div>
          </div>
          <span className="text-[10px] font-black uppercase tracking-widest text-secondary">
            {exportMut.isPending ? 'Gerando...' : 'Exportar'}
          </span>
        </button>

        <button
          onClick={() => setShowDeletion(true)}
          className="w-full flex items-center justify-between p-4 bg-red-500/5 hover:bg-red-500/10 border border-red-500/20 rounded-2xl transition-all group"
        >
          <div className="flex items-center gap-3">
            <Trash2 className="w-4 h-4 text-red-400" />
            <div className="text-left">
              <div className="text-sm font-bold text-red-400">Excluir minha conta</div>
              <div className="text-[11px] text-secondary">
                Soft-delete com 30d de janela para reverter
              </div>
            </div>
          </div>
          <span className="text-[10px] font-black uppercase tracking-widest text-red-400">
            Excluir
          </span>
        </button>
      </div>

      {/* Deletion modal */}
      {showDeletion && (
        <div className="fixed inset-0 z-50 bg-black/70 flex items-center justify-center p-6">
          <div className="bg-bg-surface border border-red-500/30 rounded-3xl p-8 max-w-lg w-full space-y-5">
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 rounded-2xl bg-red-500/10 flex items-center justify-center">
                <AlertTriangle className="w-6 h-6 text-red-400" />
              </div>
              <h3 className="text-lg font-black">Excluir minha conta</h3>
            </div>

            <div className="bg-red-500/5 border border-red-500/20 rounded-xl p-3 text-xs text-red-300">
              <strong>Atenção:</strong> sua conta entra em deleção por 30 dias.
              Após esse prazo, seus dados são removidos permanentemente —
              não há como recuperar.
            </div>

            <div>
              <label className="text-[10px] uppercase font-black tracking-widest text-secondary mb-1.5 block">
                Motivo (opcional)
              </label>
              <textarea
                value={deletionReason}
                onChange={(e) => setDeletionReason(e.target.value)}
                rows={2}
                placeholder="Conta-nos por que está saindo..."
                className="w-full bg-bg-primary border border-border rounded-xl px-3 py-2 text-sm placeholder:text-secondary focus:outline-none resize-none"
              />
            </div>

            <div>
              <label className="text-[10px] uppercase font-black tracking-widest text-secondary mb-1.5 block">
                Confirme digitando seu email
              </label>
              <input
                type="email"
                value={confirmEmail}
                onChange={(e) => setConfirmEmail(e.target.value)}
                className="w-full bg-bg-primary border border-border rounded-xl px-3 py-2 text-sm font-mono focus:outline-none focus:border-red-500/50"
              />
            </div>

            <div className="flex gap-3">
              <button
                onClick={() => { setShowDeletion(false); setConfirmEmail(''); setDeletionReason(''); }}
                className="flex-1 px-5 py-3 bg-bg-primary border border-border rounded-2xl text-sm font-bold"
              >
                Cancelar
              </button>
              <button
                onClick={() => deletionMut.mutate()}
                disabled={!confirmEmail || deletionMut.isPending}
                className="flex-1 px-5 py-3 bg-red-600 hover:bg-red-500 disabled:opacity-30 text-white rounded-2xl text-sm font-black uppercase tracking-widest"
              >
                {deletionMut.isPending ? 'Processando...' : 'Excluir conta'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function parseUserAgent(ua: string): string {
  if (!ua) return 'Dispositivo desconhecido';
  // Heurística simples
  if (/iPhone/i.test(ua)) return 'iPhone';
  if (/iPad/i.test(ua)) return 'iPad';
  if (/Android/i.test(ua)) return 'Android';
  if (/Macintosh/i.test(ua)) return 'Mac';
  if (/Windows/i.test(ua)) return 'Windows';
  if (/Linux/i.test(ua)) return 'Linux';
  return 'Dispositivo desconhecido';
}

function fmtRelative(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const min = Math.floor(diff / 60000);
  if (min < 1) return 'agora';
  if (min < 60) return `${min}m atrás`;
  const h = Math.floor(min / 60);
  if (h < 24) return `${h}h atrás`;
  return `${Math.floor(h / 24)}d atrás`;
}
