import { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { CheckCircle2, Clock, CreditCard, MessageCircle, Save } from 'lucide-react';
import { settingsApi } from '../../api/settings';
import { toast } from '../../lib/toast';

export default function Recovery() {
  const queryClient = useQueryClient();
  const [cadenceInput, setCadenceInput] = useState('');

  const { data: settings, isLoading } = useQuery({
    queryKey: ['saas-settings'],
    queryFn: settingsApi.get,
    retry: false,
  });

  useEffect(() => {
    if (settings) setCadenceInput(settings.cadence_str);
  }, [settings]);

  const updateMutation = useMutation({
    mutationFn: settingsApi.updateRecovery,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['saas-settings'] });
      toast.success('Cadência de recuperação atualizada.');
    },
    onError: (err: Error) => toast.error(`Falha: ${err.message}`),
  });

  if (isLoading) {
    return <div className="px-8 py-12 text-sibila-smoke text-sm animate-pulse-soft">Lendo configurações…</div>;
  }

  return (
    <div className="px-8 py-8 max-w-4xl mx-auto">
      <div className="mb-6">
        <h2 className="font-display text-2xl text-sibila-moonlight">Recuperação</h2>
        <p className="text-sm text-sibila-smoke mt-1">
          Cadência de reengajamento + status WhatsApp e billing.
        </p>
      </div>

      <div className="space-y-4">
        {/* Cadência */}
        <section className="bg-sibila-obsidian border border-sibila-mist rounded-xl overflow-hidden shadow-inset-veil">
          <header className="px-5 py-3 border-b border-sibila-mist bg-sibila-veil/40 flex items-center gap-2">
            <Clock className="w-4 h-4 text-sibila-amethyst" />
            <h3 className="font-display text-base text-sibila-moonlight">
              Cadência de Recuperação
            </h3>
          </header>
          <div className="px-5 py-4">
            <p className="text-xs text-sibila-smoke mb-3">
              Intervalos (em minutos) entre tentativas do bot reengajar leads parados.
            </p>
            <div className="flex gap-2">
              <input
                type="text"
                value={cadenceInput}
                onChange={(e) => setCadenceInput(e.target.value)}
                placeholder="5, 60, 180"
                className="flex-1 bg-sibila-onyx border border-sibila-mist rounded px-3 py-1.5 text-sm text-sibila-moonlight focus:outline-none focus:border-sibila-amethyst"
              />
              <button
                onClick={() => updateMutation.mutate(cadenceInput)}
                disabled={updateMutation.isPending}
                className="flex items-center gap-1.5 bg-sibila-amethyst text-white px-4 py-1.5 rounded text-sm hover:brightness-110 disabled:opacity-50"
              >
                <Save className="w-3.5 h-3.5" />
                {updateMutation.isPending ? 'Salvando…' : 'Salvar'}
              </button>
            </div>
            <p className="text-[10px] text-sibila-smoke mt-2">
              Ex.: <span className="font-mono text-sibila-fog">5, 60, 180</span> = bot tenta após 5min, 1h, 3h.
            </p>
          </div>
        </section>

        {/* WhatsApp */}
        <section className="bg-sibila-obsidian border border-sibila-mist rounded-xl overflow-hidden shadow-inset-veil">
          <header className="px-5 py-3 border-b border-sibila-mist bg-sibila-veil/40 flex items-center gap-2">
            <MessageCircle className="w-4 h-4 text-sibila-sage" />
            <h3 className="font-display text-base text-sibila-moonlight">
              Conexão WhatsApp
            </h3>
          </header>
          <div className="px-5 py-4 flex items-center justify-between">
            <div>
              <p className="text-xs text-sibila-smoke mb-1">Status da API Cloud</p>
              {settings?.whatsapp_configured ? (
                <div className="flex items-center gap-1.5 text-sibila-sage text-sm">
                  <CheckCircle2 className="w-4 h-4" />
                  Conectado e operacional
                </div>
              ) : (
                <div className="text-sibila-ember text-sm">
                  Aguardando configuração — vá pra <a href="/builder/settings/devices" className="text-sibila-amethyst hover:underline">Dispositivos</a>
                </div>
              )}
            </div>
            {settings?.whatsapp_configured && (
              <div className="text-right text-[10px] text-sibila-smoke font-mono">
                <div>Phone ID: {settings.whatsapp_phone_id}</div>
                <div>WABA ID: {settings.whatsapp_waba_id}</div>
              </div>
            )}
          </div>
        </section>

        {/* Billing */}
        <section className="bg-sibila-obsidian border border-sibila-mist rounded-xl overflow-hidden shadow-inset-veil">
          <header className="px-5 py-3 border-b border-sibila-mist bg-sibila-veil/40 flex items-center gap-2">
            <CreditCard className="w-4 h-4 text-sibila-amethyst" />
            <h3 className="font-display text-base text-sibila-moonlight">
              Assinatura e Pagamentos
            </h3>
          </header>
          <div className="px-5 py-4 space-y-3 text-sm">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-sibila-moonlight">Status da Assinatura SaaS</div>
                <div className="text-[11px] text-sibila-smoke">
                  Sua assinatura ativa da plataforma
                </div>
              </div>
              <span className="text-[10px] uppercase tracking-wider px-2 py-0.5 rounded bg-sibila-veil text-sibila-fog">
                {settings?.subscription_status || 'N/A'}
              </span>
            </div>
            <div className="flex items-center justify-between border-t border-sibila-mist pt-3">
              <div>
                <div className="text-sibila-moonlight">Stripe Connect</div>
                <div className="text-[11px] text-sibila-smoke">
                  Recebimentos automáticos
                </div>
              </div>
              <span className="text-[10px] uppercase tracking-wider px-2 py-0.5 rounded bg-sibila-veil">
                {settings?.connect_payouts ? (
                  <span className="text-sibila-sage">Ativo</span>
                ) : (
                  <span className="text-sibila-ember">Pendente</span>
                )}
              </span>
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}
