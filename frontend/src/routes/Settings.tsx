import { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { settingsApi } from '../api/settings';
import { toast } from '../lib/toast';
import { MessageCircle, Clock, CreditCard, Save, CheckCircle2 } from 'lucide-react';

export default function Settings() {
  const queryClient = useQueryClient();
  const [cadenceInput, setCadenceInput] = useState('');

  const { data: settings, isLoading } = useQuery({
    queryKey: ['saas-settings'],
    queryFn: settingsApi.get,
  });

  useEffect(() => {
    if (settings) {
      setCadenceInput(settings.cadence_str);
    }
  }, [settings]);

  const updateMutation = useMutation({
    mutationFn: settingsApi.updateRecovery,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['saas-settings'] });
      toast.success('Cadência de recuperação atualizada.');
    },
    onError: (err: Error) => {
      toast.error(`Falha ao salvar: ${err.message}`);
    },
  });

  if (isLoading) {
    return <div className="p-8 text-sibila-fog">Carregando configurações...</div>;
  }

  return (
    <div className="p-8 max-w-4xl mx-auto text-sibila-moonlight">
      <h2 className="text-2xl font-bold mb-8 font-display">Configurações SaaS</h2>

      <div className="space-y-6">
        {/* Cadence Card */}
        <div className="bg-sibila-obsidian border border-sibila-mist rounded-xl overflow-hidden shadow-sm">
          <div className="px-6 py-4 border-b border-sibila-mist bg-sibila-veil/40 flex items-center gap-3">
            <Clock className="w-5 h-5 text-sibila-amethyst" />
            <h3 className="font-bold text-lg">Cadência de Recuperação</h3>
          </div>
          <div className="p-6">
            <p className="text-sm text-sibila-fog mb-4">
              Defina os intervalos (em minutos) para o bot tentar reengajar os leads pausados ou aguardando resposta.
            </p>
            <div className="flex items-center gap-3">
              <input
                type="text"
                value={cadenceInput}
                onChange={(e) => setCadenceInput(e.target.value)}
                placeholder="Ex: 5, 60, 180"
                className="flex-1 bg-sibila-onyx border border-sibila-stone rounded-lg px-4 py-2.5 text-sm text-sibila-moonlight outline-none focus:border-sibila-amethyst transition-colors"
              />
              <button
                onClick={() => updateMutation.mutate(cadenceInput)}
                disabled={updateMutation.isPending}
                className="flex items-center gap-2 bg-sibila-amethyst hover:bg-sibila-amethyst/80 text-white px-5 py-2.5 rounded-lg text-sm font-semibold transition-colors disabled:opacity-50"
              >
                <Save className="w-4 h-4" />
                {updateMutation.isPending ? 'Salvando...' : 'Salvar'}
              </button>
            </div>
            <div className="text-xs text-sibila-smoke mt-2 flex items-center gap-1">
              Exemplo: 5, 60, 180 significa que o bot chamará após 5 minutos, depois 1 hora, depois 3 horas.
            </div>
          </div>
        </div>

        {/* WhatsApp Card */}
        <div className="bg-sibila-obsidian border border-sibila-mist rounded-xl overflow-hidden shadow-sm">
          <div className="px-6 py-4 border-b border-sibila-mist bg-sibila-veil/40 flex items-center gap-3">
            <MessageCircle className="w-5 h-5 text-emerald-400" />
            <h3 className="font-bold text-lg">Conexão WhatsApp</h3>
          </div>
          <div className="p-6 flex items-center justify-between">
            <div>
              <p className="text-sm text-sibila-fog mb-1">Status da API Oficial Cloud</p>
              {settings?.whatsapp_configured ? (
                <div className="flex items-center gap-2 text-emerald-400 text-sm font-semibold">
                  <CheckCircle2 className="w-4 h-4" />
                  Conectado e Operacional
                </div>
              ) : (
                <div className="text-amber-400 text-sm font-semibold">Aguardando configuração no Onboarding</div>
              )}
            </div>
            {settings?.whatsapp_configured && (
              <div className="text-right text-xs text-sibila-smoke font-mono">
                <div>Phone ID: {settings.whatsapp_phone_id}</div>
                <div>WABA ID: {settings.whatsapp_waba_id}</div>
              </div>
            )}
          </div>
        </div>

        {/* Billing/Stripe Card */}
        <div className="bg-sibila-obsidian border border-sibila-mist rounded-xl overflow-hidden shadow-sm">
          <div className="px-6 py-4 border-b border-sibila-mist bg-sibila-veil/40 flex items-center gap-3">
            <CreditCard className="w-5 h-5 text-sky-400" />
            <h3 className="font-bold text-lg">Assinatura e Pagamentos</h3>
          </div>
          <div className="p-6 flex flex-col gap-4">
            <div className="flex justify-between items-center border-b border-sibila-mist pb-4">
              <div>
                <div className="text-sm text-sibila-moonlight font-semibold">Status da Assinatura SaaS</div>
                <div className="text-xs text-sibila-fog">Sua assinatura ativa da plataforma</div>
              </div>
              <div className="uppercase tracking-widest text-xs font-bold bg-sibila-veil px-3 py-1 rounded text-sibila-fog">
                {settings?.subscription_status || 'N/A'}
              </div>
            </div>
            
            <div className="flex justify-between items-center">
              <div>
                <div className="text-sm text-sibila-moonlight font-semibold">Recebimentos (Stripe Connect)</div>
                <div className="text-xs text-sibila-fog">Habilitado para receber vendas automáticas</div>
              </div>
              <div className="uppercase tracking-widest text-xs font-bold bg-sibila-veil px-3 py-1 rounded text-sibila-fog">
                {settings?.connect_payouts ? (
                  <span className="text-emerald-400">Ativo</span>
                ) : (
                  <span className="text-amber-400">Pendente</span>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
