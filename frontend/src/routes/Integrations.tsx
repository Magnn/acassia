import { useQuery } from '@tanstack/react-query';
import {
  AlertCircle,
  CheckCircle2,
  Copy,
  Database,
  ExternalLink,
  Webhook,
} from 'lucide-react';
import { integrationsApi } from '../api/integrations';
import { toast } from '../lib/toast';
import WhatsAppConnect from '../components/WhatsAppConnect';

export default function Integrations() {
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
        <h2 className="text-3xl font-black tracking-tight">Integrações</h2>
        <p className="text-sm text-secondary mt-2 max-w-2xl leading-relaxed">
          Gerencie os canais de entrada e saída. Webhooks expostos, configuração da Meta WhatsApp Cloud API e estado da infraestrutura de mensageria.
        </p>
      </div>

      <div className="grid gap-6">
        {/* WhatsApp Cloud API — onboarding por tenant */}
        <section className="bg-bg-surface border border-border rounded-3xl shadow-sm overflow-hidden">
          <header className="px-6 py-4 border-b border-border bg-bg-primary/20">
            <h3 className="font-black text-sm uppercase tracking-widest">Conectar WhatsApp</h3>
          </header>
          <div className="px-6 py-6">
            <WhatsAppConnect />
          </div>
        </section>

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
