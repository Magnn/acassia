import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  AlertTriangle, CheckCircle2, ExternalLink, Phone, Plus, QrCode,
  RefreshCw, Save, ShieldCheck, Star, Trash2, Unplug, X, Zap,
} from 'lucide-react';
import { api } from '../../api/client';
import { toast } from '../../lib/toast';
import { WizardModal } from './WizardModal';

/* ── WhatsApp SVG Logo ─────────────────────── */
const WaLogo = ({ className = 'w-8 h-8' }: { className?: string }) => (
  <svg viewBox="0 0 24 24" className={className} fill="currentColor">
    <path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413z"/>
  </svg>
);

const MetaLogo = ({ className = 'w-5 h-5' }: { className?: string }) => (
  <svg viewBox="0 0 512 512" className={className} fill="currentColor">
    <path d="M412.7 163.2c-28.3 0-51.7 25.9-82.7 75.2l-13.6 21.5-12.2-20.4c-36.1-60.3-60-76.3-91.8-76.3-35.3 0-65.7 28.4-89.4 82C98.7 300 83.6 377.1 83.6 420c0 31.5 11.1 51.7 33.6 51.7 14.9 0 26.6-8.2 44.9-37.7l41-66.3 8.9-14.6 4.8-8 8.6-14.4c17.4-29.4 27.2-42.2 42.3-42.2 12.2 0 20.6 9.9 33 33.9l6 11.8 4.1 8.3 4.1 8.4 8.4 17.3c18.3 37.3 30.3 52 51.2 52 22.5 0 33.6-20.2 33.6-51.7 0-43-14.7-120-53.4-175.1-23.7-33.8-51.6-57.9-77.7-57.9"/>
  </svg>
);

interface Device {
  id: number; nickname: string; provider: string;
  phone_display: string | null; connected: boolean;
  connection_state: string | null; is_primary: boolean;
  groups_count: number; flow_mode?: 'static_funnel' | 'ai_agent' | 'flow_builder';
}

