import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { QrCode, RefreshCw, AlertTriangle, CheckCircle2, Unplug, ShieldCheck, Signal, Phone, ExternalLink, Zap, Plus, Star, Trash2, X, Save } from 'lucide-react';
import { api } from '../api/client';
import { toast } from '../lib/toast';

const WaLogo = ({ className = 'w-8 h-8' }: { className?: string }) => (
  <svg viewBox="0 0 24 24" className={className} fill="currentColor">
    <path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413z"/>
  </svg>
);

const MetaLogo = ({ className = 'w-4 h-4' }: { className?: string }) => (
  <svg viewBox="0 0 512 512" className={className} fill="currentColor">
    <path d="M412.7 163.2c-28.3 0-51.7 25.9-82.7 75.2l-13.6 21.5-12.2-20.4c-36.1-60.3-60-76.3-91.8-76.3-35.3 0-65.7 28.4-89.4 82C98.7 300 83.6 377.1 83.6 420c0 31.5 11.1 51.7 33.6 51.7 14.9 0 26.6-8.2 44.9-37.7l41-66.3 8.9-14.6 4.8-8 8.6-14.4c17.4-29.4 27.2-42.2 42.3-42.2 12.2 0 20.6 9.9 33 33.9l6 11.8 4.1 8.3 4.1 8.4 8.4 17.3c18.3 37.3 30.3 52 51.2 52 22.5 0 33.6-20.2 33.6-51.7 0-43-14.7-120-53.4-175.1-23.7-33.8-51.6-57.9-77.7-57.9"/>
  </svg>
);

interface Device { id: number; nickname: string; provider: string; phone_display: string | null; connected: boolean; connection_state: string | null; is_primary: boolean; groups_count: number; created_at: string | null; flow_mode?: 'static_funnel' | 'ai_agent' | 'flow_builder'; }

