import { useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  QrCode, RefreshCw, AlertTriangle, CheckCircle2, ShieldCheck, Signal, Phone,
  ExternalLink, Zap, Plus, Star, Trash2, X, Save, KeyRound, Globe, Smartphone,
  MessageSquare, Send, BookOpen, Copy, Sparkles, Eye, EyeOff,
} from 'lucide-react';
import { api } from '../api/client';
import { toast } from '../lib/toast';
import WhatsAppConnect from '../components/WhatsAppConnect';

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

interface Device {
  id: number;
  nickname: string;
  provider: string;
  phone_display: string | null;
  connected: boolean;
  connection_state: string | null;
  is_primary: boolean;
  groups_count: number;
  created_at: string | null;
  flow_mode?: 'static_funnel' | 'ai_agent' | 'flow_builder';
}

type TabKey = 'devices' | 'meta_keys' | 'channels';

export default function WAConnection() {
  const qc = useQueryClient();
  const [searchParams, setSearchParams] = useSearchParams();
  const activeTab: TabKey = (searchParams.get('tab') as TabKey) || 'devices';

  const [showAdd, setShowAdd] = useState(false);
  const [showMetaModal, setShowMetaModal] = useState(false);
  const [form, setForm] = useState({
    nickname: '',
    provider: 'meta_cloud',
    phone_display: '',
    meta_phone_number_id: '',
    meta_waba_id: '',
    meta_access_token: '',
    evolution_server_url: '',
    evolution_instance: '',
    evolution_api_key: '',
  });
  const [showToken, setShowToken] = useState(false);

  const { data } = useQuery({ queryKey: ['devices'], queryFn: () => api.get<any>('/saas/devices/') });
  const devices: Device[] = data?.devices || [];

  const { data: metaConfig } = useQuery({
    queryKey: ['meta-embedded-config'],
    queryFn: () => api.get<any>('/saas/wa/embedded-signup/config'),
  });

  const createMut = useMutation({
    mutationFn: (d: any) => api.post('/saas/devices/', d),
    onSuccess: () => {
      toast.success('Dispositivo criado!');
      qc.invalidateQueries({ queryKey: ['devices'] });
      setShowAdd(false);
      setForm({
        nickname: '',
        provider: 'meta_cloud',
        phone_display: '',
        meta_phone_number_id: '',
        meta_waba_id: '',
        meta_access_token: '',
        evolution_server_url: '',
        evolution_instance: '',
        evolution_api_key: '',
      });
    },
    onError: (e: any) => toast.error(e?.message || 'Erro ao criar dispositivo'),
  });

  const deleteMut = useMutation({
    mutationFn: (id: number) => api.del(`/saas/devices/${id}`),
    onSuccess: () => {
      toast.success('Dispositivo removido');
      qc.invalidateQueries({ queryKey: ['devices'] });
    },
  });

  const primaryMut = useMutation({
    mutationFn: (id: number) => api.post(`/saas/devices/${id}/set-primary`, {}),
    onSuccess: () => {
      toast.success('Dispositivo principal definido!');
      qc.invalidateQueries({ queryKey: ['devices'] });
    },
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

  const setTab = (tab: TabKey) => {
    setSearchParams({ tab });
  };

  return (
    <div className="px-6 sm:px-8 py-8 max-w-6xl mx-auto min-h-screen text-primary space-y-8">
      {/* ═══ CABEÇALHO UNIFICADO ═══ */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 border-b border-border pb-6">
        <div className="flex items-center gap-4">
          <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-[#25D366] to-[#128C7E] flex items-center justify-center shadow-lg shadow-[#25D366]/20 shrink-0">
            <WaLogo className="w-7 h-7 text-white" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-2xl sm:text-3xl font-bold tracking-tight">
                Conexão & API Meta
              </h1>
              <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-[#25D366]/10 text-[#25D366] border border-[#25D366]/25 uppercase tracking-wider">
                Oficial
              </span>
            </div>
            <p className="text-xs text-secondary mt-1 max-w-xl">
              Central oficial de comunicação: configure números de WhatsApp, credenciais Meta Cloud API, webhooks e canais externos em um único lugar.
            </p>
          </div>
        </div>

        {activeTab === 'devices' && (
          <div className="flex items-center gap-2.5 w-full sm:w-auto">
            <button
              onClick={() => setShowMetaModal(true)}
              className="flex-1 sm:flex-none flex items-center justify-center gap-2 px-4 py-2.5 bg-[#0082FB]/10 hover:bg-[#0082FB]/20 text-[#0082FB] border border-[#0082FB]/30 rounded-xl text-xs font-bold transition-all shadow-sm"
            >
              <MetaLogo className="w-4 h-4" /> Conectar via Meta
            </button>
            <button
              onClick={() => setShowAdd(true)}
              className="flex-1 sm:flex-none flex items-center justify-center gap-2 px-4 py-2.5 bg-gradient-to-r from-[#25D366] to-[#128C7E] text-white rounded-xl text-xs font-bold hover:shadow-lg hover:shadow-[#25D366]/20 transition-all"
            >
              <Plus className="w-4 h-4" /> Novo Dispositivo
            </button>
          </div>
        )}
      </div>

      {/* ═══ NAVEGAÇÃO ENTRE ABAS ═══ */}
      <div className="flex items-center gap-2 p-1.5 bg-bg-surface border border-border rounded-2xl w-fit">
        <button
          onClick={() => setTab('devices')}
          className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-bold transition-all ${
            activeTab === 'devices'
              ? 'bg-[#25D366] text-white shadow-md shadow-[#25D366]/20'
              : 'text-secondary hover:text-primary hover:bg-bg-primary'
          }`}
        >
          <Smartphone className="w-4 h-4" />
          <span>Meus Números</span>
          <span className={`px-1.5 py-0.2 rounded-full text-[10px] font-mono ${
            activeTab === 'devices' ? 'bg-white/20 text-white' : 'bg-bg-primary text-secondary'
          }`}>
            {devices.length}
          </span>
        </button>

        <button
          onClick={() => setTab('meta_keys')}
          className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-bold transition-all ${
            activeTab === 'meta_keys'
              ? 'bg-blue-600 text-white shadow-md shadow-blue-600/20'
              : 'text-secondary hover:text-primary hover:bg-bg-primary'
          }`}
        >
          <KeyRound className="w-4 h-4" />
          <span>Credenciais Meta Cloud</span>
        </button>

        <button
          onClick={() => setTab('channels')}
          className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-bold transition-all ${
            activeTab === 'channels'
              ? 'bg-purple-600 text-white shadow-md shadow-purple-600/20'
              : 'text-secondary hover:text-primary hover:bg-bg-primary'
          }`}
        >
          <Globe className="w-4 h-4" />
          <span>Webhooks & Canais Externos</span>
        </button>
      </div>

      {/* ═══ CONTEÚDO DA ABA 1: DISPOSITIVOS & NÚMEROS ═══ */}
      {activeTab === 'devices' && (
        <div className="space-y-6">
          {devices.length === 0 ? (
            <div className="text-center py-16 bg-bg-surface border border-dashed border-border rounded-3xl p-8">
              <Phone className="w-12 h-12 text-secondary mx-auto mb-3 opacity-30" />
              <h3 className="text-lg font-bold text-primary mb-1">Nenhum número conectado</h3>
              <p className="text-xs text-secondary mb-6 max-w-sm mx-auto">
                Adicione seu primeiro número do WhatsApp via Meta Cloud API ou Evolution QR Code para começar a atender leads.
              </p>
              <div className="flex items-center justify-center gap-3">
                <button
                  onClick={() => setShowMetaModal(true)}
                  className="px-5 py-2.5 bg-[#0082FB] hover:bg-[#0070db] text-white rounded-xl text-xs font-bold shadow-md flex items-center gap-2"
                >
                  <MetaLogo className="w-4 h-4" /> Conectar via Meta
                </button>
                <button
                  onClick={() => setShowAdd(true)}
                  className="px-5 py-2.5 bg-bg-primary border border-border hover:bg-bg-surface text-primary rounded-xl text-xs font-bold flex items-center gap-2"
                >
                  <Plus className="w-4 h-4" /> Cadastro Manual
                </button>
              </div>
            </div>
          ) : (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
              {devices.map((d) => (
                <DeviceCard
                  key={d.id}
                  device={d}
                  onDelete={() => deleteMut.mutate(d.id)}
                  onSetPrimary={() => primaryMut.mutate(d.id)}
                  onSetFlowMode={(mode) => flowModeMut.mutate({ id: d.id, mode })}
                />
              ))}
            </div>
          )}
        </div>
      )}

      {/* ═══ CONTEÚDO DA ABA 2: CREDENCIAIS META CLOUD API ═══ */}
      {activeTab === 'meta_keys' && (
        <div className="bg-bg-surface border border-border rounded-3xl p-6 sm:p-8 shadow-sm">
          <WhatsAppConnect />
        </div>
      )}

      {/* ═══ CONTEÚDO DA ABA 3: WEBHOOKS & CANAIS EXTERNOS ═══ */}
      {activeTab === 'channels' && (
        <ChannelsTab />
      )}

      {/* Modal Novo Dispositivo */}
      {showAdd && (
        <div className="fixed inset-0 z-[100] bg-black/80 backdrop-blur-md flex items-center justify-center p-4 sm:p-6" onClick={() => setShowAdd(false)}>
          <div onClick={(e) => e.stopPropagation()} className="bg-zinc-950 border border-zinc-800 rounded-3xl shadow-2xl max-w-xl w-full overflow-hidden flex flex-col max-h-[90vh]">
            <header className="flex items-center justify-between px-6 py-5 border-b border-zinc-800 bg-zinc-900/40">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-2xl bg-gradient-to-br from-[#25D366]/20 to-[#128C7E]/20 border border-[#25D366]/30 flex items-center justify-center text-[#25D366]">
                  <WaLogo className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="font-bold text-base text-zinc-100">Novo Número WhatsApp</h3>
                  <p className="text-xs text-zinc-400">Conecte via Meta Cloud Oficial ou WhatsApp Web / QR Code</p>
                </div>
              </div>
              <button onClick={() => setShowAdd(false)} className="p-2 rounded-xl hover:bg-zinc-800 text-zinc-400 hover:text-zinc-200 transition-colors">
                <X className="w-4 h-4" />
              </button>
            </header>

            <div className="p-6 space-y-5 overflow-y-auto flex-1">
              {/* Opção Rápida: Embedded Signup oficial */}
              <div className="p-4 rounded-2xl bg-gradient-to-r from-blue-600/10 via-indigo-600/10 to-transparent border border-blue-500/20 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                <div>
                  <div className="flex items-center gap-1.5 text-xs font-bold text-blue-400 mb-0.5">
                    <Sparkles className="w-3.5 h-3.5" />
                    <span>Conexão Oficial em 1 Clique (Recomendado)</span>
                  </div>
                  <p className="text-[11px] text-zinc-400 leading-relaxed">
                    Autorize diretamente com sua conta do Facebook / Meta sem precisar preencher IDs e tokens manualmente.
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => {
                    setShowAdd(false);
                    setShowMetaModal(true);
                  }}
                  className="px-3.5 py-2 rounded-xl text-xs font-bold bg-[#0082FB] hover:bg-[#0070db] text-white transition-all shadow-md shadow-[#0082FB]/20 flex items-center justify-center gap-1.5 shrink-0"
                >
                  <MetaLogo className="w-3.5 h-3.5" />
                  <span>Entrar com Meta</span>
                </button>
              </div>

              <div className="flex items-center gap-3">
                <div className="h-px bg-zinc-800 flex-1" />
                <span className="text-[10px] font-bold uppercase tracking-wider text-zinc-500">ou cadastro manual</span>
                <div className="h-px bg-zinc-800 flex-1" />
              </div>

              {/* Informações Básicas */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="text-xs font-semibold text-zinc-300 block mb-1.5">
                    Apelido do Dispositivo <span className="text-rose-400">*</span>
                  </label>
                  <input
                    value={form.nickname}
                    onChange={(e) => setForm((f) => ({ ...f, nickname: e.target.value }))}
                    placeholder="Ex: Comercial, Vendas, Suporte..."
                    className="w-full px-3.5 py-2.5 bg-zinc-900 border border-zinc-700/70 rounded-xl text-sm text-zinc-100 placeholder:text-zinc-500 focus:outline-none focus:border-[#25D366] focus:ring-1 focus:ring-[#25D366]/30 transition-all"
                  />
                </div>
                <div>
                  <label className="text-xs font-semibold text-zinc-300 block mb-1.5">
                    Número do WhatsApp (com DDI e DDD)
                  </label>
                  <input
                    value={form.phone_display}
                    onChange={(e) => setForm((f) => ({ ...f, phone_display: e.target.value }))}
                    placeholder="+55 69 98105-1492"
                    className="w-full px-3.5 py-2.5 bg-zinc-900 border border-zinc-700/70 rounded-xl text-sm text-zinc-100 placeholder:text-zinc-500 focus:outline-none focus:border-[#25D366] focus:ring-1 focus:ring-[#25D366]/30 transition-all font-mono"
                  />
                </div>
              </div>

              {/* Seletor de Provedor */}
              <div>
                <label className="text-xs font-semibold text-zinc-300 block mb-2">Provedor de Conexão</label>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  {[
                    {
                      id: 'meta_cloud',
                      label: 'Meta Cloud API Oficial',
                      badge: 'Oficial Meta',
                      desc: 'Envio ativo, alta entrega, botões interativos e sem risco de ban.',
                      color: 'border-emerald-500/60 bg-emerald-950/20 text-emerald-400 ring-1 ring-emerald-500/30',
                    },
                    {
                      id: 'evolution',
                      label: 'Evolution API (QR Code)',
                      badge: 'Conexão Web',
                      desc: 'Conecte lendo o QR Code do WhatsApp tradicional no celular.',
                      color: 'border-purple-500/60 bg-purple-950/20 text-purple-400 ring-1 ring-purple-500/30',
                    },
                  ].map((p) => {
                    const isSelected = form.provider === p.id;
                    return (
                      <button
                        key={p.id}
                        type="button"
                        onClick={() => setForm((f) => ({ ...f, provider: p.id }))}
                        className={`text-left p-3.5 rounded-2xl border transition-all ${
                          isSelected
                            ? p.color
                            : 'bg-zinc-900/60 border-zinc-800 hover:border-zinc-700 text-zinc-300'
                        }`}
                      >
                        <div className="flex items-center justify-between mb-1">
                          <span className="font-bold text-xs text-zinc-100">{p.label}</span>
                          <span className="text-[10px] px-2 py-0.5 rounded-full font-bold bg-zinc-800 text-zinc-300 border border-zinc-700/60">
                            {p.badge}
                          </span>
                        </div>
                        <p className="text-[11px] text-zinc-400 leading-snug">{p.desc}</p>
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* Campos Meta Cloud API */}
              {form.provider === 'meta_cloud' && (
                <div className="space-y-3.5 p-4 bg-zinc-900/80 rounded-2xl border border-zinc-800">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold uppercase tracking-wider text-emerald-400">
                      Credenciais Meta Cloud (Graph API)
                    </span>
                    <a
                      href="https://developers.facebook.com/apps"
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-[11px] text-zinc-400 hover:text-white flex items-center gap-1 underline"
                    >
                      <ExternalLink className="w-3 h-3" /> Abrir Meta Developers
                    </a>
                  </div>

                  <div>
                    <label className="text-xs font-medium text-zinc-300 block mb-1">
                      ID do Número de Telefone (<code className="font-mono text-emerald-400">phone_number_id</code>)
                    </label>
                    <input
                      value={form.meta_phone_number_id}
                      onChange={(e) => setForm((f) => ({ ...f, meta_phone_number_id: e.target.value }))}
                      placeholder="Ex: 1126244453895124"
                      className="w-full px-3.5 py-2 bg-zinc-950 border border-zinc-700/80 rounded-xl text-xs text-zinc-100 placeholder:text-zinc-600 focus:outline-none focus:border-[#25D366] font-mono"
                    />
                  </div>

                  <div>
                    <label className="text-xs font-medium text-zinc-300 block mb-1">
                      ID da Conta de WhatsApp Business (<code className="font-mono text-emerald-400">waba_id</code>)
                    </label>
                    <input
                      value={form.meta_waba_id}
                      onChange={(e) => setForm((f) => ({ ...f, meta_waba_id: e.target.value }))}
                      placeholder="Ex: 1443823057400060"
                      className="w-full px-3.5 py-2 bg-zinc-950 border border-zinc-700/80 rounded-xl text-xs text-zinc-100 placeholder:text-zinc-600 focus:outline-none focus:border-[#25D366] font-mono"
                    />
                  </div>

                  <div>
                    <div className="flex items-center justify-between mb-1">
                      <label className="text-xs font-medium text-zinc-300">
                        Token de Acesso Permanente (System User)
                      </label>
                      <button
                        type="button"
                        onClick={() => setShowToken(!showToken)}
                        className="text-[11px] text-zinc-400 hover:text-zinc-200 flex items-center gap-1"
                      >
                        {showToken ? <EyeOff className="w-3 h-3" /> : <Eye className="w-3 h-3" />}
                        <span>{showToken ? 'Ocultar' : 'Mostrar'}</span>
                      </button>
                    </div>
                    <input
                      value={form.meta_access_token}
                      onChange={(e) => setForm((f) => ({ ...f, meta_access_token: e.target.value }))}
                      placeholder="EAAB... (Token permanente do Gerenciador de Negócios)"
                      type={showToken ? 'text' : 'password'}
                      className="w-full px-3.5 py-2 bg-zinc-950 border border-zinc-700/80 rounded-xl text-xs text-zinc-100 placeholder:text-zinc-600 focus:outline-none focus:border-[#25D366] font-mono"
                    />
                  </div>
                </div>
              )}

              {/* Campos Evolution API */}
              {form.provider === 'evolution' && (
                <div className="space-y-3.5 p-4 bg-purple-950/20 rounded-2xl border border-purple-500/20">
                  <span className="text-xs font-bold uppercase tracking-wider text-purple-400 block">
                    Servidor Evolution API (QR Code)
                  </span>

                  <div>
                    <label className="text-xs font-medium text-zinc-300 block mb-1">URL do Servidor Evolution</label>
                    <input
                      value={form.evolution_server_url}
                      onChange={(e) => setForm((f) => ({ ...f, evolution_server_url: e.target.value }))}
                      placeholder="https://evo.seu-dominio.com"
                      className="w-full px-3.5 py-2 bg-zinc-950 border border-zinc-700/80 rounded-xl text-xs text-zinc-100 placeholder:text-zinc-600 focus:outline-none focus:border-purple-500 font-mono"
                    />
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    <div>
                      <label className="text-xs font-medium text-zinc-300 block mb-1">Nome da Instância</label>
                      <input
                        value={form.evolution_instance}
                        onChange={(e) => setForm((f) => ({ ...f, evolution_instance: e.target.value }))}
                        placeholder="minha-instancia"
                        className="w-full px-3.5 py-2 bg-zinc-950 border border-zinc-700/80 rounded-xl text-xs text-zinc-100 placeholder:text-zinc-600 focus:outline-none focus:border-purple-500 font-mono"
                      />
                    </div>
                    <div>
                      <label className="text-xs font-medium text-zinc-300 block mb-1">Chave Global / API Key</label>
                      <input
                        value={form.evolution_api_key}
                        onChange={(e) => setForm((f) => ({ ...f, evolution_api_key: e.target.value }))}
                        placeholder="API Key do servidor"
                        type="password"
                        className="w-full px-3.5 py-2 bg-zinc-950 border border-zinc-700/80 rounded-xl text-xs text-zinc-100 placeholder:text-zinc-600 focus:outline-none focus:border-purple-500 font-mono"
                      />
                    </div>
                  </div>
                </div>
              )}
            </div>

            <footer className="px-6 py-4 border-t border-zinc-800 bg-zinc-900/40 flex items-center justify-between">
              <button
                type="button"
                onClick={() => setShowAdd(false)}
                className="px-4 py-2 text-xs font-semibold text-zinc-400 hover:text-zinc-200 transition-colors"
              >
                Cancelar
              </button>
              <button
                type="button"
                onClick={() => createMut.mutate(form)}
                disabled={!form.nickname.trim() || createMut.isPending}
                className="inline-flex items-center gap-2 px-5 py-2.5 bg-gradient-to-r from-[#25D366] to-[#128C7E] hover:from-[#22bf5b] hover:to-[#0f7a6e] text-white rounded-xl text-xs font-bold disabled:opacity-40 shadow-md shadow-[#25D366]/20 transition-all active:scale-[0.98]"
              >
                <Save className="w-4 h-4" />
                <span>{createMut.isPending ? 'Conectando...' : 'Salvar e Conectar'}</span>
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
            setForm((f) => ({ ...f, provider: 'meta_cloud' }));
          }}
        />
      )}
    </div>
  );
}

/* ── Card de Dispositivo ─────────────────────────────── */
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
    <div
      className={`relative overflow-hidden rounded-3xl border transition-all ${
        isConnected
          ? 'bg-gradient-to-br from-[#0a1a12] via-bg-surface to-[#0f2318] border-[#25D366]/30 shadow-xl shadow-[#25D366]/5'
          : 'bg-bg-surface border-border hover:border-amber-500/30'
      }`}
    >
      {/* Glow effect */}
      {isConnected && (
        <div className="absolute top-0 right-0 w-64 h-64 bg-[#25D366]/10 rounded-full blur-3xl -translate-y-1/2 translate-x-1/3 pointer-events-none" />
      )}

      {/* Primary badge */}
      {d.is_primary && (
        <div className="absolute top-4 right-4 flex items-center gap-1 px-2.5 py-1 rounded-full bg-amber-500/15 border border-amber-500/30 z-10">
          <Star className="w-3 h-3 text-amber-400 fill-amber-400" />
          <span className="text-[9px] font-black text-amber-400 uppercase tracking-wider">Principal</span>
        </div>
      )}

      {/* Top section */}
      <div className="relative p-6">
        <div className="flex items-start gap-4">
          <div className="relative shrink-0">
            <div
              className={`w-14 h-14 rounded-2xl flex items-center justify-center shadow-lg ${
                isConnected
                  ? 'bg-gradient-to-br from-[#25D366] to-[#128C7E] text-white shadow-[#25D366]/20'
                  : 'bg-bg-primary text-secondary border border-border'
              }`}
            >
              <WaLogo className="w-7 h-7" />
            </div>
            {isConnected && (
              <div className="absolute -bottom-1 -right-1 w-4 h-4 rounded-full bg-black flex items-center justify-center">
                <div className="w-2.5 h-2.5 rounded-full bg-[#25D366] animate-pulse" />
              </div>
            )}
          </div>

          <div className="flex-1 min-w-0">
            <h3 className="text-base sm:text-lg font-bold truncate text-primary">
              {d.nickname}
            </h3>
            <div className="flex items-center gap-2 mt-1">
              <Phone className="w-3.5 h-3.5 text-secondary" />
              <span className="text-xs sm:text-sm font-mono font-bold text-primary">
                {d.phone_display || 'Sem número'}
              </span>
            </div>

            <div className="flex items-center gap-2 mt-3 flex-wrap">
              {isMeta ? (
                <div className="flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-[#25D366]/10 border border-[#25D366]/25">
                  <ShieldCheck className="w-3 h-3 text-[#25D366]" />
                  <span className="text-[9px] font-bold text-[#25D366] uppercase tracking-wider">API Oficial Meta</span>
                </div>
              ) : (
                <div className="flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-purple-500/10 border border-purple-500/25">
                  <QrCode className="w-3 h-3 text-purple-400" />
                  <span className="text-[9px] font-bold text-purple-400 uppercase tracking-wider">Evolution QR</span>
                </div>
              )}

              {isConnected ? (
                <div className="flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-[#25D366]/10 border border-[#25D366]/25">
                  <CheckCircle2 className="w-3 h-3 text-[#25D366]" />
                  <span className="text-[9px] font-bold text-[#25D366] uppercase">Conectado</span>
                </div>
              ) : (
                <div className="flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-amber-500/10 border border-amber-500/25">
                  <AlertTriangle className="w-3 h-3 text-amber-400" />
                  <span className="text-[9px] font-bold text-amber-400 uppercase">Desconectado</span>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Stats */}
        {isConnected && (
          <div className="flex items-center gap-2 mt-4 flex-wrap">
            <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-bg-primary/80 border border-border text-[10px]">
              <Signal className="w-3 h-3 text-[#25D366]" />
              <span className="text-secondary">Latência: <strong className="text-emerald-400">&lt;200ms</strong></span>
            </div>
            {isMeta && (
              <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-bg-primary/80 border border-border text-[10px]">
                <Zap className="w-3 h-3 text-amber-400" />
                <span className="text-secondary">Vazão: <strong className="text-amber-400">80 msgs/s</strong></span>
              </div>
            )}
            <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-bg-primary/80 border border-border text-[10px]">
              <span className="text-secondary">Grupos: <strong className="text-[#0082FB]">{d.groups_count}</strong></span>
            </div>
          </div>
        )}

        {/* Modo de Atendimento */}
        <div className="mt-5 pt-4 border-t border-border">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-1.5">
              <Zap className="w-3.5 h-3.5 text-[#25D366]" />
              <span className="text-[10px] font-black uppercase tracking-wider text-secondary">
                Modo de Atendimento
              </span>
            </div>
            <span className="text-[10px] font-bold px-2 py-0.5 rounded-full border bg-bg-primary border-border">
              {currentMode === 'ai_agent' ? '🤖 Agente de IA' : '⚡ Funil Estático'}
            </span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
            <button
              type="button"
              onClick={() => onSetFlowMode('static_funnel')}
              className={`p-3 rounded-2xl border text-left transition-all ${
                currentMode === 'static_funnel'
                  ? 'bg-emerald-500/15 border-emerald-500/60 ring-1 ring-emerald-500/30'
                  : 'bg-bg-primary/60 border-border hover:border-emerald-500/30'
              }`}
            >
              <div className="flex items-center justify-between">
                <span className="font-bold text-xs flex items-center gap-1.5 text-primary">
                  ⚡ Funil Estático
                </span>
                {currentMode === 'static_funnel' && (
                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                )}
              </div>
              <p className="text-[10px] mt-1 text-secondary leading-snug">
                7 etapas Meu Mistério (áudios, tarot e checkout de R$ 9,90).
              </p>
            </button>

            <button
              type="button"
              onClick={() => onSetFlowMode('ai_agent')}
              className={`p-3 rounded-2xl border text-left transition-all ${
                currentMode === 'ai_agent'
                  ? 'bg-purple-500/15 border-purple-500/60 ring-1 ring-purple-500/30'
                  : 'bg-bg-primary/60 border-border hover:border-purple-500/30'
              }`}
            >
              <div className="flex items-center justify-between">
                <span className="font-bold text-xs flex items-center gap-1.5 text-primary">
                  🤖 Agente de IA
                </span>
                {currentMode === 'ai_agent' && (
                  <CheckCircle2 className="w-3.5 h-3.5 text-purple-400" />
                )}
              </div>
              <p className="text-[10px] mt-1 text-secondary leading-snug">
                IA conversacional Gemini: diálogo livre e fechamento autônomo.
              </p>
            </button>
          </div>
        </div>
      </div>

      {/* Footer */}
      <div className="px-6 py-3 border-t border-border bg-bg-primary/40 flex items-center justify-between">
        <div className="flex items-center gap-3">
          {!d.is_primary && (
            <button
              onClick={onSetPrimary}
              className="text-[11px] font-bold text-secondary hover:text-primary transition-colors"
            >
              Tornar número principal
            </button>
          )}
          {isMeta && isConnected && (
            <a
              href="https://business.facebook.com"
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-1 text-[11px] text-[#0082FB] font-bold hover:underline"
            >
              <ExternalLink className="w-3 h-3" /> Meta Manager
            </a>
          )}
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => refetch()}
            className="p-1.5 rounded-lg hover:bg-bg-surface text-secondary hover:text-primary transition-all"
            title="Atualizar status"
          >
            <RefreshCw className="w-3.5 h-3.5" />
          </button>
          <button
            onClick={() => {
              if (confirm(`Remover "${d.nickname}"?`)) onDelete();
            }}
            className="p-1.5 rounded-lg text-red-400/50 hover:text-red-400 hover:bg-red-500/10 transition-all"
            title="Excluir dispositivo"
          >
            <Trash2 className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>
    </div>
  );
}

/* ── Aba de Canais Externos & Webhooks ─────────────────────────────── */
function ChannelsTab() {
  const copy = (text: string) => {
    navigator.clipboard.writeText(text);
    toast.success('Copiado para a área de transferência!');
  };

  return (
    <div className="space-y-6">
      {/* Webchat Widget */}
      <section className="bg-bg-surface border border-border rounded-3xl p-6 sm:p-8 space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-border pb-4">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-2xl bg-purple-500/10 border border-purple-500/20 text-purple-400">
              <MessageSquare className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-base font-bold text-primary">Webchat Widget para Sites</h3>
              <p className="text-xs text-secondary">Incorpore o atendimento automatizado em landing pages, lojas ou WordPress</p>
            </div>
          </div>
          <button
            onClick={() => {
              if (!document.getElementById('acassia-widget-container')) {
                const s = document.createElement('script');
                s.src = '/assets/widget.js';
                s.setAttribute('data-site-key', 'SUA_SITE_KEY_AQUI');
                s.setAttribute('data-title', 'Atendimento');
                s.setAttribute('data-color', '#9333ea');
                document.body.appendChild(s);
                toast.success('Widget ativado no canto inferior direito!');
              } else {
                toast.success('Widget já está carregado na página.');
              }
            }}
            className="text-xs px-4 py-2 bg-purple-600/10 text-purple-400 hover:bg-purple-600/20 border border-purple-500/30 rounded-xl font-bold transition-all self-start sm:self-auto"
          >
            Testar Widget ao Vivo
          </button>
        </div>

        <p className="text-xs text-secondary leading-relaxed">
          Cole este snippet no código HTML antes do fechamento de <code className="bg-bg-primary px-1.5 py-0.5 rounded border border-border text-primary font-mono">&lt;/body&gt;</code>:
        </p>

        <div className="relative">
          <pre className="p-4 bg-bg-primary border border-border rounded-2xl font-mono text-xs text-primary overflow-x-auto leading-relaxed">
{`<script 
  src="${typeof window !== 'undefined' ? window.location.origin : ''}/assets/widget.js" 
  data-site-key="SUA_SITE_KEY_AQUI" 
  data-title="Atendimento" 
  data-color="#25D366">
</script>`}
          </pre>
          <button
            onClick={() => copy(`<script src="${window.location.origin}/assets/widget.js" data-site-key="SUA_SITE_KEY_AQUI" data-title="Atendimento" data-color="#25D366"></script>`)}
            className="absolute top-3 right-3 p-2 bg-bg-surface border border-border hover:bg-bg-primary rounded-xl text-secondary hover:text-primary transition-all shadow-sm"
            title="Copiar snippet"
          >
            <Copy className="w-4 h-4" />
          </button>
        </div>
      </section>

      {/* Telegram Bot */}
      <section className="bg-bg-surface border border-border rounded-3xl p-6 sm:p-8 space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-border pb-4">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-2xl bg-sky-500/10 border border-sky-500/20 text-sky-400">
              <Send className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-base font-bold text-primary">Canal Telegram Bot</h3>
              <p className="text-xs text-secondary">Conecte um bot do Telegram ao mesmo motor inteligente de atendimento</p>
            </div>
          </div>
          <a
            href="https://t.me/BotFather"
            target="_blank"
            rel="noopener noreferrer"
            className="text-xs px-4 py-2 bg-sky-500/10 text-sky-400 hover:bg-sky-500/20 border border-sky-500/30 rounded-xl font-bold transition-all flex items-center gap-1.5 self-start sm:self-auto"
          >
            Abrir @BotFather <ExternalLink className="w-3 h-3" />
          </a>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          <div className="sm:col-span-2">
            <label className="text-[10px] font-bold uppercase tracking-wider text-secondary block mb-1">
              Token do Bot Telegram (@BotFather)
            </label>
            <input
              type="password"
              id="telegram-token-hub"
              placeholder="123456789:ABCdefGHIjklMNOpqrsTUVwxyz"
              className="w-full bg-bg-primary border border-border rounded-xl px-3.5 py-2.5 text-xs font-mono text-primary focus:outline-none focus:border-sky-500"
            />
          </div>
          <div className="flex items-end">
            <button
              type="button"
              onClick={async () => {
                const el = document.getElementById('telegram-token-hub') as HTMLInputElement;
                const token = el ? el.value.trim() : '';
                if (!token) {
                  toast.error('Informe o token do bot.');
                  return;
                }
                try {
                  const res = await fetch('/api/webhooks/telegram/setup', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                      bot_token: token,
                      tenant_id: 'default',
                      server_url: window.location.origin,
                    }),
                  });
                  const d = await res.json();
                  if (d.ok) toast.success('Webhook do Telegram configurado!');
                  else toast.error(d.telegram_response?.description || 'Falha ao registrar.');
                } catch (e: any) {
                  toast.error(e?.message || 'Erro');
                }
              }}
              className="w-full py-2.5 px-4 bg-sky-500 hover:bg-sky-600 text-white rounded-xl text-xs font-bold transition-all shadow-md shadow-sky-500/20"
            >
              Ativar Webhook Telegram
            </button>
          </div>
        </div>
      </section>

      {/* Swagger & n8n docs */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
        <section className="bg-bg-surface border border-border rounded-3xl p-6 space-y-3">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-xl bg-emerald-500/10 text-emerald-400">
              <BookOpen className="w-5 h-5" />
            </div>
            <div>
              <h4 className="text-sm font-bold text-primary">Documentação OpenAPI / Swagger</h4>
              <p className="text-[11px] text-secondary">Endpoints REST para envio e consulta</p>
            </div>
          </div>
          <p className="text-xs text-secondary leading-relaxed">
            Consulte todos os endpoints para envio ativo de mensagens, consulta de leads e status de disparos.
          </p>
          <a
            href="/docs"
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-2 text-xs text-[#25D366] hover:underline font-bold pt-1"
          >
            Abrir Swagger Interativo <ExternalLink className="w-3.5 h-3.5" />
          </a>
        </section>

        <section className="bg-bg-surface border border-border rounded-3xl p-6 space-y-3">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-xl bg-amber-500/10 text-amber-400">
              <Sparkles className="w-5 h-5" />
            </div>
            <div>
              <h4 className="text-sm font-bold text-primary">Automações com n8n / Make</h4>
              <p className="text-[11px] text-secondary">Integração via Webhook de Eventos</p>
            </div>
          </div>
          <p className="text-xs text-secondary leading-relaxed">
            Dispare fluxos externos no n8n a cada nova venda ou mensagem recebida usando os Webhooks de Saída.
          </p>
          <a
            href="/settings/webhooks"
            className="inline-flex items-center gap-2 text-xs text-amber-400 hover:underline font-bold pt-1"
          >
            Configurar Webhooks de Saída <ExternalLink className="w-3.5 h-3.5" />
          </a>
        </section>
      </div>
    </div>
  );
}

/* ── Modal Meta Embedded Signup ─────────────────────────────── */
function MetaEmbeddedModal({
  config,
  onClose,
  onSuccess,
  onFallbackManual,
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
      toast.success('WhatsApp conectado via Meta Embedded Signup!');
      onSuccess();
    },
    onError: (err: any) => toast.error(err?.message || 'Falha ao autorizar com a Meta.'),
  });

  const effectiveAppId = config?.app_id || '2344565976011888';
  const isConfigured = Boolean(config?.configured || effectiveAppId);

  const launchMetaOAuth = () => {
    const redirectUri = `${window.location.origin}/builder/wa-connection`;
    const version = config?.graph_version || 'v20.0';
    const oauthUrl = `https://www.facebook.com/${version}/dialog/oauth?client_id=${effectiveAppId}&redirect_uri=${encodeURIComponent(
      redirectUri
    )}&response_type=code&scope=whatsapp_business_management,whatsapp_business_messaging`;

    const width = 600;
    const height = 700;
    const left = window.screenX + (window.outerWidth - width) / 2;
    const top = window.screenY + (window.outerHeight - height) / 2;
    const popup = window.open(
      oauthUrl,
      'MetaEmbeddedSignup',
      `width=${width},height=${height},left=${left},top=${top},status=no,toolbar=no,menubar=no`
    );

    const handleMessage = (event: MessageEvent) => {
      if (!event.origin.includes(window.location.hostname) && !event.origin.includes('facebook.com')) return;
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
    <div className="fixed inset-0 z-[100] bg-black/80 backdrop-blur-md flex items-center justify-center p-4 sm:p-6" onClick={onClose}>
      <div onClick={(e) => e.stopPropagation()} className="bg-zinc-950 border border-zinc-800 rounded-3xl shadow-2xl max-w-lg w-full overflow-hidden flex flex-col max-h-[92vh]">
        <header className="flex items-center justify-between px-6 py-4 border-b border-zinc-800 bg-zinc-900/50">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-2xl bg-blue-600/20 border border-blue-500/30 flex items-center justify-center text-[#0082FB]">
              <MetaLogo className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-base font-bold text-zinc-100">Conectar via Meta</h3>
                <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-blue-500/10 text-blue-400 border border-blue-500/30">
                  Cloud API Oficial
                </span>
              </div>
              <p className="text-xs text-zinc-400">Embedded Signup & Vinculação Direta</p>
            </div>
          </div>
          <button onClick={onClose} className="p-2 rounded-xl hover:bg-zinc-800 text-zinc-400 hover:text-zinc-200 transition-colors">
            <X className="w-4 h-4" />
          </button>
        </header>

        <div className="p-6 space-y-5 overflow-y-auto flex-1">
          {/* Banner de destaque 1 clique */}
          <div className="p-4 rounded-2xl bg-gradient-to-br from-blue-600/15 via-blue-900/10 to-transparent border border-blue-500/30 space-y-3">
            <div className="flex items-start gap-3">
              <div className="p-2 rounded-xl bg-blue-500/20 text-blue-400 shrink-0 mt-0.5">
                <Sparkles className="w-4 h-4" />
              </div>
              <div>
                <h4 className="text-xs font-bold text-zinc-100">Conexão Oficial em 1 Clique (Recomendado)</h4>
                <p className="text-[11px] text-zinc-300 mt-0.5 leading-relaxed">
                  Autorize o WhatsApp Business diretamente pela janela oficial do Facebook / Meta. Seus números e tokens são configurados automaticamente.
                </p>
              </div>
            </div>

            <div>
              <label className="text-xs font-semibold text-zinc-300 block mb-1">Apelido do número</label>
              <input
                value={nickname}
                onChange={(e) => setNickname(e.target.value)}
                placeholder="Ex: WhatsApp Comercial, Suporte..."
                className="w-full px-3.5 py-2 bg-zinc-900 border border-zinc-700/80 rounded-xl text-xs text-zinc-100 placeholder:text-zinc-500 focus:outline-none focus:border-blue-500"
              />
            </div>

            <button
              type="button"
              onClick={launchMetaOAuth}
              disabled={exchangeMut.isPending}
              className="w-full flex items-center justify-center gap-2.5 py-3 bg-[#0082FB] hover:bg-[#0070db] text-white rounded-xl font-bold text-xs shadow-lg shadow-[#0082FB]/25 transition-all active:scale-[0.99] disabled:opacity-50"
            >
              <MetaLogo className="w-4 h-4" />
              <span>{exchangeMut.isPending ? 'Autenticando na Meta...' : 'Continuar com Facebook / Meta'}</span>
            </button>
          </div>

          {/* Divisor */}
          <div className="flex items-center gap-3">
            <div className="h-px bg-zinc-800 flex-1" />
            <span className="text-[10px] font-bold uppercase tracking-wider text-zinc-500">ou autorização por código / manual</span>
            <div className="h-px bg-zinc-800 flex-1" />
          </div>

          {/* Opção Manual / Código */}
          <div className="p-4 rounded-2xl bg-zinc-900/60 border border-zinc-800 space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-zinc-200">Código de Autorização Meta</span>
              <button
                type="button"
                onClick={() => setShowManualCode(!showManualCode)}
                className="text-[11px] text-blue-400 hover:text-blue-300 font-medium underline"
              >
                {showManualCode ? 'Ocultar' : 'Inserir código'}
              </button>
            </div>

            {showManualCode && (
              <div className="space-y-3 pt-2">
                <p className="text-[11px] text-zinc-400 leading-relaxed">
                  Caso o popup do Facebook retorne um código na URL ou console, você pode colá-lo aqui diretamente para troca imediata de token.
                </p>
                <div>
                  <label className="text-[11px] font-medium text-zinc-400 block mb-1">Authorization Code</label>
                  <input
                    value={code}
                    onChange={(e) => setCode(e.target.value)}
                    placeholder="AQB... ou código de autorização retornado"
                    className="w-full px-3 py-2 bg-zinc-950 border border-zinc-700/80 rounded-xl text-xs text-zinc-100 placeholder:text-zinc-600 font-mono focus:outline-none focus:border-blue-500"
                  />
                </div>
                <div className="grid grid-cols-2 gap-2">
                  <div>
                    <label className="text-[11px] font-medium text-zinc-400 block mb-1">Phone Number ID (opcional)</label>
                    <input
                      value={phoneNumberId}
                      onChange={(e) => setPhoneNumberId(e.target.value)}
                      placeholder="Ex: 1126244453895124"
                      className="w-full px-3 py-2 bg-zinc-950 border border-zinc-700/80 rounded-xl text-xs text-zinc-100 placeholder:text-zinc-600 font-mono focus:outline-none focus:border-blue-500"
                    />
                  </div>
                  <div>
                    <label className="text-[11px] font-medium text-zinc-400 block mb-1">WABA ID (opcional)</label>
                    <input
                      value={wabaId}
                      onChange={(e) => setWabaId(e.target.value)}
                      placeholder="Ex: 1443823057400060"
                      className="w-full px-3 py-2 bg-zinc-950 border border-zinc-700/80 rounded-xl text-xs text-zinc-100 placeholder:text-zinc-600 font-mono focus:outline-none focus:border-blue-500"
                    />
                  </div>
                </div>
                <button
                  type="button"
                  onClick={() => exchangeMut.mutate({ code, phone_number_id: phoneNumberId, waba_id: wabaId, nickname })}
                  disabled={!code.trim() || exchangeMut.isPending}
                  className="w-full py-2.5 bg-blue-600 hover:bg-blue-500 text-white rounded-xl text-xs font-bold transition-all disabled:opacity-40 shadow-md"
                >
                  {exchangeMut.isPending ? 'Trocando código...' : 'Finalizar Conexão com Código'}
                </button>
              </div>
            )}

            <div className="pt-2 flex items-center justify-between border-t border-zinc-800/80">
              <button
                type="button"
                onClick={onFallbackManual}
                className="text-xs text-emerald-400 hover:text-emerald-300 font-semibold flex items-center gap-1.5"
              >
                <span>Inserir tokens manualmente</span> →
              </button>
              <a
                href="https://developers.facebook.com/apps"
                target="_blank"
                rel="noopener noreferrer"
                className="text-[11px] text-zinc-400 hover:text-zinc-200 flex items-center gap-1"
              >
                <ExternalLink className="w-3 h-3" /> Meta Developers
              </a>
            </div>
          </div>
        </div>

        <footer className="px-6 py-3 border-t border-zinc-800 bg-zinc-900/30 flex items-center justify-end">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 text-xs font-semibold text-zinc-400 hover:text-zinc-200 transition-colors"
          >
            Fechar
          </button>
        </footer>
      </div>
    </div>
  );
}
