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

export default function Integrations() {
  const { data, isLoading, error } = useQuery({
    queryKey: ['integrations-summary'],
    queryFn: integrationsApi.summary,
    refetchInterval: 30000,
  });

  if (isLoading) {
    return (
      <div className="p-8 text-slate-400">Carregando integrações…</div>
    );
  }
  if (error || !data) {
    return (
      <div className="p-8">
        <div className="bg-red-500/10 border border-red-500/30 text-red-400 p-4 rounded-xl">
          Falha ao carregar: {(error as Error)?.message ?? '—'}
        </div>
      </div>
    );
  }

  const copy = (text: string) => {
    navigator.clipboard.writeText(text).then(
      () => toast.success('Copiado.'),
      () => toast.error('Falha ao copiar.'),
    );
  };

  return (
    <div className="p-8 max-w-5xl mx-auto text-slate-100 space-y-6">
      <div>
        <h2 className="text-2xl font-bold font-display">Integrações</h2>
        <p className="text-sm text-slate-400 mt-1">
          Webhooks expostos, configuração da Meta WhatsApp Cloud API e estado da
          fila Redis.
        </p>
      </div>

      {/* Webhooks */}
      <section className="bg-cigana-surface border border-cigana-border rounded-xl overflow-hidden">
        <header className="px-5 py-3 border-b border-cigana-border bg-slate-800/20 flex items-center gap-2">
          <Webhook className="w-4 h-4 text-cigana-purple" />
          <h3 className="font-bold text-sm">Webhooks expostos</h3>
        </header>
        <ul className="divide-y divide-cigana-border/50">
          {data.webhooks.map((w) => {
            const url = `${data.base_url}${w.path}`;
            return (
              <li key={w.id} className="px-5 py-3">
                <div className="flex items-center justify-between gap-3">
                  <div className="min-w-0">
                    <div className="font-medium text-slate-200">{w.label}</div>
                    <div className="text-xs text-slate-500 mt-0.5">{w.hint}</div>
                  </div>
                  <button
                    onClick={() => copy(url)}
                    className="text-xs px-2 py-1 rounded border border-cigana-border hover:border-cigana-purple flex items-center gap-1 flex-shrink-0"
                    title="Copiar URL completa"
                  >
                    <Copy className="w-3 h-3" />
                    copiar URL
                  </button>
                </div>
                <code className="block mt-2 text-[11px] text-sky-300 bg-cigana-bg/60 rounded px-2 py-1 font-mono break-all">
                  {url}
                </code>
              </li>
            );
          })}
        </ul>
      </section>

      {/* Meta Cloud API */}
      <section className="bg-cigana-surface border border-cigana-border rounded-xl overflow-hidden">
        <header className="px-5 py-3 border-b border-cigana-border bg-slate-800/20">
          <h3 className="font-bold text-sm">Meta WhatsApp Cloud API</h3>
        </header>
        <ul className="divide-y divide-cigana-border/50 text-sm">
          <ConfigRow label="WABA ID" ok={data.meta.waba_configured} />
          <ConfigRow label="Phone number ID" ok={data.meta.phone_number_configured} />
          <ConfigRow label="Token de acesso" ok={data.meta.token_configured} />
          <ConfigRow label="Verify token (webhook)" ok={data.meta.verify_token_configured} />
        </ul>
        {data.docs.whatsapp_cloud && (
          <div className="px-5 py-2 border-t border-cigana-border bg-cigana-bg/30">
            <a
              href={data.docs.whatsapp_cloud}
              target="_blank"
              rel="noreferrer"
              className="text-xs text-sky-400 hover:underline flex items-center gap-1"
            >
              <ExternalLink className="w-3 h-3" />
              Documentação WhatsApp Cloud API
            </a>
          </div>
        )}
      </section>

      {/* Redis inbound */}
      <section className="bg-cigana-surface border border-cigana-border rounded-xl overflow-hidden">
        <header className="px-5 py-3 border-b border-cigana-border bg-slate-800/20 flex items-center gap-2">
          <Database className="w-4 h-4 text-rose-400" />
          <h3 className="font-bold text-sm">Fila durável (Redis inbound)</h3>
        </header>
        <div className="px-5 py-4 space-y-2 text-sm">
          {!data.redis_inbound.configured ? (
            <div className="text-xs text-amber-300 flex items-start gap-2">
              <AlertCircle className="w-3.5 h-3.5 mt-0.5 flex-shrink-0" />
              <span>
                <strong>REDIS_URL</strong> não está setada — a fila roda
                in-process (mensagens podem ser perdidas em restart). Configure
                pra produção.
              </span>
            </div>
          ) : (
            <>
              <div className="flex items-center gap-2 text-emerald-300 text-xs">
                <CheckCircle2 className="w-3.5 h-3.5" />
                <span>
                  Configurado e {data.redis_inbound.ready ? 'pronto' : 'inicializando…'}
                </span>
              </div>
              {data.redis_inbound.queue_key && (
                <div className="text-xs text-slate-400 font-mono">
                  queue_key:{' '}
                  <span className="text-slate-300">
                    {data.redis_inbound.queue_key}
                  </span>
                </div>
              )}
              {data.redis_inbound.depth != null && (
                <div className="text-xs text-slate-400">
                  Profundidade da fila:{' '}
                  <span className="text-slate-300 font-mono">
                    {data.redis_inbound.depth}
                  </span>
                </div>
              )}
            </>
          )}
        </div>
      </section>

      {/* Telas Jinja não migradas — atalhos */}
      <section className="bg-cigana-surface border border-cigana-border rounded-xl p-5">
        <h3 className="font-bold text-sm mb-3">Outras telas (Jinja)</h3>
        <p className="text-xs text-slate-500 mb-3">
          Estas telas ainda usam os templates Flask. Migração pra React vem nas
          próximas sprints.
        </p>
        <div className="flex flex-wrap gap-2">
          <a
            href="/saas/onboarding"
            className="text-xs px-3 py-1.5 rounded border border-cigana-border hover:border-cigana-purple flex items-center gap-1"
          >
            <ExternalLink className="w-3 h-3" />
            Onboarding
          </a>
          <a
            href="/saas/billing"
            className="text-xs px-3 py-1.5 rounded border border-cigana-border hover:border-cigana-purple flex items-center gap-1"
          >
            <ExternalLink className="w-3 h-3" />
            Billing / Planos
          </a>
          <a
            href="/saas/connect/status"
            className="text-xs px-3 py-1.5 rounded border border-cigana-border hover:border-cigana-purple flex items-center gap-1"
          >
            <ExternalLink className="w-3 h-3" />
            Status WhatsApp Embedded
          </a>
        </div>
      </section>
    </div>
  );
}

function ConfigRow({ label, ok }: { label: string; ok: boolean }) {
  return (
    <li className="px-5 py-2.5 flex items-center justify-between">
      <span className="text-slate-300">{label}</span>
      {ok ? (
        <span className="flex items-center gap-1 text-xs text-emerald-300">
          <CheckCircle2 className="w-3.5 h-3.5" />
          configurado
        </span>
      ) : (
        <span className="flex items-center gap-1 text-xs text-amber-300">
          <AlertCircle className="w-3.5 h-3.5" />
          pendente
        </span>
      )}
    </li>
  );
}