export default function WAConnection() {
  const qc = useQueryClient();
  const [showAdd, setShowAdd] = useState(false);
  const [showMetaModal, setShowMetaModal] = useState(false);
  const [form, setForm] = useState({ nickname: '', provider: 'meta_cloud', phone_display: '', meta_phone_number_id: '', meta_waba_id: '', meta_access_token: '', evolution_server_url: '', evolution_instance: '', evolution_api_key: '' });

  const { data } = useQuery({ queryKey: ['devices'], queryFn: () => api.get<any>('/saas/devices/') });
  const devices: Device[] = data?.devices || [];

  const { data: metaConfig } = useQuery({
    queryKey: ['meta-embedded-config'],
    queryFn: () => api.get<any>('/saas/wa/embedded-signup/config'),
  });

  const createMut = useMutation({
    mutationFn: (d: any) => api.post('/saas/devices/', d),
    onSuccess: () => { toast.success('Dispositivo criado!'); qc.invalidateQueries({ queryKey: ['devices'] }); setShowAdd(false); setForm({ nickname: '', provider: 'meta_cloud', phone_display: '', meta_phone_number_id: '', meta_waba_id: '', meta_access_token: '', evolution_server_url: '', evolution_instance: '', evolution_api_key: '' }); },
    onError: (e: any) => toast.error(e?.message || 'Erro'),
  });
  const deleteMut = useMutation({
    mutationFn: (id: number) => api.del(`/saas/devices/${id}`),
    onSuccess: () => { toast.success('Removido'); qc.invalidateQueries({ queryKey: ['devices'] }); },
  });
  const primaryMut = useMutation({
    mutationFn: (id: number) => api.post(`/saas/devices/${id}/set-primary`, {}),
    onSuccess: () => { toast.success('Dispositivo principal definido!'); qc.invalidateQueries({ queryKey: ['devices'] }); },
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
    <div className="px-8 py-8 max-w-[1100px] mx-auto min-h-screen">
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 mb-10">
        <div className="flex items-center gap-4">
          <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-[#25D366] to-[#128C7E] flex items-center justify-center shadow-lg shadow-[#25D366]/20">
            <WaLogo className="w-7 h-7 text-white" />
          </div>
          <div>
            <h1 className="font-display text-3xl text-primary tracking-tight">Conexão WhatsApp</h1>
            <p className="text-xs text-secondary mt-0.5">{devices.length} dispositivo{devices.length !== 1 ? 's' : ''} cadastrado{devices.length !== 1 ? 's' : ''}</p>
          </div>
        </div>
        <div className="flex items-center gap-2.5">
          <button
            onClick={() => setShowMetaModal(true)}
            className="flex items-center gap-2 px-4 py-2.5 bg-blue-600/10 hover:bg-blue-600/20 text-blue-400 border border-blue-500/30 rounded-xl text-sm font-bold transition-all shadow-sm"
          >
            <MetaLogo className="w-4 h-4" /> Conectar via Meta
          </button>
          <button onClick={() => setShowAdd(true)} className="flex items-center gap-2 px-5 py-2.5 bg-gradient-to-r from-[#25D366] to-[#128C7E] text-white rounded-xl text-sm font-bold hover:shadow-lg hover:shadow-[#25D366]/20 transition-all">
            <Plus className="w-4 h-4" /> Novo Dispositivo
          </button>
        </div>
      </div>

      {/* Grid de dispositivos */}
      {devices.length === 0 && (
        <div className="text-center py-20 bg-bg-surface border border-border rounded-2xl">
          <Phone className="w-12 h-12 text-secondary mx-auto mb-4 opacity-30" />
          <h3 className="text-lg font-bold text-primary mb-2">Nenhum dispositivo conectado</h3>
          <p className="text-xs text-secondary mb-6">Adicione seu primeiro número WhatsApp para começar.</p>
          <button onClick={() => setShowAdd(true)} className="px-6 py-3 bg-gradient-to-r from-[#25D366] to-[#128C7E] text-white rounded-xl text-sm font-bold">
            <Plus className="w-4 h-4 inline mr-2" /> Adicionar Dispositivo
          </button>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        {devices.map(d => (
          <DeviceCard
            key={d.id}
            device={d}
            onDelete={() => deleteMut.mutate(d.id)}
            onSetPrimary={() => primaryMut.mutate(d.id)}
            onSetFlowMode={(mode) => flowModeMut.mutate({ id: d.id, mode })}
          />
        ))}
      </div>

      {/* Modal Novo Dispositivo */}
      {showAdd && (
        <div className="fixed inset-0 z-[100] bg-black/70 backdrop-blur-sm flex items-center justify-center p-4" onClick={() => setShowAdd(false)}>
          <div onClick={e => e.stopPropagation()} className="bg-bg-surface border border-border rounded-2xl shadow-2xl max-w-lg w-full overflow-hidden">
            <header className="flex items-center justify-between px-6 py-4 border-b border-border">
              <h3 className="font-display text-xl text-primary">Novo Dispositivo</h3>
              <button onClick={() => setShowAdd(false)} className="p-1.5 rounded-lg hover:bg-bg-primary text-secondary"><X className="w-4 h-4" /></button>
            </header>
            <div className="p-6 space-y-4">
              <div>
                <label className="text-xs font-bold text-secondary block mb-1">Apelido *</label>
                <input value={form.nickname} onChange={e => setForm(f => ({ ...f, nickname: e.target.value }))} placeholder="Ex: Spanda VIP, Suporte, Vendas..." className="w-full px-4 py-2.5 bg-bg-primary border border-border rounded-xl text-sm text-primary" />
              </div>
              <div>
                <label className="text-xs font-bold text-secondary block mb-1">Número do chip</label>
                <input value={form.phone_display} onChange={e => setForm(f => ({ ...f, phone_display: e.target.value }))} placeholder="+55 11 99999-0000" className="w-full px-4 py-2.5 bg-bg-primary border border-border rounded-xl text-sm text-primary" />
              </div>
              <div>
                <label className="text-xs font-bold text-secondary block mb-2">Provedor</label>
                <div className="grid grid-cols-2 gap-3">
                  {[{ id: 'meta_cloud', label: 'Meta Cloud API', sub: 'Oficial', color: 'from-[#0a1a12] to-[#0f2318]', border: 'border-[#25D366]/30' },
                    { id: 'evolution', label: 'Evolution API', sub: 'QR Code', color: 'from-purple-900/30 to-purple-950/30', border: 'border-purple-500/30' }]
                    .map(p => (
                    <button key={p.id} type="button" onClick={() => setForm(f => ({ ...f, provider: p.id }))}
                      className={`text-left p-4 rounded-xl border transition-all ${form.provider === p.id ? `bg-gradient-to-br ${p.color} ${p.border} ring-1 ring-white/10` : 'bg-bg-primary border-border hover:border-border'}`}>
                      <div className="text-sm font-bold text-primary">{p.label}</div>
                      <div className="text-[10px] text-secondary">{p.sub}</div>
                    </button>
                  ))}
                </div>
              </div>
              {form.provider === 'meta_cloud' && (
                <div className="space-y-3 p-4 bg-[#0a1a12]/50 rounded-xl border border-[#25D366]/10">
                  <input value={form.meta_phone_number_id} onChange={e => setForm(f => ({ ...f, meta_phone_number_id: e.target.value }))} placeholder="phone_number_id" className="w-full px-3 py-2 bg-white/5 border border-white/10 rounded-lg text-xs text-primary font-mono" />
                  <input value={form.meta_waba_id} onChange={e => setForm(f => ({ ...f, meta_waba_id: e.target.value }))} placeholder="waba_id" className="w-full px-3 py-2 bg-white/5 border border-white/10 rounded-lg text-xs text-primary font-mono" />
                  <input value={form.meta_access_token} onChange={e => setForm(f => ({ ...f, meta_access_token: e.target.value }))} placeholder="access_token" type="password" className="w-full px-3 py-2 bg-white/5 border border-white/10 rounded-lg text-xs text-primary font-mono" />
                </div>
              )}
              {form.provider === 'evolution' && (
                <div className="space-y-3 p-4 bg-purple-900/10 rounded-xl border border-purple-500/10">
                  <input value={form.evolution_server_url} onChange={e => setForm(f => ({ ...f, evolution_server_url: e.target.value }))} placeholder="https://evo.example.com" className="w-full px-3 py-2 bg-white/5 border border-white/10 rounded-lg text-xs text-primary font-mono" />
                  <input value={form.evolution_instance} onChange={e => setForm(f => ({ ...f, evolution_instance: e.target.value }))} placeholder="instance_name" className="w-full px-3 py-2 bg-white/5 border border-white/10 rounded-lg text-xs text-primary font-mono" />
                  <input value={form.evolution_api_key} onChange={e => setForm(f => ({ ...f, evolution_api_key: e.target.value }))} placeholder="api_key" type="password" className="w-full px-3 py-2 bg-white/5 border border-white/10 rounded-lg text-xs text-primary font-mono" />
                </div>
              )}
            </div>
            <footer className="px-6 py-4 border-t border-border flex justify-end gap-3">
              <button onClick={() => setShowAdd(false)} className="px-4 py-2 text-sm text-secondary hover:text-primary">Cancelar</button>
              <button onClick={() => createMut.mutate(form)} disabled={!form.nickname || createMut.isPending}
                className="flex items-center gap-2 px-6 py-2.5 bg-gradient-to-r from-[#25D366] to-[#128C7E] text-white rounded-xl text-sm font-bold disabled:opacity-40">
                <Save className="w-4 h-4" /> {createMut.isPending ? 'Salvando...' : 'Criar Dispositivo'}
              </button>
            </footer>
          </div>
        </div>
      )}

      {/* Modal Meta Embedded Signup */}
      {showMetaModal && (
        <MetaEmbeddedModal
          config={metaConfig}
          onClose={() => setShowMetaModal(false)}
          onSuccess={() => {
            setShowMetaModal(false);
            qc.invalidateQueries({ queryKey: ['devices'] });
          }}
          onFallbackManual={() => {
            setShowMetaModal(false);
            setShowAdd(true);
            setForm(f => ({ ...f, provider: 'meta_cloud' }));
          }}
        />
      )}
    </div>
  );
}

/* ── Device Card ─────────────────────────────── */
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
  const qc = useQueryClient();
  const { data: liveStatus, refetch } = useQuery({
    queryKey: ['device-status', d.id],
    queryFn: () => api.get<any>(`/saas/devices/${d.id}/status`),
    refetchInterval: (query) => {
      if (typeof document !== 'undefined' && document.hidden) return false;
      const isConn = query.state.data?.connected ?? d.connected;
      return isConn ? 60000 : 15000;
    },
  });

  const isConnected = liveStatus?.connected ?? d.connected;
  const isMeta = d.provider === 'meta_cloud' || d.provider === 'coex';
  const currentMode = d.flow_mode || 'static_funnel';

  return (
    <div className={`relative overflow-hidden rounded-2xl border transition-all ${isConnected
      ? 'bg-gradient-to-br from-[#0a1a12] to-[#0f2318] border-[#25D366]/20 hover:border-[#25D366]/40'
      : 'bg-bg-surface border-border hover:border-amber-500/30'}`}>

      {/* Glow effect when connected */}
      {isConnected && <div className="absolute top-0 right-0 w-64 h-64 bg-[#25D366]/5 rounded-full blur-3xl -translate-y-1/2 translate-x-1/3 pointer-events-none" />}

      {/* Primary badge */}
      {d.is_primary && (
        <div className="absolute top-3 right-3 flex items-center gap-1 px-2.5 py-1 rounded-full bg-amber-500/15 border border-amber-500/25 z-10">
          <Star className="w-3 h-3 text-amber-400 fill-amber-400" />
          <span className="text-[9px] font-bold text-amber-400 uppercase tracking-wider">Principal</span>
        </div>
      )}

      {/* Top section */}
      <div className="relative px-6 pt-6 pb-5">
        <div className="flex items-start gap-4">
          {/* Logo */}
          <div className="relative flex-shrink-0">
            <div className={`w-16 h-16 rounded-2xl flex items-center justify-center shadow-lg ${isConnected ? 'bg-gradient-to-br from-[#25D366] to-[#128C7E] shadow-[#25D366]/20' : 'bg-zinc-800'}`}>
              <WaLogo className={`w-8 h-8 ${isConnected ? 'text-white' : 'text-zinc-500'}`} />
            </div>
            {isConnected && (
              <div className="absolute -bottom-1 -right-1 w-5 h-5 rounded-full bg-[#0a1a12] flex items-center justify-center">
                <div className="w-3.5 h-3.5 rounded-full bg-[#25D366] animate-pulse" />
              </div>
            )}
          </div>

          {/* Info */}
          <div className="flex-1 min-w-0">
            <h3 className={`text-lg font-bold tracking-tight truncate ${isConnected ? 'text-white' : 'text-primary'}`}>{d.nickname}</h3>
            <div className="flex items-center gap-2 mt-1">
              <Phone className={`w-3.5 h-3.5 ${isConnected ? 'text-white/40' : 'text-secondary'}`} />
              <span className={`text-sm font-mono ${isConnected ? 'text-white/60' : 'text-secondary'}`}>
                {d.phone_display || 'Sem número'}
              </span>
            </div>

            {/* Provider badge */}
            <div className="flex items-center gap-2 mt-2.5">
              {isMeta ? (
                <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-[#25D366]/10 border border-[#25D366]/20">
                  <ShieldCheck className="w-3 h-3 text-[#25D366]" />
                  <span className="text-[9px] font-bold text-[#25D366] uppercase tracking-wider">API Oficial</span>
                </div>
              ) : (
                <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-purple-500/10 border border-purple-500/20">
                  <QrCode className="w-3 h-3 text-purple-400" />
                  <span className="text-[9px] font-bold text-purple-400 uppercase tracking-wider">Evolution · QR</span>
                </div>
              )}
              {isConnected ? (
                <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-[#25D366]/10 border border-[#25D366]/20">
                  <CheckCircle2 className="w-3 h-3 text-[#25D366]" />
                  <span className="text-[9px] font-bold text-[#25D366] uppercase">Conectado</span>
                </div>
              ) : (
                <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-amber-500/10 border border-amber-500/20">
                  <AlertTriangle className="w-3 h-3 text-amber-400" />
                  <span className="text-[9px] font-bold text-amber-400 uppercase">Desconectado</span>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Stats when connected */}
        {isConnected && (
          <div className="flex items-center gap-2 mt-5 flex-wrap">
            <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-white/5 border border-white/8">
              <Signal className="w-3.5 h-3.5 text-[#25D366]" />
              <span className="text-[10px] font-bold text-white/60">Latência: <span className="text-[#25D366]">&lt;200ms</span></span>
            </div>
            {isMeta && (
              <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-white/5 border border-white/8">
                <Zap className="w-3.5 h-3.5 text-amber-400" />
                <span className="text-[10px] font-bold text-white/60">Rate: <span className="text-amber-400">80/s</span></span>
              </div>
            )}
            <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-white/5 border border-white/8">
              <span className="text-[10px] font-bold text-white/60">Grupos: <span className="text-[#0082FB]">{d.groups_count}</span></span>
            </div>
          </div>
        )}

        {/* Flow Mode Switcher: Static Funnel vs AI Agent */}
        <div className={`mt-5 pt-4 border-t ${isConnected ? 'border-white/10' : 'border-border'}`}>
          <div className="flex items-center justify-between mb-2.5">
            <div className="flex items-center gap-1.5">
              <Zap className={`w-3.5 h-3.5 ${isConnected ? 'text-emerald-400' : 'text-emerald-600'}`} />
              <span className={`text-[10px] font-black uppercase tracking-wider ${isConnected ? 'text-white/70' : 'text-secondary'}`}>
                Modo de Atendimento
              </span>
            </div>
            <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${
              isConnected ? 'bg-white/10 text-white border-white/15' : 'bg-bg-primary text-primary border-border'
            }`}>
              {currentMode === 'ai_agent' ? '🤖 Agente de IA' : '⚡ Funil Estático'}
            </span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
            <button
              type="button"
              onClick={() => onSetFlowMode('static_funnel')}
              className={`p-2.5 rounded-xl border text-left transition-all ${
                currentMode === 'static_funnel'
                  ? 'bg-emerald-500/20 border-emerald-500/60 ring-1 ring-emerald-500/30'
                  : isConnected
                    ? 'bg-white/5 border-white/10 hover:border-white/20 text-white/60 hover:text-white'
                    : 'bg-bg-primary border-border hover:border-emerald-500/30 text-secondary hover:text-primary'
              }`}
            >
              <div className="flex items-center justify-between">
                <span className={`font-bold text-xs flex items-center gap-1 ${isConnected ? 'text-white' : 'text-primary'}`}>
                  ⚡ Funil Estático
                </span>
                {currentMode === 'static_funnel' && (
                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                )}
              </div>
              <p className={`text-[10px] mt-0.5 leading-snug ${isConnected ? 'text-white/50' : 'text-secondary'}`}>
                7 etapas Meu Mistério (áudios, tarot e checkout).
              </p>
            </button>

            <button
              type="button"
              onClick={() => onSetFlowMode('ai_agent')}
              className={`p-2.5 rounded-xl border text-left transition-all ${
                currentMode === 'ai_agent'
                  ? 'bg-purple-500/20 border-purple-500/60 ring-1 ring-purple-500/30'
                  : isConnected
                    ? 'bg-white/5 border-white/10 hover:border-white/20 text-white/60 hover:text-white'
                    : 'bg-bg-primary border-border hover:border-purple-500/30 text-secondary hover:text-primary'
              }`}
            >
              <div className="flex items-center justify-between">
                <span className={`font-bold text-xs flex items-center gap-1 ${isConnected ? 'text-white' : 'text-primary'}`}>
                  🤖 Agente de IA
                </span>
                {currentMode === 'ai_agent' && (
                  <CheckCircle2 className="w-3.5 h-3.5 text-purple-400" />
                )}
              </div>
              <p className={`text-[10px] mt-0.5 leading-snug ${isConnected ? 'text-white/50' : 'text-secondary'}`}>
                IA autônoma Gemini: conversa livre e fechamento.
              </p>
            </button>
          </div>
        </div>
      </div>

      {/* Bottom actions */}
      <div className={`relative px-6 py-3.5 border-t flex items-center justify-between ${isConnected ? 'border-white/5 bg-black/20' : 'border-border bg-bg-primary/30'}`}>
        <div className="flex items-center gap-3">
          {!d.is_primary && (
            <button onClick={onSetPrimary} className={`text-[10px] font-bold hover:underline ${isConnected ? 'text-white/30 hover:text-white/60' : 'text-secondary hover:text-primary'}`}>
              Definir como principal
            </button>
          )}
          {isMeta && isConnected && (
            <a href="https://business.facebook.com" target="_blank" rel="noopener" className="flex items-center gap-1 text-[10px] text-[#0082FB] font-bold hover:underline">
              <ExternalLink className="w-3 h-3" /> Meta Dashboard
            </a>
          )}
        </div>
        <div className="flex items-center gap-2">
          <button onClick={() => refetch()} className={`p-1.5 rounded-lg transition-all ${isConnected ? 'hover:bg-white/5 text-white/30 hover:text-white/60' : 'hover:bg-bg-primary text-secondary'}`}>
            <RefreshCw className="w-3.5 h-3.5" />
          </button>
          <button onClick={() => { if (confirm(`Remover "${d.nickname}"?`)) onDelete(); }}
            className="p-1.5 rounded-lg text-red-400/40 hover:text-red-400 hover:bg-red-500/10 transition-all">
            <Trash2 className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>
    </div>
  );
}

/* ── Meta Embedded Signup Modal ─────────────────────────────── */
function MetaEmbeddedModal({
  config, onClose, onSuccess, onFallbackManual,
}: {
  config: { configured?: boolean; app_id?: string; config_id?: string; graph_version?: string } | undefined;
  onClose: () => void;
  onSuccess: () => void;
  onFallbackManual: () => void;
}) {
  const [nickname, setNickname] = useState('WhatsApp Oficial');
  const [code, setCode] = useState('');
  const [phoneNumberId, setPhoneNumberId] = useState('');
  const [wabaId, setWabaId] = useState('');
  const [showManualCode, setShowManualCode] = useState(false);

  const exchangeMut = useMutation({
    mutationFn: (payload: { code: string; phone_number_id?: string; waba_id?: string; nickname?: string }) =>
      api.post<{ ok: boolean; device: any }>('/saas/wa/embedded-signup/exchange', payload),
    onSuccess: () => {
      toast.success('WhatsApp conectado com sucesso via Meta Embedded Signup!');
      onSuccess();
    },
    onError: (err: any) => toast.error(err?.message || 'Falha ao autorizar com a Meta.'),
  });

  const isConfigured = Boolean(config?.configured && config?.app_id);

  const launchMetaOAuth = () => {
    if (!config?.app_id) return;
    const redirectUri = `${window.location.origin}/builder/wa-connection`;
    const version = config.graph_version || 'v20.0';
    const oauthUrl = `https://www.facebook.com/${version}/dialog/oauth?client_id=${config.app_id}&redirect_uri=${encodeURIComponent(redirectUri)}&response_type=code&scope=whatsapp_business_management,whatsapp_business_messaging`;

    const width = 600;
    const height = 700;
    const left = window.screenX + (window.outerWidth - width) / 2;
    const top = window.screenY + (window.outerHeight - height) / 2;
    const popup = window.open(
      oauthUrl,
      'MetaEmbeddedSignup',
      `width=${width},height=${height},left=${left},top=${top},status=no,toolbar=no,menubar=no`,
    );

    // Listener para o retorno do popup
    const handleMessage = (event: MessageEvent) => {
      if (!event.origin.includes(window.location.hostname) && !event.origin.includes('facebook.com')) {
        return;
      }
      try {
        const raw = typeof event.data === 'string' ? JSON.parse(event.data) : event.data;
        if (raw?.type === 'WA_EMBEDDED_SIGNUP' || raw?.code) {
          window.removeEventListener('message', handleMessage);
          if (popup && !popup.closed) popup.close();
          const authCode = raw.code || raw?.data?.code;
          const pId = raw.phone_number_id || raw?.data?.phone_number_id;
          const wId = raw.waba_id || raw?.data?.waba_id;
          if (authCode) {
            exchangeMut.mutate({
              code: authCode,
              phone_number_id: pId,
              waba_id: wId,
              nickname,
            });
          }
        }
      } catch {}
    };

    window.addEventListener('message', handleMessage);
  };

  return (
    <div className="fixed inset-0 z-[100] bg-black/70 backdrop-blur-sm flex items-center justify-center p-4" onClick={onClose}>
      <div onClick={(e) => e.stopPropagation()} className="bg-bg-surface border border-border rounded-3xl shadow-2xl max-w-lg w-full overflow-hidden">
        <header className="flex items-center justify-between px-6 py-4 border-b border-border bg-gradient-to-r from-blue-600/10 via-transparent to-transparent">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-xl bg-blue-600/20 flex items-center justify-center text-[#0082FB]">
              <MetaLogo className="w-5 h-5" />
            </div>
            <div>
              <h3 className="font-display text-lg text-primary">Conectar via Meta</h3>
              <p className="text-[10px] text-secondary">WhatsApp Cloud API Oficial (Embedded Signup)</p>
            </div>
          </div>
          <button onClick={onClose} className="p-1.5 rounded-lg hover:bg-bg-primary text-secondary">
            <X className="w-4 h-4" />
          </button>
        </header>

        <div className="p-6 space-y-5">
          {isConfigured ? (
            <div className="space-y-4">
              <div className="p-4 rounded-2xl bg-blue-500/5 border border-blue-500/20 text-xs text-secondary leading-relaxed">
                <span className="font-bold text-primary block mb-1">Conexão em 1 Clique</span>
                Você será redirecionado para autorizar o número da sua empresa diretamente com o Facebook / WhatsApp Business Manager, sem precisar copiar tokens manualmente.
              </div>

              <div>
                <label className="text-xs font-bold text-secondary block mb-1">Apelido do dispositivo</label>
                <input
                  value={nickname}
                  onChange={(e) => setNickname(e.target.value)}
                  placeholder="Ex: WhatsApp Comercial"
                  className="w-full px-4 py-2.5 bg-bg-primary border border-border rounded-xl text-sm text-primary"
                />
              </div>

              <button
                type="button"
                onClick={launchMetaOAuth}
                disabled={exchangeMut.isPending}
                className="w-full flex items-center justify-center gap-3 py-3.5 bg-[#0082FB] hover:bg-[#0070db] text-white rounded-xl font-bold text-sm shadow-lg shadow-[#0082FB]/20 transition-all"
              >
                <MetaLogo className="w-5 h-5" />
                {exchangeMut.isPending ? 'Autenticando...' : 'Entrar com Facebook'}
              </button>

              <div className="pt-2 text-center">
                <button
                  type="button"
                  onClick={() => setShowManualCode(!showManualCode)}
                  className="text-[11px] text-secondary hover:text-primary underline"
                >
                  {showManualCode ? 'Ocultar inserção manual de código' : 'Possui um código de autorização manual?'}
                </button>
              </div>

              {showManualCode && (
                <div className="space-y-3 p-4 bg-bg-primary rounded-xl border border-border">
                  <input
                    value={code}
                    onChange={(e) => setCode(e.target.value)}
                    placeholder="Cole o authorization code aqui"
                    className="w-full px-3 py-2 bg-bg-surface border border-border rounded-lg text-xs font-mono"
                  />
                  <div className="grid grid-cols-2 gap-2">
                    <input
                      value={phoneNumberId}
                      onChange={(e) => setPhoneNumberId(e.target.value)}
                      placeholder="phone_number_id (opcional)"
                      className="px-3 py-2 bg-bg-surface border border-border rounded-lg text-xs font-mono"
                    />
                    <input
                      value={wabaId}
                      onChange={(e) => setWabaId(e.target.value)}
                      placeholder="waba_id (opcional)"
                      className="px-3 py-2 bg-bg-surface border border-border rounded-lg text-xs font-mono"
                    />
                  </div>
                  <button
                    type="button"
                    onClick={() => exchangeMut.mutate({ code, phone_number_id: phoneNumberId, waba_id: wabaId, nickname })}
                    disabled={!code.trim() || exchangeMut.isPending}
                    className="w-full py-2 bg-blue-600/20 text-blue-400 hover:bg-blue-600/30 rounded-lg text-xs font-bold transition-all disabled:opacity-40"
                  >
                    {exchangeMut.isPending ? 'Verificando...' : 'Trocar código por token'}
                  </button>
                </div>
              )}
            </div>
          ) : (
            <div className="space-y-4">
              <div className="p-4 rounded-2xl bg-amber-500/10 border border-amber-500/20 text-xs text-secondary leading-relaxed">
                <span className="font-bold text-amber-400 block mb-1">Configuração do Servidor Pendente</span>
                Para habilitar o login em 1 clique via Meta, configure as variáveis de ambiente no servidor:
                <div className="mt-2 p-2 bg-black/40 rounded-lg font-mono text-[11px] text-amber-200 space-y-0.5">
                  <div>META_APP_ID=seu_app_id</div>
                  <div>META_APP_SECRET=seu_app_secret</div>
                </div>
                <p className="mt-2 text-[11px]">
                  Enquanto isso, você pode adicionar seu número manualmente inserindo o token da API Cloud do Meta diretamente.
                </p>
              </div>

              <div className="flex flex-col gap-2 pt-2">
                <button
                  type="button"
                  onClick={onFallbackManual}
                  className="w-full py-3 bg-gradient-to-r from-[#25D366] to-[#128C7E] text-white rounded-xl font-bold text-sm shadow-md"
                >
                  Inserir Credenciais Manualmente
                </button>
                <a
                  href="https://developers.facebook.com/apps"
                  target="_blank"
                  rel="noopener"
                  className="text-center py-2 text-xs text-secondary hover:text-primary flex items-center justify-center gap-1"
                >
                  <ExternalLink className="w-3 h-3" /> Abrir Meta Developers Portal
                </a>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

