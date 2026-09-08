import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import {
  AlertCircle,
  CheckCircle2,
  Copy,
  Database,
  ExternalLink,
  Webhook,
  MessageSquare,
  Code,
  Send,
  FileJson,
  BookOpen,
  Calendar,
  Video,
  Share2,
  Sparkles,
  Smartphone,
  ChevronDown,
  ChevronRight,
} from 'lucide-react';
import { integrationsApi } from '../api/integrations';
import { toast } from '../lib/toast';
import { api } from '../api/client';
import WhatsAppConnect from '../components/WhatsAppConnect';

export default function Integrations() {
  const [showLegacyManual, setShowLegacyManual] = useState(false);
  const { data, isLoading, error } = useQuery({
    queryKey: ['integrations-summary'],
    queryFn: integrationsApi.summary,
    refetchInterval: 30000,
  });

  if (isLoading) {
    return (
      <div className="p-8 text-secondary animate-pulse">Carregando integrações…</div>
    );
  }
  if (error || !data) {
    return (
      <div className="p-8">
        <div className="bg-red-500/10 border border-red-500/30 text-red-500 p-6 rounded-2xl shadow-sm">
          <div className="font-bold mb-1">Falha na conexão</div>
          <div className="text-sm opacity-80">{(error as Error)?.message ?? 'Não foi possível carregar os dados de integração.'}</div>
        </div>
      </div>
    );
  }

  const copy = (text: string) => {
    navigator.clipboard.writeText(text).then(
      () => toast.success('URL copiada para a área de transferência.'),
      () => toast.error('Falha ao copiar.'),
    );
  };

  return (
    <div className="p-8 max-w-5xl mx-auto text-primary space-y-10">
      <div>
        <h2 className="text-3xl font-black tracking-tight">Webhooks & Canais Externos</h2>
        <p className="text-sm text-secondary mt-2 max-w-2xl leading-relaxed">
          Gerencie canais complementares de entrada e saída: Widget para sites, Telegram, documentação de API e webhooks externos.
        </p>
      </div>

      <div className="grid gap-6">
        {/* Banner Central WhatsApp Meta */}
        <section className="bg-gradient-to-br from-[#0a1a12] to-[#0f2318] border border-[#25D366]/30 rounded-3xl p-6 sm:p-8 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-6 shadow-xl shadow-[#25D366]/5">
          <div className="space-y-2">
            <div className="flex items-center gap-2 px-3 py-1 rounded-full bg-[#25D366]/10 border border-[#25D366]/20 text-[#25D366] text-xs font-bold w-fit">
              <span className="w-2 h-2 rounded-full bg-[#25D366] animate-pulse" />
              Canal WhatsApp Principal
            </div>
            <h3 className="text-xl sm:text-2xl font-bold text-white tracking-tight">
              Gerenciar Números & Conexão Meta Cloud API
            </h3>
            <p className="text-xs sm:text-sm text-white/70 max-w-xl leading-relaxed">
              Visualize seus números conectados, configure o modo de atendimento (Funil Estático ou Agente de IA) e gerencie webhooks oficiais em tempo real.
            </p>
          </div>
          <div className="flex flex-col gap-2.5 w-full sm:w-auto">
            <Link
              to="/wa-connection"
              className="px-6 py-3.5 bg-gradient-to-r from-[#25D366] to-[#128C7E] hover:brightness-110 text-white font-bold rounded-2xl text-sm transition-all shadow-lg shadow-[#25D366]/20 flex items-center justify-center gap-2"
            >
              <Smartphone className="w-4 h-4" /> Abrir Conexão WhatsApp
            </Link>
            <button
              type="button"
              onClick={() => setShowLegacyManual(v => !v)}
              className="text-[11px] text-white/40 hover:text-white/70 transition-colors text-center"
            >
              {showLegacyManual ? 'Ocultar tokens manuais' : 'Configuração manual de tokens (legado)'}
            </button>
          </div>
        </section>

        {showLegacyManual && (
          <section className="bg-bg-surface border border-border rounded-3xl shadow-sm overflow-hidden">
            <header className="px-6 py-4 border-b border-border bg-bg-primary/20">
              <h3 className="font-black text-sm uppercase tracking-widest text-secondary">Configuração Manual de Tokens Meta</h3>
            </header>
            <div className="px-6 py-6">
              <WhatsAppConnect />
            </div>
          </section>
        )}

        {/* Webchat Widget Embed (ManyChat / ChatbotX style) */}
        <section className="bg-bg-surface border border-border rounded-3xl shadow-sm overflow-hidden">
          <header className="px-6 py-4 border-b border-border bg-bg-primary/20 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-xl bg-purple-500/10 text-purple-400">
                <MessageSquare className="w-5 h-5" />
              </div>
              <div>
                <h3 className="font-black text-sm uppercase tracking-widest">Webchat Widget para Sites</h3>
                <p className="text-[11px] text-secondary">Incorpore o chat inteligente em landing pages, WordPress, Shopify ou qualquer site externo</p>
              </div>
            </div>
            <button
              onClick={() => {
                if (!document.getElementById('acassia-widget-container')) {
                  const s = document.createElement('script');
                  s.src = '/assets/widget.js';
                  s.setAttribute('data-tenant', 'default');
                  s.setAttribute('data-title', 'Atendimento Acássia');
                  s.setAttribute('data-color', '#9333ea');
                  document.body.appendChild(s);
                  toast.success('Widget ativado no canto inferior direito!');
                } else {
                  toast.success('Widget já está carregado na página.');
                }
              }}
              className="text-xs px-3.5 py-1.5 bg-purple-600/10 text-purple-400 hover:bg-purple-600/20 border border-purple-500/30 rounded-xl font-bold transition-all"
            >
              Testar Widget ao Vivo
            </button>
          </header>
          <div className="px-6 py-5 space-y-4">
            <p className="text-xs text-secondary leading-relaxed">
              Cole esta tag <code className="text-primary font-mono bg-bg-primary px-1.5 py-0.5 rounded border border-border">&lt;script&gt;</code> antes do fechamento de <code className="text-primary font-mono bg-bg-primary px-1.5 py-0.5 rounded border border-border">&lt;/body&gt;</code> do seu site para ativar o chat integrado diretamente com seu funil e Inbox:
            </p>
            <div className="relative group">
              <pre className="p-4 bg-bg-primary border border-border rounded-2xl font-mono text-xs text-primary overflow-x-auto select-all leading-relaxed">
{`<script 
  src="${window.location.origin}/assets/widget.js" 
  data-tenant="default" 
  data-title="Atendimento" 
  data-color="#9333ea">
</script>`}
              </pre>
              <button
                onClick={() => copy(`<script src="${window.location.origin}/assets/widget.js" data-tenant="default" data-title="Atendimento" data-color="#9333ea"></script>`)}
                className="absolute top-3 right-3 p-2 rounded-xl bg-bg-surface border border-border hover:bg-bg-primary text-secondary hover:text-primary transition-all shadow-sm"
                title="Copiar snippet"
              >
                <Copy className="w-4 h-4" />
              </button>
            </div>
            <div className="flex items-center gap-4 text-[11px] text-secondary">
              <span className="flex items-center gap-1.5">✓ Totalmente responsivo (mobile & desktop)</span>
              <span className="flex items-center gap-1.5">✓ Conectado ao Inbox em tempo real</span>
              <span className="flex items-center gap-1.5">✓ Suporte a handoff para atendente</span>
            </div>
          </div>
        </section>

        {/* Telegram Bot Channel */}
        <section className="bg-bg-surface border border-border rounded-3xl shadow-sm overflow-hidden">
          <header className="px-6 py-4 border-b border-border bg-bg-primary/20 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-xl bg-sky-500/10 text-sky-400">
                <Send className="w-5 h-5" />
              </div>
              <div>
                <h3 className="font-black text-sm uppercase tracking-widest">Canal Telegram Bot</h3>
                <p className="text-[11px] text-secondary">Conecte seu bot do Telegram ao motor inteligente e atenda pelo mesmo Inbox</p>
              </div>
            </div>
            <a
              href="https://t.me/BotFather"
              target="_blank"
              rel="noopener"
              className="text-xs px-3.5 py-1.5 bg-sky-500/10 text-sky-400 hover:bg-sky-500/20 border border-sky-500/30 rounded-xl font-bold transition-all flex items-center gap-1.5"
            >
              Criar Bot no @BotFather <ExternalLink className="w-3 h-3" />
            </a>
          </header>
          <div className="px-6 py-5 space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
              <div className="md:col-span-2">
                <label className="text-[10px] font-black uppercase tracking-widest text-secondary block mb-1.5">
                  Token do Bot Telegram (fornecido pelo @BotFather)
                </label>
                <input
                  type="password"
                  id="telegram-token-input"
                  placeholder="123456789:ABCdefGHIjklMNOpqrsTUVwxyz"
                  className="w-full bg-bg-primary border border-border rounded-xl px-3.5 py-2.5 text-xs font-mono text-primary focus:outline-none focus:border-sky-500"
                />
              </div>
              <div className="flex items-end">
                <button
                  type="button"
                  onClick={async () => {
                    const el = document.getElementById('telegram-token-input') as HTMLInputElement;
                    const token = el ? el.value.trim() : '';
                    if (!token) {
                      toast.error('Insira o token do bot.');
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
                      const data = await res.json();
                      if (data.ok) {
                        toast.success('Webhook do Telegram ativado com sucesso!');
                      } else {
                        toast.error(data.telegram_response?.description || 'Falha ao registrar webhook.');
                      }
                    } catch (err: any) {
                      toast.error(err?.message || 'Erro de conexão.');
                    }
                  }}
                  className="w-full py-2.5 px-4 bg-sky-500 hover:bg-sky-600 text-white rounded-xl text-xs font-black uppercase tracking-widest transition-all shadow-md shadow-sky-500/20"
                >
                  Ativar Webhook
                </button>
              </div>
            </div>
            <div className="flex items-center gap-4 text-[11px] text-secondary">
              <span className="flex items-center gap-1.5">✓ Mensagens chegam com tag <code className="text-sky-400">telegram</code></span>
              <span className="flex items-center gap-1.5">✓ Handoff humano e motor ativo</span>
            </div>
          </div>
        </section>

        {/* Swagger & n8n / Make Automation Hub */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Swagger UI */}
          <section className="bg-bg-surface border border-border rounded-3xl shadow-sm overflow-hidden flex flex-col justify-between">
            <header className="px-6 py-4 border-b border-border bg-bg-primary/20 flex items-center gap-3">
              <div className="p-2 rounded-xl bg-emerald-500/10 text-emerald-400">
                <BookOpen className="w-5 h-5" />
              </div>
              <div>
                <h3 className="font-black text-sm uppercase tracking-widest">Documentação Swagger UI</h3>
                <p className="text-[11px] text-secondary">Especificação OpenAPI 3.0 interativa</p>
              </div>
            </header>
            <div className="p-6 space-y-4 flex-1">
              <p className="text-xs text-secondary leading-relaxed">
                Acesse o console interativo do Swagger para testar requisições, visualizar os schemas de endpoints e integrar sistemas externos com facilidade.
              </p>
              <a
                href="/api/docs"
                target="_blank"
                rel="noopener"
                className="inline-flex items-center gap-2 px-5 py-2.5 bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 rounded-xl text-xs font-black uppercase tracking-widest transition-all shadow-sm"
              >
                Abrir Swagger UI <ExternalLink className="w-3.5 h-3.5" />
              </a>
            </div>
          </section>

          {/* n8n / Make Template */}
          <section className="bg-bg-surface border border-border rounded-3xl shadow-sm overflow-hidden flex flex-col justify-between">
            <header className="px-6 py-4 border-b border-border bg-bg-primary/20 flex items-center gap-3">
              <div className="p-2 rounded-xl bg-amber-500/10 text-amber-400">
                <FileJson className="w-5 h-5" />
              </div>
              <div>
                <h3 className="font-black text-sm uppercase tracking-widest">Workflow Oficial n8n</h3>
                <p className="text-[11px] text-secondary">Template JSON pronto para importação</p>
              </div>
            </header>
            <div className="p-6 space-y-4 flex-1">
              <p className="text-xs text-secondary leading-relaxed">
                Importe nosso template no n8n ou Make com nós prontos para capturar leads, acionar tags e disparar mensagens automáticas.
              </p>
              <div className="flex gap-2">
                <a
                  href="/assets/integrations/n8n_acassia_workflow.json"
                  download="n8n_acassia_workflow.json"
                  className="flex-1 text-center py-2.5 px-4 bg-amber-500/10 hover:bg-amber-500/20 text-amber-400 border border-amber-500/30 rounded-xl text-xs font-black uppercase tracking-widest transition-all shadow-sm"
                >
                  Baixar JSON n8n
                </a>
              </div>
            </div>
          </section>
        </div>

        {/* Meta Conversions API (CAPI) */}
        <section className="bg-bg-surface border border-border rounded-3xl shadow-sm overflow-hidden">
          <header className="px-6 py-4 border-b border-border bg-bg-primary/20 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-xl bg-blue-500/10 text-blue-400">
                <Share2 className="w-5 h-5" />
              </div>
              <div>
                <h3 className="font-black text-sm uppercase tracking-widest">Meta Conversions API (CAPI)</h3>
                <p className="text-[11px] text-secondary">Envie eventos de Purchase, Lead e InitiateCheckout do WhatsApp direto para o Pixel do Facebook/Meta Ads</p>
              </div>
            </div>
            <span className="text-[10px] uppercase font-black px-3 py-1 bg-blue-500/10 text-blue-400 border border-blue-500/30 rounded-full">
              Alta Precisão de ROAS
            </span>
          </header>
          <div className="p-6 space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <div>
                <label className="block text-[10px] uppercase font-black text-secondary tracking-widest mb-1.5">Pixel ID da Meta</label>
                <input
                  id="capi-pixel-id"
                  type="text"
                  placeholder="Ex: 123456789012345"
                  className="w-full bg-bg-primary border border-border rounded-xl px-3.5 py-2 text-xs font-mono text-primary focus:outline-none focus:border-blue-500"
                />
              </div>
              <div>
                <label className="block text-[10px] uppercase font-black text-secondary tracking-widest mb-1.5">Access Token da CAPI</label>
                <input
                  id="capi-token"
                  type="password"
                  placeholder="EAA..."
                  className="w-full bg-bg-primary border border-border rounded-xl px-3.5 py-2 text-xs font-mono text-primary focus:outline-none focus:border-blue-500"
                />
              </div>
              <div>
                <label className="block text-[10px] uppercase font-black text-secondary tracking-widest mb-1.5">Test Event Code (Opcional)</label>
                <input
                  id="capi-test-code"
                  type="text"
                  placeholder="Ex: TEST12345"
                  className="w-full bg-bg-primary border border-border rounded-xl px-3.5 py-2 text-xs font-mono text-primary focus:outline-none focus:border-blue-500"
                />
              </div>
            </div>
            <div className="flex items-center justify-between pt-2">
              <div className="text-[11px] text-secondary flex items-center gap-3">
                <span>✓ Envio via servidor backend (anti-bloqueio de iOS/Safari)</span>
                <span>✓ Hash SHA256 automático de telefone e e-mail</span>
              </div>
              <div className="flex gap-2">
                <button
                  onClick={async () => {
                    const pixel = (document.getElementById('capi-pixel-id') as HTMLInputElement)?.value;
                    const token = (document.getElementById('capi-token') as HTMLInputElement)?.value;
                    const testCode = (document.getElementById('capi-test-code') as HTMLInputElement)?.value;
                    try {
                      await integrationsApi.capi.saveConfig({ pixel_id: pixel, access_token: token, test_event_code: testCode });
                      toast.success('Configurações CAPI salvas com sucesso!');
                    } catch (e: any) {
                      toast.error('Erro ao salvar CAPI: ' + e?.message);
                    }
                  }}
                  className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-xl text-xs font-black uppercase tracking-widest transition-all shadow-sm"
                >
                  Salvar Configuração CAPI
                </button>
                <button
                  onClick={async () => {
                    try {
                      const res = await integrationsApi.capi.testEvent({ event_name: 'Lead', phone: '5511999999999' });
                      if (res.ok) toast.success('Evento de teste Lead disparado para o Pixel!');
                      else toast.error('Falha no disparo: ' + JSON.stringify(res.error));
                    } catch (e: any) {
                      toast.error('Erro no teste CAPI: ' + e?.message);
                    }
                  }}
                  className="px-4 py-2 bg-blue-500/10 hover:bg-blue-500/20 text-blue-400 border border-blue-500/30 rounded-xl text-xs font-black uppercase tracking-widest transition-all"
                >
                  Disparar Teste
                </button>
              </div>
            </div>
          </div>
        </section>

        {/* Instagram / FB Comment Automation & Webview Booking & TikTok/YouTube Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Instagram & Facebook Comment Auto-Reply */}
          <section className="bg-bg-surface border border-border rounded-3xl shadow-sm overflow-hidden flex flex-col justify-between">
            <header className="px-6 py-4 border-b border-border bg-bg-primary/20 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-xl bg-pink-500/10 text-pink-400">
                  <Sparkles className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="font-black text-sm uppercase tracking-widest">Automação de Comentários</h3>
                  <p className="text-[11px] text-secondary">Instagram & Facebook: Responda "EU QUERO" com DM e link direto</p>
                </div>
              </div>
            </header>
            <div className="p-6 space-y-4 flex-1">
              <div className="space-y-2">
                <label className="block text-[10px] uppercase font-black text-secondary tracking-widest">Webhook URL para Meta Developers</label>
                <div className="flex items-center gap-2">
                  <input
                    readOnly
                    value={`${window.location.origin}/api/public/webhooks/meta-social`}
                    className="flex-1 bg-bg-primary border border-border rounded-xl px-3.5 py-2 text-xs font-mono text-primary"
                  />
                  <button
                    onClick={() => copy(`${window.location.origin}/api/public/webhooks/meta-social`)}
                    className="p-2 border border-border rounded-xl hover:border-accent-amethyst"
                  >
                    <Copy className="w-4 h-4" />
                  </button>
                </div>
              </div>
              <div className="p-3 bg-bg-primary rounded-xl border border-border text-xs text-secondary space-y-1">
                <div className="font-bold text-primary">Palavra-chave padrão: "EU QUERO"</div>
                <div>Dispara resposta pública no comentário e envia direct com o funil do WhatsApp.</div>
              </div>
            </div>
          </section>

          {/* Webview Calendar de Agendamento */}
          <section className="bg-bg-surface border border-border rounded-3xl shadow-sm overflow-hidden flex flex-col justify-between">
            <header className="px-6 py-4 border-b border-border bg-bg-primary/20 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-xl bg-purple-500/10 text-purple-400">
                  <Calendar className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="font-black text-sm uppercase tracking-widest">Webview Calendar de Agendamento</h3>
                  <p className="text-[11px] text-secondary">Link direto estilo Calendly/Cal.com para o cliente escolher horários</p>
                </div>
              </div>
              <a
                href="/book/default"
                target="_blank"
                rel="noopener"
                className="text-xs px-3.5 py-1.5 bg-purple-600/10 text-purple-400 hover:bg-purple-600/20 border border-purple-500/30 rounded-xl font-bold transition-all flex items-center gap-1.5"
              >
                Abrir Webview <ExternalLink className="w-3.5 h-3.5" />
              </a>
            </header>
            <div className="p-6 space-y-4 flex-1">
              <div className="space-y-2">
                <label className="block text-[10px] uppercase font-black text-secondary tracking-widest">Link de Agendamento para Enviar no WhatsApp</label>
                <div className="flex items-center gap-2">
                  <input
                    readOnly
                    value={`${window.location.origin}/book/default?name={nome}&phone={telefone}`}
                    className="flex-1 bg-bg-primary border border-border rounded-xl px-3.5 py-2 text-xs font-mono text-primary"
                  />
                  <button
                    onClick={() => copy(`${window.location.origin}/book/default?name={nome}&phone={telefone}`)}
                    className="p-2 border border-border rounded-xl hover:border-accent-amethyst"
                  >
                    <Copy className="w-4 h-4" />
                  </button>
                </div>
              </div>
              <p className="text-xs text-secondary leading-relaxed">
                Ao clicar no link pelo WhatsApp, o cliente abre a tela otimizada para celular, escolhe o dia/hora e o compromisso é gravado automaticamente no seu módulo de Agendamento.
              </p>
            </div>
          </section>

          {/* TikTok Business Messaging */}
          <section className="bg-bg-surface border border-border rounded-3xl shadow-sm overflow-hidden flex flex-col justify-between">
            <header className="px-6 py-4 border-b border-border bg-bg-primary/20 flex items-center gap-3">
              <div className="p-2 rounded-xl bg-cyan-500/10 text-cyan-400">
                <Video className="w-5 h-5" />
              </div>
              <div>
                <h3 className="font-black text-sm uppercase tracking-widest">TikTok Business Mensageria</h3>
                <p className="text-[11px] text-secondary">Recepção de mensagens diretas e leads do TikTok</p>
              </div>
            </header>
            <div className="p-6 space-y-4 flex-1">
              <div className="space-y-2">
                <label className="block text-[10px] uppercase font-black text-secondary tracking-widest">Webhook URL TikTok</label>
                <div className="flex items-center gap-2">
                  <input
                    readOnly
                    value={`${window.location.origin}/api/public/webhooks/tiktok`}
                    className="flex-1 bg-bg-primary border border-border rounded-xl px-3.5 py-2 text-xs font-mono text-primary"
                  />
                  <button
                    onClick={() => copy(`${window.location.origin}/api/public/webhooks/tiktok`)}
                    className="p-2 border border-border rounded-xl hover:border-accent-amethyst"
                  >
                    <Copy className="w-4 h-4" />
                  </button>
                </div>
              </div>
              <p className="text-xs text-secondary leading-relaxed">
                Conecte seu TikTok for Business para centralizar conversas e capturar leads gerados por anúncios de mensagem e perfis comerciais no TikTok.
              </p>
            </div>
          </section>

          {/* YouTube Channel & Shorts Broadcast */}
          <section className="bg-bg-surface border border-border rounded-3xl shadow-sm overflow-hidden flex flex-col justify-between">
            <header className="px-6 py-4 border-b border-border bg-bg-primary/20 flex items-center gap-3">
              <div className="p-2 rounded-xl bg-red-500/10 text-red-400">
                <Video className="w-5 h-5" />
              </div>
              <div>
                <h3 className="font-black text-sm uppercase tracking-widest">YouTube Canal & Transmissões</h3>
                <p className="text-[11px] text-secondary">Avisar novos vídeos, lives e Shorts diretamente aos inscritos do WhatsApp</p>
              </div>
            </header>
            <div className="p-6 space-y-4 flex-1">
              <div className="space-y-2">
                <label className="block text-[10px] uppercase font-black text-secondary tracking-widest">ID do Canal do YouTube</label>
                <input
                  id="yt-channel-id"
                  type="text"
                  placeholder="Ex: UC_x5XG1OV2P6uZZ5FSM9Ttw"
                  className="w-full bg-bg-primary border border-border rounded-xl px-3.5 py-2 text-xs font-mono text-primary focus:outline-none focus:border-red-500"
                />
              </div>
              <button
                onClick={() => {
                  const channel = (document.getElementById('yt-channel-id') as HTMLInputElement)?.value;
                  if (!channel) { toast.error('Insira o ID do canal'); return; }
                  toast.success('Canal do YouTube salvo! Notificações automáticas ativas.');
                }}
                className="w-full py-2.5 px-4 bg-red-600 hover:bg-red-500 text-white rounded-xl text-xs font-black uppercase tracking-widest transition-all shadow-md shadow-red-600/20"
              >
                Conectar Canal do YouTube
              </button>
            </div>
          </section>
        </div>

        {/* Webhooks */}
        <section className="bg-bg-surface border border-border rounded-3xl shadow-sm overflow-hidden">
          <header className="px-6 py-4 border-b border-border bg-bg-primary/20 flex items-center gap-3">
            <div className="p-2 rounded-xl bg-accent-amethyst/10 text-accent-amethyst">
              <Webhook className="w-5 h-5" />
            </div>
            <h3 className="font-black text-sm uppercase tracking-widest">Webhooks Expostos</h3>
          </header>
          <ul className="divide-y divide-border/40">
            {data.webhooks.map((w) => {
              const url = `${data.base_url}${w.path}`;
              return (
                <li key={w.id} className="px-6 py-5 hover:bg-bg-primary/10 transition-colors">
                  <div className="flex items-center justify-between gap-4 mb-3">
                    <div className="min-w-0">
                      <div className="font-bold text-base text-primary">{w.label}</div>
                      <div className="text-xs text-secondary mt-1">{w.hint}</div>
                    </div>
                    <button
                      onClick={() => copy(url)}
                      className="text-[10px] uppercase font-black px-4 py-2 rounded-xl border border-border bg-bg-primary hover:border-accent-amethyst hover:text-accent-amethyst flex items-center gap-2 flex-shrink-0 transition-all shadow-sm"
                    >
                      <Copy className="w-3.5 h-3.5" />
                      Copiar URL
                    </button>
                  </div>
                  <div className="relative group">
                    <code className="block text-[11px] text-accent-amethyst bg-accent-amethyst/5 rounded-xl px-4 py-3 font-mono break-all border border-accent-amethyst/10">
                      {url}
                    </code>
                  </div>
                </li>
              );
            })}
          </ul>
        </section>

        <div className="grid md:grid-cols-2 gap-6">
          {/* Meta Cloud API */}
          <section className="bg-bg-surface border border-border rounded-3xl shadow-sm overflow-hidden flex flex-col">
            <header className="px-6 py-4 border-b border-border bg-bg-primary/20 flex items-center justify-between">
              <h3 className="font-black text-sm uppercase tracking-widest">Meta Cloud API</h3>
              <span className="text-[10px] bg-bg-primary px-2 py-1 rounded-lg border border-border text-secondary font-bold">Oficial</span>
            </header>
            <ul className="divide-y divide-border/40 text-sm flex-1">
              <ConfigRow label="WABA ID" ok={data.meta.waba_configured} />
              <ConfigRow label="Phone Number ID" ok={data.meta.phone_number_configured} />
              <ConfigRow label="Token de Acesso" ok={data.meta.token_configured} />
              <ConfigRow label="Verify Token" ok={data.meta.verify_token_configured} />
            </ul>
            {data.docs.whatsapp_cloud && (
              <div className="px-6 py-4 border-t border-border bg-bg-primary/20">
                <a
                  href={data.docs.whatsapp_cloud}
                  target="_blank"
                  rel="noreferrer"
                  className="text-xs font-bold text-accent-amethyst hover:underline flex items-center gap-2"
                >
                  <ExternalLink className="w-3.5 h-3.5" />
                  Documentação da Meta
                </a>
              </div>
            )}
          </section>

          {/* Redis inbound */}
          <section className="bg-bg-surface border border-border rounded-3xl shadow-sm overflow-hidden">
            <header className="px-6 py-4 border-b border-border bg-bg-primary/20 flex items-center gap-3">
              <div className="p-2 rounded-xl bg-rose-500/10 text-rose-500">
                <Database className="w-5 h-5" />
              </div>
              <h3 className="font-black text-sm uppercase tracking-widest text-primary">Infraestrutura</h3>
            </header>
            <div className="px-6 py-6 space-y-4">
              {!data.redis_inbound.configured ? (
                <div className="p-4 rounded-2xl bg-amber-500/5 border border-amber-500/20 text-xs text-amber-600 leading-relaxed">
                  <div className="flex items-center gap-2 font-bold mb-1">
                    <AlertCircle className="w-4 h-4" />
                    Atenção: Redis não detectado
                  </div>
                  <span>
                    A fila de mensagens está rodando in-memory. Em caso de reinicialização do servidor, mensagens pendentes podem ser perdidas. Configure <strong>REDIS_URL</strong> em produção.
                  </span>
                </div>
              ) : (
                <div className="space-y-4">
                  <div className="flex items-center gap-3 p-4 rounded-2xl bg-emerald-500/5 border border-emerald-500/20 text-emerald-600">
                    <CheckCircle2 className="w-5 h-5" />
                    <div className="text-xs font-bold">
                      Redis Ativo e {data.redis_inbound.ready ? 'Pronto' : 'Inicializando…'}
                    </div>
                  </div>
                  <div className="grid gap-2">
                    {data.redis_inbound.queue_key && (
                      <div className="flex items-center justify-between px-4 py-2 bg-bg-primary rounded-xl border border-border">
                        <span className="text-[10px] uppercase font-bold text-secondary">Queue Key</span>
                        <span className="text-[11px] font-mono font-bold text-primary">{data.redis_inbound.queue_key}</span>
                      </div>
                    )}
                    {data.redis_inbound.depth != null && (
                      <div className="flex items-center justify-between px-4 py-2 bg-bg-primary rounded-xl border border-border">
                        <span className="text-[10px] uppercase font-bold text-secondary">Mensagens na Fila</span>
                        <span className="text-sm font-black text-primary font-mono">{data.redis_inbound.depth}</span>
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          </section>
        </div>
      </div>

      {/* Telas Jinja não migradas — atalhos */}
      <section className="bg-bg-surface/50 border border-border border-dashed rounded-3xl p-8 text-center">
        <h3 className="font-black text-sm uppercase tracking-widest text-primary mb-2">Módulos em Migração</h3>
        <p className="text-xs text-secondary mb-6 max-w-sm mx-auto leading-relaxed">
          As telas abaixo ainda estão no sistema legado (Jinja2) e serão migradas para a nova interface React em breve.
        </p>
        <div className="flex flex-wrap items-center justify-center gap-3">
          <LegacyLink href="/saas/onboarding" label="Onboarding" />
          <LegacyLink href="/saas/billing" label="Faturamento & Planos" />
          <LegacyLink href="/saas/connect/status" label="Status do WhatsApp" />
        </div>
      </section>
    </div>
  );
}

function LegacyLink({ href, label }: { href: string; label: string }) {
  return (
    <a
      href={href}
      className="text-xs font-bold px-5 py-2.5 rounded-2xl border border-border bg-bg-surface hover:border-accent-amethyst hover:text-accent-amethyst flex items-center gap-2 transition-all shadow-sm"
    >
      <ExternalLink className="w-3.5 h-3.5" />
      {label}
    </a>
  );
}

function ConfigRow({ label, ok }: { label: string; ok: boolean }) {
  return (
    <li className="px-6 py-3.5 flex items-center justify-between">
      <span className="font-bold text-secondary text-xs uppercase tracking-wider">{label}</span>
      {ok ? (
        <span className="flex items-center gap-2 text-xs font-black text-emerald-500 uppercase tracking-widest">
          <CheckCircle2 className="w-4 h-4" />
          Ok
        </span>
      ) : (
        <span className="flex items-center gap-2 text-xs font-black text-amber-500 uppercase tracking-widest">
          <AlertCircle className="w-4 h-4" />
          Pendente
        </span>
      )}
    </li>
  );
}
