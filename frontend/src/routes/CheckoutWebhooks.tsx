import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Webhook, Copy, Check, RefreshCw, ExternalLink,
  ShoppingCart, CreditCard, BarChart3, AlertCircle
} from 'lucide-react';
import { api } from '../api/client';
import { toast } from '../lib/toast';

export default function CheckoutWebhooks() {
  const qc = useQueryClient();
  const [tab, setTab] = useState<'setup' | 'events' | 'stats'>('setup');
  const [copied, setCopied] = useState('');

  const { data: setupData } = useQuery({
    queryKey: ['checkout-setup'],
    queryFn: () => api.get<{
      tenant_id: string;
      webhooks: Record<string, string>;
      instructions: Record<string, string>;
    }>('/saas/checkout/setup-info'),
  });

  const { data: eventsData } = useQuery({
    queryKey: ['checkout-events'],
    queryFn: () => api.get<{ events: any[]; total: number }>('/saas/checkout/events'),
    enabled: tab === 'events',
  });

  const { data: statsData } = useQuery({
    queryKey: ['checkout-stats'],
    queryFn: () => api.get<{
      by_platform: Record<string, number>; by_event: Record<string, number>;
      total_revenue: number; total_events: number;
    }>('/saas/checkout/stats'),
    enabled: tab === 'stats',
  });

  const copyUrl = (url: string, key: string) => {
    navigator.clipboard.writeText(url);
    setCopied(key);
    toast.success('URL copiada!');
    setTimeout(() => setCopied(''), 2000);
  };

  const platforms = [
    { key: 'hotmart', label: 'Hotmart', emoji: '🔥', color: 'from-orange-500 to-red-500' },
    { key: 'kiwify', label: 'Kiwify', emoji: '🥝', color: 'from-green-500 to-emerald-500' },
    { key: 'asaas', label: 'Asaas', emoji: '💳', color: 'from-blue-500 to-indigo-500' },
    { key: 'stripe', label: 'Stripe', emoji: '💎', color: 'from-purple-500 to-violet-500' },
  ];

  const eventLabels: Record<string, { label: string; emoji: string; color: string }> = {
    purchase_approved: { label: 'Compra Aprovada', emoji: '✅', color: 'text-emerald-400' },
    billet_printed: { label: 'Boleto Gerado', emoji: '📄', color: 'text-amber-400' },
    pix_generated: { label: 'PIX Gerado', emoji: '📱', color: 'text-cyan-400' },
    cart_abandoned: { label: 'Carrinho Abandonado', emoji: '🛒', color: 'text-rose-400' },
    refunded: { label: 'Reembolso', emoji: '↩️', color: 'text-red-400' },
    unknown: { label: 'Outro', emoji: '❓', color: 'text-secondary' },
  };

  return (
    <div className="px-8 py-8 max-w-[1400px] mx-auto min-h-screen">
      <div className="flex items-center gap-3 mb-8">
        <div className="w-12 h-12 rounded-2xl bg-gradient-to-br from-orange-500 to-red-600 flex items-center justify-center shadow-lg shadow-orange-500/30">
          <Webhook className="w-6 h-6 text-white" />
        </div>
        <div>
          <h1 className="font-display text-3xl text-primary tracking-tight">Checkout Webhooks</h1>
          <p className="text-xs text-secondary">Receba notificações de Hotmart, Kiwify, Asaas e Stripe</p>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex items-center gap-1 bg-bg-sidebar p-1 rounded-2xl border border-border mb-6 w-fit">
        {([
          { key: 'setup', label: 'Configuração', icon: Webhook },
          { key: 'events', label: 'Eventos', icon: ShoppingCart },
          { key: 'stats', label: 'Estatísticas', icon: BarChart3 },
        ] as const).map(t => (
          <button key={t.key} onClick={() => setTab(t.key)}
            className={`flex items-center gap-2 px-5 py-2.5 rounded-xl text-xs font-bold transition-all ${
              tab === t.key ? 'bg-bg-surface text-primary shadow-sm border border-border' : 'text-secondary hover:text-primary'
            }`}>
            <t.icon className="w-4 h-4" /> {t.label}
          </button>
        ))}
      </div>

      {/* SETUP */}
      {tab === 'setup' && setupData && (
        <div className="space-y-4">
          <div className="bg-bg-surface border border-border rounded-2xl p-6 mb-6">
            <h3 className="font-bold text-lg text-primary mb-2 flex items-center gap-2">
              <AlertCircle className="w-5 h-5 text-amber-500" /> Como funciona?
            </h3>
            <p className="text-xs text-secondary">
              Copie a URL da plataforma desejada e cole nas configurações de webhook dela.
              Quando um cliente comprar, gerar boleto ou abandonar o carrinho, o Meu Mistério
              receberá a notificação e atualizará o lead automaticamente no pipeline.
            </p>
          </div>

          {platforms.map(p => (
            <div key={p.key} className="bg-bg-surface border border-border rounded-2xl p-5 hover:border-indigo-500/30 transition-all">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className={`w-10 h-10 rounded-xl bg-gradient-to-br ${p.color} flex items-center justify-center`}>
                    <span className="text-lg">{p.emoji}</span>
                  </div>
                  <div>
                    <h3 className="font-bold text-sm text-primary">{p.label}</h3>
                    <p className="text-[10px] text-secondary">{setupData.instructions[p.key]}</p>
                  </div>
                </div>
                <button onClick={() => copyUrl(setupData.webhooks[p.key], p.key)}
                  className="flex items-center gap-2 px-4 py-2 bg-bg-sidebar border border-border rounded-xl text-xs font-bold text-primary hover:border-indigo-500/50 transition-all">
                  {copied === p.key ? <Check className="w-4 h-4 text-emerald-400" /> : <Copy className="w-4 h-4" />}
                  {copied === p.key ? 'Copiado!' : 'Copiar URL'}
                </button>
              </div>
              <div className="mt-3 p-2 bg-bg-sidebar rounded-lg">
                <code className="text-[10px] text-secondary break-all">{setupData.webhooks[p.key]}</code>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* EVENTS */}
      {tab === 'events' && (
        <div className="space-y-3">
          {(!eventsData?.events?.length) ? (
            <div className="text-center py-20 text-secondary">
              <ShoppingCart className="w-12 h-12 mx-auto mb-4 opacity-30" />
              <p className="text-sm">Nenhum evento recebido ainda.</p>
              <p className="text-xs mt-1">Configure os webhooks na aba "Configuração".</p>
            </div>
          ) : eventsData.events.map((e: any) => {
            const meta = eventLabels[e.event_type] || eventLabels.unknown;
            return (
              <div key={e.id} className="bg-bg-surface border border-border rounded-xl p-4 flex items-center gap-4">
                <span className="text-lg">{meta.emoji}</span>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className={`text-sm font-bold ${meta.color}`}>{meta.label}</span>
                    <span className="text-[10px] text-secondary bg-bg-sidebar px-2 py-0.5 rounded">{e.platform}</span>
                  </div>
                  <div className="text-xs text-secondary truncate">
                    {e.buyer_name} • {e.product_name} • R${e.value}
                  </div>
                </div>
                <div className="text-right text-[10px] text-secondary">
                  {e.received_at && new Date(e.received_at).toLocaleDateString('pt-BR')}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* STATS */}
      {tab === 'stats' && statsData && (
        <div className="space-y-6">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="bg-bg-surface border border-border rounded-2xl p-5">
              <div className="text-xs text-secondary mb-1">Total Eventos</div>
              <div className="text-2xl font-bold text-primary">{statsData.total_events}</div>
            </div>
            <div className="bg-bg-surface border border-border rounded-2xl p-5">
              <div className="text-xs text-secondary mb-1">Receita Total</div>
              <div className="text-2xl font-bold text-emerald-400">R${statsData.total_revenue.toLocaleString()}</div>
            </div>
            {Object.entries(statsData.by_event).map(([k, v]) => {
              const meta = eventLabels[k] || eventLabels.unknown;
              return (
                <div key={k} className="bg-bg-surface border border-border rounded-2xl p-5">
                  <div className="text-xs text-secondary mb-1">{meta.emoji} {meta.label}</div>
                  <div className="text-2xl font-bold text-primary">{v as number}</div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