export default function Devices() {
  const qc = useQueryClient();
  const [showAdd, setShowAdd] = useState(false);
  const emptyForm = { nickname: '', provider: 'meta_cloud', phone_display: '', meta_phone_number_id: '', meta_waba_id: '', meta_access_token: '', evolution_server_url: '', evolution_instance: '', evolution_api_key: '' };
  const [form, setForm] = useState(emptyForm);

  const { data } = useQuery({ queryKey: ['devices'], queryFn: () => api.get<any>('/saas/devices/') });
  const devices: Device[] = data?.devices || [];

  const createMut = useMutation({
    mutationFn: (d: any) => api.post('/saas/devices/', d),
    onSuccess: () => { toast.success('Dispositivo criado!'); qc.invalidateQueries({ queryKey: ['devices'] }); setShowAdd(false); setForm(emptyForm); },
    onError: (e: any) => toast.error(e?.message || 'Erro ao criar'),
  });
  const deleteMut = useMutation({
    mutationFn: (id: number) => api.del(`/saas/devices/${id}`),
    onSuccess: () => { toast.success('Removido'); qc.invalidateQueries({ queryKey: ['devices'] }); },
  });
  const primaryMut = useMutation({
    mutationFn: (id: number) => api.post(`/saas/devices/${id}/set-primary`, {}),
    onSuccess: () => { toast.success('Principal definido'); qc.invalidateQueries({ queryKey: ['devices'] }); },
  });
  const flowModeMut = useMutation({
    mutationFn: ({ id, mode }: { id: number; mode: string }) =>
      api.post(`/saas/devices/${id}/flow-mode`, { flow_mode: mode }),
    onSuccess: (_, vars) => {
      toast.success(
        vars.mode === 'static_funnel'
          ? '⚡ Modo definido: Funil Estático (Meu Mistério)!'
          : '🤖 Modo definido: Agente de IA Conversacional!'
      );
      qc.invalidateQueries({ queryKey: ['devices'] });
    },
    onError: (e: any) => toast.error(e?.message || 'Erro ao alterar modo'),
  });

  return (
    <div className="px-8 py-8 max-w-6xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div className="flex items-center gap-4">
          <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-[#25D366] to-[#128C7E] flex items-center justify-center shadow-lg shadow-[#25D366]/20">
            <WaLogo className="w-7 h-7 text-white" />
          </div>
          <div>
            <h2 className="font-display text-3xl text-primary tracking-tight">Meus Dispositivos</h2>
            <p className="text-xs text-secondary mt-0.5">{devices.length} número{devices.length !== 1 ? 's' : ''} conectado{devices.length !== 1 ? 's' : ''}</p>
          </div>
        </div>
        <button onClick={() => setShowAdd(true)}
          className="flex items-center gap-2 px-5 py-2.5 bg-gradient-to-r from-[#25D366] to-[#128C7E] text-white rounded-xl text-sm font-bold hover:shadow-lg hover:shadow-[#25D366]/20 transition-all">
          <Plus className="w-4 h-4" /> Novo Dispositivo
        </button>
      </div>

      {/* Empty state */}
      {devices.length === 0 && (
        <div className="text-center py-20 bg-bg-surface border border-border rounded-2xl">
          <Phone className="w-12 h-12 text-secondary mx-auto mb-4 opacity-30" />
          <h3 className="text-lg font-bold text-primary mb-2">Nenhum dispositivo conectado</h3>
          <p className="text-xs text-secondary mb-6">Adicione seu primeiro número WhatsApp para começar.</p>
          <button onClick={() => setShowAdd(true)}
            className="px-6 py-3 bg-gradient-to-r from-[#25D366] to-[#128C7E] text-white rounded-xl text-sm font-bold inline-flex items-center gap-2">
            <Plus className="w-4 h-4" /> Adicionar Dispositivo
          </button>
        </div>
      )}

      {/* Device cards grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        {devices.map(d => (
          <DeviceCard key={d.id} device={d}
            onDelete={() => deleteMut.mutate(d.id)}
            onSetPrimary={() => primaryMut.mutate(d.id)}
            onSetFlowMode={(mode) => flowModeMut.mutate({ id: d.id, mode })} />
        ))}
      </div>

      {/* Add Device Modal */}
      {showAdd && <WizardModal onClose={() => setShowAdd(false)} />}
    </div>
  );
}

/* ── Reusable Field ──────────────────────────── */
function Field({ label, value, onChange, placeholder }: { label: string; value: string; onChange: (v: string) => void; placeholder: string }) {
  return (
    <div>
      <label className="text-xs font-bold text-secondary block mb-1">{label}</label>
      <input value={value} onChange={e => onChange(e.target.value)} placeholder={placeholder}
        className="w-full px-4 py-2.5 bg-bg-primary border border-border rounded-xl text-sm text-primary" />
    </div>
  );
}

/* ── Provider Button ─────────────────────────── */
function ProviderBtn({ label, sub, active, onClick, color }: { id: string; label: string; sub: string; active: boolean; onClick: () => void; color: string }) {
  const cls = active
    ? color === 'green'
      ? 'bg-gradient-to-br from-[#0a1a12] to-[#0f2318] border-[#25D366]/30 ring-1 ring-[#25D366]/20'
      : 'bg-gradient-to-br from-purple-900/30 to-purple-950/30 border-purple-500/30 ring-1 ring-purple-500/20'
    : 'bg-bg-primary border-border hover:border-border';
  return (
    <button type="button" onClick={onClick} className={`text-left p-4 rounded-xl border transition-all ${cls}`}>
      <div className="text-sm font-bold text-primary">{label}</div>
      <div className="text-[10px] text-secondary">{sub}</div>
    </button>
  );
}

function DeviceCard({
  device: d,
  onDelete,
  onSetPrimary,
  onSetFlowMode,
}: {
  device: Device;
  onDelete: () => void;
  onSetPrimary: () => void;
  onSetFlowMode: (mode: string) => void;
}) {
  const { data: liveStatus, refetch } = useQuery({
    queryKey: ['device-status', d.id],
    queryFn: () => api.get<any>(`/saas/devices/${d.id}/status`),
    refetchInterval: 20000,
  });
  const isConnected = liveStatus?.connected ?? d.connected;
  const isConflict = (liveStatus?.connection_state === 'CONFLICT' || d.connection_state === 'CONFLICT');
  const isMeta = d.provider === 'meta_cloud' || d.provider === 'coex';
  const isOpenWA = d.provider === 'openwa';
  const currentMode = d.flow_mode || 'static_funnel';

  const restartMut = useMutation({
    mutationFn: () => api.post(`/saas/devices/${d.id}/restart`, {}),
    onSuccess: () => {
      toast.success('Comando de reinício enviado!');
      refetch();
    },
    onError: (e: any) => toast.error(e?.message || 'Falha ao reiniciar sessão'),
  });

  return (
    <div className="relative rounded-[24px] bg-[#F2F4F7] p-8 shadow-[0_12px_40px_rgba(0,0,0,0.08)] transition-all group overflow-hidden max-w-[600px]">
      
      {d.is_primary && (
        <div className="absolute top-5 right-5 flex items-center gap-1 px-3 py-1 rounded-full bg-amber-500/10 border border-amber-500/20">
          <Star className="w-3.5 h-3.5 text-amber-500 fill-amber-500" />
          <span className="text-[10px] font-bold text-amber-600 uppercase tracking-wider">Principal</span>
        </div>
      )}

      {/* Conflict Alert Banner */}
      {isConflict && (
        <div className="mb-6 p-4 rounded-2xl bg-rose-500/10 border border-rose-500/30 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="flex items-start gap-3">
            <AlertTriangle className="w-5 h-5 text-rose-600 flex-shrink-0 mt-0.5" />
            <div>
              <h4 className="text-sm font-bold text-rose-900">Conflito de Sessão Detectado</h4>
              <p className="text-xs text-rose-700 mt-0.5">
                O WhatsApp Web foi aberto em outro navegador ou computador. Desconecte lá e reinicie aqui para reativar o robô.
              </p>
            </div>
          </div>
          <button
            onClick={() => restartMut.mutate()}
            disabled={restartMut.isPending}
            className="px-4 py-2 bg-rose-600 hover:bg-rose-700 text-white text-xs font-bold rounded-xl shadow-sm transition flex items-center gap-1.5 self-end sm:self-center disabled:opacity-50 flex-shrink-0"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${restartMut.isPending ? 'animate-spin' : ''}`} />
            Reconectar
          </button>
        </div>
      )}

      {/* Top: WA Logo + Phone Number */}
      <div className="flex items-center gap-5 mb-8">
        <div className="relative">
          <div className="w-[56px] h-[56px] bg-white rounded-full shadow-[0_4px_12px_rgba(0,0,0,0.08)] flex items-center justify-center">
            <svg viewBox="0 0 24 24" className="w-[42px] h-[42px] text-[#25D366] fill-current">
              <path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.888-.788-1.489-1.761-1.662-2.06-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51h-.57c-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413z"/>
            </svg>
          </div>
        </div>
        <div className="text-[34px] font-bold text-[#1D2B36] tracking-tight font-sans">
          {d.phone_display || d.nickname || 'Sem número'}
        </div>
      </div>

      {/* Middle: Status + Disconnect */}
      <div className="flex items-center justify-between mb-8">
        <div className="flex items-center gap-3">
          {isConflict ? (
            <>
              <div className="w-[16px] h-[16px] rounded-full bg-rose-500 shadow-[0_0_16px_5px_rgba(244,63,94,0.5)] animate-bounce" />
              <span className="text-[22px] font-medium text-rose-600">Conflito de Sessão</span>
            </>
          ) : isConnected ? (
            <>
              <div className="w-[16px] h-[16px] rounded-full bg-[#25D366] shadow-[0_0_16px_5px_rgba(37,211,102,0.5)] animate-pulse" />
              <span className="text-[22px] font-medium text-[#25D366]">Conectado</span>
            </>
          ) : (
            <>
              <div className="w-[16px] h-[16px] rounded-full bg-amber-400 shadow-[0_0_16px_5px_rgba(251,191,36,0.5)]" />
              <span className="text-[22px] font-medium text-amber-500">Desconectado</span>
            </>
          )}
        </div>
        
        <button onClick={() => { if (confirm(`Desconectar "${d.nickname}"?`)) onDelete(); }}
          className="flex items-center gap-2.5 px-6 py-3 bg-white border border-gray-200 rounded-[12px] text-[16px] font-medium text-[#1D2B36] hover:bg-gray-50 hover:border-gray-300 transition-all shadow-sm">
          <Unplug className="w-5 h-5 text-gray-800" strokeWidth={2} /> Desconectar
        </button>
      </div>

      {/* Flow Mode Switcher: Static Funnel vs AI Agent */}
      <div className="mt-4 pt-5 border-t border-gray-300/80 mb-6">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <Zap className="w-4 h-4 text-emerald-600" />
            <span className="text-xs font-black uppercase tracking-wider text-gray-700">
              Modo de Atendimento deste Número
            </span>
          </div>
          <span className="text-xs font-bold px-2.5 py-0.5 rounded-full bg-white border border-gray-200 text-gray-800 shadow-sm">
            {currentMode === 'ai_agent' ? '🤖 Agente de IA' : '⚡ Funil Estático'}
          </span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <button
            type="button"
            onClick={() => onSetFlowMode('static_funnel')}
            className={`p-3.5 rounded-xl border text-left transition-all ${
              currentMode === 'static_funnel'
                ? 'bg-emerald-500/10 border-emerald-500 ring-2 ring-emerald-500/20 shadow-sm'
                : 'bg-white border-gray-200 hover:border-gray-300 text-gray-600'
            }`}
          >
            <div className="flex items-center justify-between">
              <span className="font-bold text-sm text-[#1D2B36] flex items-center gap-1.5">
                ⚡ Funil Estático
              </span>
              {currentMode === 'static_funnel' && (
                <CheckCircle2 className="w-4 h-4 text-emerald-600" />
              )}
            </div>
            <p className="text-[11px] text-gray-500 mt-1 leading-snug">
              7 etapas fixas estruturadas (áudios, tarot, quiz e checkout).
            </p>
          </button>

          <button
            type="button"
            onClick={() => onSetFlowMode('ai_agent')}
            className={`p-3.5 rounded-xl border text-left transition-all ${
              currentMode === 'ai_agent'
                ? 'bg-purple-500/10 border-purple-500 ring-2 ring-purple-500/20 shadow-sm'
                : 'bg-white border-gray-200 hover:border-gray-300 text-gray-600'
            }`}
          >
            <div className="flex items-center justify-between">
              <span className="font-bold text-sm text-[#1D2B36] flex items-center gap-1.5">
                🤖 Agente de IA
              </span>
              {currentMode === 'ai_agent' && (
                <CheckCircle2 className="w-4 h-4 text-purple-600" />
              )}
            </div>
            <p className="text-[11px] text-gray-500 mt-1 leading-snug">
              IA autônoma Gemini: conversa livre, tira dúvidas e qualifica.
            </p>
          </button>
        </div>
      </div>

      {/* Bottom Right: Meta / OpenWA / Evolution Logo */}
      <div className="flex justify-end mt-4">
        <div className="flex flex-col items-end">
          {isMeta ? (
            <>
              <div className="flex items-center gap-2 mb-1">
                <svg viewBox="0 0 36 36" className="w-[32px] h-[32px] text-[#0866FF] fill-current">
                  <path d="M19.78,24.11a2.83,2.83,0,0,1-2.22-1.07l-3.24-4L11,15a4.34,4.34,0,0,0-6.17,0A4.47,4.47,0,0,0,3.58,18a4.47,4.47,0,0,0,1.25,3A4.34,4.34,0,0,0,11,21l3.35,4.06a6.83,6.83,0,0,0,10.6,0A6.83,6.83,0,0,0,25,15h0a6.83,6.83,0,0,0-10.6,0L13.11,16.63l1.83,2.23L16.22,17.3a4.34,4.34,0,0,1,6.17,0,4.47,4.47,0,0,1,0,6A4.34,4.34,0,0,1,19.78,24.11Z" />
                </svg>
                <span className="text-[28px] font-bold text-[#1D2B36] tracking-tight">Meta</span>
              </div>
              <span className="text-[14px] font-medium text-[#0866FF]">Official Meta API Connection</span>
            </>
          ) : isOpenWA ? (
            <>
              <div className="flex items-center gap-2 mb-1">
                <div className="w-7 h-7 rounded-lg bg-emerald-600 text-white flex items-center justify-center font-bold text-xs shadow-sm">WA</div>
                <span className="text-[28px] font-bold text-[#1D2B36] tracking-tight">OpenWA</span>
              </div>
              <span className="text-[14px] font-medium text-emerald-600">Self-Hosted Gateway</span>
            </>
          ) : (
            <>
              <div className="flex items-center gap-2 mb-1">
                <QrCode className="w-[32px] h-[32px] text-purple-600" />
                <span className="text-[28px] font-bold text-[#1D2B36] tracking-tight">Evolution</span>
              </div>
              <span className="text-[14px] font-medium text-purple-600">QR Code Connection</span>
            </>
          )}
        </div>
      </div>
      
      {/* Set Primary Button (Hidden unless hovered) */}
      {!d.is_primary && (
        <button onClick={onSetPrimary} className="absolute bottom-6 left-8 text-[12px] font-bold text-gray-400 hover:text-gray-700 underline opacity-0 group-hover:opacity-100 transition-opacity">
          Definir principal
        </button>
      )}
    </div>
  );
}
