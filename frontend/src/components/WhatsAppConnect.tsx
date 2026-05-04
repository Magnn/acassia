import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  CheckCircle2, XCircle, Webhook, Copy, RefreshCw, Trash2,
  Phone, KeyRound, Shield, AlertTriangle, ExternalLink, Eye, EyeOff,
  Send, Activity, Inbox,
} from 'lucide-react';
import { integrationsApi } from '../api/integrations';
import { handleApiError } from '../lib/handleApiError';
import { toast } from '../lib/toast';

export default function WhatsAppConnect() {
  const qc = useQueryClient();
  const { data, isLoading } = useQuery({
    queryKey: ['integrations-whatsapp'],
    queryFn: integrationsApi.whatsapp.status,
  });

  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState({
    access_token: '',
    phone_number_id: '',
    waba_id: '',
    app_secret: '',
    verify_token: '',
    skip_validation: false,
  });
  const [showSecret, setShowSecret] = useState(false);
  const [testResult, setTestResult] = useState<{ ok: boolean; message: string } | null>(null);
  const [lastSaved, setLastSaved] = useState<{
    verify_token: string; webhook_url: string; instructions: string[];
  } | null>(null);

  const testMut = useMutation({
    mutationFn: () => integrationsApi.whatsapp.test({
      access_token: draft.access_token.trim(),
      phone_number_id: draft.phone_number_id.trim(),
    }),
    onSuccess: (res) => {
      if (res.ok) {
        setTestResult({
          ok: true,
          message: `OK — ${res.display_phone_number || ''} (${res.verified_name || 'sem nome'})`,
        });
      } else {
        const err = (res.error as { message?: string } | undefined)?.message || 'desconhecido';
        setTestResult({ ok: false, message: `Falhou: ${err}` });
      }
    },
    onError: handleApiError('Erro ao testar credenciais'),
  });

  const saveMut = useMutation({
    mutationFn: () => integrationsApi.whatsapp.save({
      access_token: draft.access_token.trim(),
      phone_number_id: draft.phone_number_id.trim(),
      waba_id: draft.waba_id.trim() || undefined,
      app_secret: draft.app_secret.trim() || undefined,
      verify_token: draft.verify_token.trim() || undefined,
      skip_validation: draft.skip_validation,
    }),
    onSuccess: (res) => {
      toast.success('WhatsApp conectado');
      setLastSaved({
        verify_token: res.verify_token,
        webhook_url: res.webhook_url,
        instructions: res.instructions,
      });
      setEditing(false);
      qc.invalidateQueries({ queryKey: ['integrations-whatsapp'] });
    },
    onError: handleApiError('Erro ao salvar'),
  });

  const removeMut = useMutation({
    mutationFn: () => integrationsApi.whatsapp.remove(),
    onSuccess: () => {
      toast.success('Conexão removida');
      setLastSaved(null);
      qc.invalidateQueries({ queryKey: ['integrations-whatsapp'] });
    },
    onError: handleApiError('Erro ao remover'),
  });

  const rotateMut = useMutation({
    mutationFn: () => integrationsApi.whatsapp.rotateVerifyToken(),
    onSuccess: (res) => {
      toast.success('Verify token rotacionado — atualize na Meta');
      setLastSaved({
        verify_token: res.verify_token,
        webhook_url: res.webhook_url,
        instructions: ['Atualize o verify_token no painel da Meta antes que ele expire.'],
      });
      qc.invalidateQueries({ queryKey: ['integrations-whatsapp'] });
    },
    onError: handleApiError('Erro ao rotacionar'),
  });

  const subscribeMut = useMutation({
    mutationFn: () => integrationsApi.whatsapp.subscribe(),
    onSuccess: (res) => {
      if (res.ok) {
        toast.success('App subscrita ao WABA');
      } else {
        const err = res.binding?.subscribe_error || 'Falhou — verifique permissões na Meta';
        toast.error(err);
      }
      qc.invalidateQueries({ queryKey: ['integrations-whatsapp'] });
    },
    onError: handleApiError('Erro ao subscrever'),
  });

  const rotatePathMut = useMutation({
    mutationFn: () => integrationsApi.whatsapp.rotateWebhookPath(),
    onSuccess: (res) => {
      toast.success('URL rotacionada — atualize na Meta');
      setLastSaved({
        verify_token: binding?.has_verify_token ? '(token mantido)' : '',
        webhook_url: res.webhook_url,
        instructions: [
          'A URL antiga foi invalidada — substitua pela nova no painel da Meta.',
          'A URL global /webhook continua aceitando msgs até você atualizar.',
        ],
      });
      qc.invalidateQueries({ queryKey: ['integrations-whatsapp'] });
    },
    onError: handleApiError('Erro ao rotacionar'),
  });

  const copy = (text: string, label = 'Copiado') => {
    navigator.clipboard.writeText(text);
    toast.success(label);
  };

  if (isLoading) {
    return <div className="text-secondary text-sm py-6">Carregando…</div>;
  }

  const binding = data?.binding;
  const validDraft =
    draft.access_token.trim().length > 20 &&
    draft.phone_number_id.trim().length >= 6;

  return (
    <div className="space-y-5">
      <header className="flex items-start justify-between gap-4 border-b border-sibila-mist/50 pb-5">
        <div>
          <h3 className="text-3xl font-display text-sibila-moonlight tracking-tight flex items-center gap-3">
            <Phone className="w-8 h-8 text-sibila-amethyst" />
            WhatsApp Cloud API
          </h3>
          <p className="text-sm text-sibila-smoke mt-2 leading-relaxed max-w-2xl">
            Conecte seu número oficial Meta WhatsApp Business. O fluxo de credenciais é encriptado 
            e gerido individualmente por Workspace *(Tenant)*.
          </p>
        </div>
        {binding && !editing && (
          <button
            onClick={() => {
              if (confirm('Deseja realmente remover a conexão? Suas automações pararão de funcionar imediatamente.')) {
                removeMut.mutate();
              }
            }}
            className="px-4 py-2 bg-sibila-rose/10 border border-sibila-rose/30 text-sibila-rose hover:bg-sibila-rose hover:text-white rounded-xl text-xs font-bold transition-all flex items-center gap-2 shadow-sm"
          >
            <Trash2 className="w-4 h-4" />
            Remover Conexão
          </button>
        )}
      </header>

      {!editing && binding ? (
        <>
          <BindingView
            binding={binding}
            webhookUrl={data!.webhook_url}
            webhookUrlGlobal={data!.webhook_url_global}
            onEdit={() => setEditing(true)}
            onCopy={copy}
            onRotate={() => rotateMut.mutate()}
            rotating={rotateMut.isPending}
            onSubscribe={() => subscribeMut.mutate()}
            subscribing={subscribeMut.isPending}
            onRotatePath={() => rotatePathMut.mutate()}
            rotatingPath={rotatePathMut.isPending}
          />
          <InboundTelemetry binding={binding} />
          <ObservabilityPanel />
          <TestSendForm />
        </>
      ) : !editing && !binding ? (
        <EmptyState onStart={() => setEditing(true)} webhookUrl={data!.webhook_url} />
      ) : (
        <EditForm
          draft={draft}
          setDraft={setDraft}
          showSecret={showSecret}
          setShowSecret={setShowSecret}
          testResult={testResult}
          onTest={() => testMut.mutate()}
          testing={testMut.isPending}
          onSave={() => saveMut.mutate()}
          saving={saveMut.isPending}
          onCancel={() => {
            setEditing(false);
            setTestResult(null);
          }}
          validDraft={validDraft}
          isUpdate={!!binding}
        />
      )}

      {lastSaved && (
        <SetupInstructions data={lastSaved} onCopy={copy} />
      )}
    </div>
  );
}

function EmptyState({ onStart, webhookUrl }: { onStart: () => void; webhookUrl: string }) {
  return (
    <div className="bg-gradient-to-br from-sibila-obsidian/40 to-sibila-veil/20 border border-dashed border-sibila-mist/60 rounded-2xl p-10 text-center space-y-5 relative overflow-hidden group">
      <div className="absolute inset-0 bg-sibila-amethyst/5 opacity-0 group-hover:opacity-100 transition-opacity" />
      <div className="relative z-10 w-20 h-20 mx-auto rounded-full bg-sibila-veil border border-sibila-mist flex items-center justify-center shadow-lg group-hover:scale-110 transition-transform duration-500">
        <Webhook className="w-10 h-10 text-sibila-amethyst" strokeWidth={1.5} />
      </div>
      <div className="relative z-10">
        <div className="text-xl font-display text-sibila-moonlight mb-2">Nenhum número conectado</div>
        <p className="text-sm text-sibila-fog max-w-md mx-auto leading-relaxed">
          Você precisa de um App aprovado no Meta Business e um número de telefone da API Nuvem
          com um Token de Usuário de Sistema Permanente.
        </p>
      </div>
      <div className="relative z-10 inline-flex flex-col items-center gap-2 bg-sibila-veil/50 border border-sibila-mist/50 px-6 py-4 rounded-xl shadow-inner mt-4">
        <span className="text-[10px] uppercase tracking-widest text-sibila-smoke font-bold">Webhook URL Gerada:</span>
        <code className="text-xs font-mono text-sibila-moonlight bg-sibila-obsidian/50 px-3 py-1.5 rounded-lg border border-sibila-mist/30">
          {webhookUrl}
        </code>
      </div>
      <div className="relative z-10 pt-4 flex flex-col items-center gap-4">
        <button
          onClick={onStart}
          className="px-8 py-3 bg-gradient-to-r from-sibila-amethyst to-[#9d89c4] hover:brightness-110 text-white rounded-xl text-sm font-bold uppercase tracking-widest shadow-[0_0_20px_rgba(124,106,153,0.3)] transition-all transform hover:scale-[1.02] active:scale-[0.98]"
        >
          Iniciar Conexão Meta
        </button>
        <a
          href="https://developers.facebook.com/docs/whatsapp/cloud-api/get-started"
          target="_blank"
          rel="noreferrer"
          className="inline-flex items-center gap-1.5 text-xs text-sibila-amethyst hover:text-sibila-moonlight hover:underline transition-colors font-medium"
        >
          <ExternalLink className="w-3.5 h-3.5" />
          Ler Documentação Oficial da Meta
        </a>
      </div>
    </div>
  );
}

function BindingView({
  binding, webhookUrl, webhookUrlGlobal, onEdit, onCopy, onRotate, rotating,
  onSubscribe, subscribing, onRotatePath, rotatingPath,
}: {
  binding: import('../api/integrations').WaBinding;
  webhookUrl: string;
  webhookUrlGlobal?: string;
  onEdit: () => void;
  onCopy: (text: string, label?: string) => void;
  onRotate: () => void;
  rotating: boolean;
  onSubscribe: () => void;
  subscribing: boolean;
  onRotatePath: () => void;
  rotatingPath: boolean;
}) {
  const statusColor = {
    active: 'text-emerald-400 bg-emerald-500/10 border-emerald-500/30 shadow-[0_0_15px_rgba(16,185,129,0.15)]',
    pending: 'text-amber-400 bg-amber-500/10 border-amber-500/30 shadow-[0_0_15px_rgba(245,158,11,0.15)]',
    failed: 'text-rose-400 bg-rose-500/10 border-rose-500/30 shadow-[0_0_15px_rgba(225,29,72,0.15)]',
  }[binding.status] || 'text-sibila-fog bg-sibila-veil border-sibila-mist';

  return (
    <div className="bg-sibila-obsidian/40 border border-sibila-mist/50 rounded-2xl p-6 space-y-4 shadow-inset-veil backdrop-blur-sm">
      <div className="flex items-center justify-between pb-3 border-b border-sibila-mist/30">
        <div className="flex items-center gap-3">
          {binding.status === 'active' ? (
            <div className="w-8 h-8 rounded-full bg-emerald-500/10 flex items-center justify-center">
              <CheckCircle2 className="w-5 h-5 text-emerald-400" />
            </div>
          ) : (
            <div className="w-8 h-8 rounded-full bg-amber-500/10 flex items-center justify-center animate-pulse">
              <AlertTriangle className="w-5 h-5 text-amber-400" />
            </div>
          )}
          <span className="font-display text-2xl text-sibila-moonlight tracking-tight">
            {binding.display_phone_number || binding.phone_number_id}
          </span>
        </div>
        <span className={`text-[10px] font-black uppercase tracking-widest px-3 py-1 rounded-md border ${statusColor}`}>
          {binding.status}
        </span>
      </div>

      <Row label="Phone Number ID" value={binding.phone_number_id} onCopy={onCopy} mono />
      {binding.waba_id && (
        <Row label="WABA ID" value={binding.waba_id} onCopy={onCopy} mono />
      )}
      <Row
        label={binding.webhook_path ? 'Webhook URL (per-tenant)' : 'Webhook URL'}
        value={webhookUrl}
        onCopy={onCopy}
        mono
      />
      {binding.webhook_path && webhookUrlGlobal && webhookUrlGlobal !== webhookUrl && (
        <Row label="Webhook URL global (fallback)" value={webhookUrlGlobal} onCopy={onCopy} mono />
      )}

      <div className="grid grid-cols-2 gap-4 text-xs pt-2">
        <div className="bg-sibila-veil/30 p-3 rounded-xl border border-sibila-mist/30">
          <span className="text-[10px] uppercase tracking-widest text-sibila-smoke block mb-1 font-bold">Verify Token</span>
          <span className="text-sibila-moonlight font-medium">{binding.has_verify_token ? '✓ Definido no Tenant' : '— Global .env'}</span>
        </div>
        <div className="bg-sibila-veil/30 p-3 rounded-xl border border-sibila-mist/30">
          <span className="text-[10px] uppercase tracking-widest text-sibila-smoke block mb-1 font-bold">App Secret</span>
          <span className="text-sibila-moonlight font-medium">{binding.has_app_secret ? '✓ Definido no Tenant' : '— Global .env'}</span>
        </div>
      </div>

      {binding.last_verified_at && (
        <div className="text-[11px] text-sibila-smoke flex items-center gap-1.5">
          <Shield className="w-3.5 h-3.5" />
          Última validação da Graph API: {new Date(binding.last_verified_at).toLocaleString('pt-BR')}
        </div>
      )}
      {binding.last_error && (
        <div className="text-[11px] text-rose-400 bg-rose-500/10 border border-rose-500/30 rounded-xl p-3 shadow-inner">
          <strong>Erro na última verificação:</strong> {binding.last_error}
        </div>
      )}

      <div className="bg-sibila-veil/50 border border-sibila-mist rounded-xl p-4 text-[11px] shadow-inner">
        <div className="flex items-center gap-3">
          {binding.subscribed_at ? (
            <>
              <div className="w-6 h-6 rounded-full bg-emerald-500/20 flex items-center justify-center">
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
              </div>
              <span className="text-emerald-400 font-bold text-sm tracking-wide">Webhooks Subscritos no WABA</span>
              <span className="text-sibila-smoke text-[10px] ml-auto font-medium">
                {new Date(binding.subscribed_at).toLocaleString('pt-BR')}
              </span>
            </>
          ) : (
            <>
              <div className="w-6 h-6 rounded-full bg-amber-500/20 flex items-center justify-center animate-pulse">
                <AlertTriangle className="w-3.5 h-3.5 text-amber-400" />
              </div>
              <span className="text-amber-400 font-bold text-sm tracking-wide">App não subscrita aos Webhooks WABA</span>
              <button
                onClick={onSubscribe}
                disabled={subscribing}
                className="ml-auto text-xs text-sibila-amethyst hover:text-sibila-moonlight hover:underline font-bold flex items-center gap-1.5 transition-colors"
              >
                <RefreshCw className={`w-3 h-3 ${subscribing ? 'animate-spin' : ''}`} />
                {subscribing ? 'Subscrevendo…' : 'Tentar subscrever'}
              </button>
            </>
          )}
        </div>
        {binding.subscribe_error && !binding.subscribed_at && (
          <div className="text-[11px] text-rose-400 mt-2 bg-rose-500/10 p-2 rounded-lg">{binding.subscribe_error}</div>
        )}
      </div>

      <div className="flex flex-wrap gap-3 pt-4 border-t border-sibila-mist/50">
        <button
          onClick={onEdit}
          className="px-4 py-2 bg-sibila-veil/50 hover:bg-sibila-veil border border-sibila-mist hover:border-sibila-amethyst/50 rounded-xl text-xs font-bold text-sibila-moonlight flex items-center gap-2 transition-all shadow-sm"
        >
          <KeyRound className="w-3.5 h-3.5 text-sibila-amethyst" />
          Atualizar Credenciais
        </button>
        <button
          onClick={onRotate}
          disabled={rotating}
          className="px-4 py-2 bg-sibila-veil/50 hover:bg-sibila-veil border border-sibila-mist hover:border-sibila-amethyst/50 rounded-xl text-xs font-bold text-sibila-moonlight flex items-center gap-2 transition-all shadow-sm disabled:opacity-50"
        >
          <RefreshCw className={`w-3.5 h-3.5 text-sibila-amethyst ${rotating ? 'animate-spin' : ''}`} />
          Rotacionar Verify Token
        </button>
        {binding.webhook_path && (
          <button
            onClick={onRotatePath}
            disabled={rotatingPath}
            className="px-4 py-2 bg-sibila-veil/50 hover:bg-sibila-veil border border-sibila-mist hover:border-sibila-amethyst/50 rounded-xl text-xs font-bold text-sibila-moonlight flex items-center gap-2 transition-all shadow-sm disabled:opacity-50"
            title="Gera nova URL per-tenant (defesa em profundidade)"
          >
            <RefreshCw className={`w-3.5 h-3.5 text-sibila-amethyst ${rotatingPath ? 'animate-spin' : ''}`} />
            Rotacionar Webhook URL
          </button>
        )}
      </div>
    </div>
  );
}


function InboundTelemetry({
  binding,
}: {
  binding: import('../api/integrations').WaBinding;
}) {
  const hasInbound = (binding.inbound_count || 0) > 0;
  return (
    <div
      className={`rounded-2xl p-6 border shadow-inner transition-colors duration-500 ${
        hasInbound
          ? 'bg-emerald-500/10 border-emerald-500/30'
          : 'bg-amber-500/10 border-amber-500/30'
      }`}
    >
      <div className="flex items-center gap-3 mb-4">
        <div className={`w-8 h-8 rounded-full flex items-center justify-center ${hasInbound ? 'bg-emerald-500/20' : 'bg-amber-500/20'}`}>
          {hasInbound ? (
            <Inbox className="w-4 h-4 text-emerald-400" />
          ) : (
            <Activity className="w-4 h-4 text-amber-400 animate-pulse" />
          )}
        </div>
        <span className={`text-[11px] font-bold uppercase tracking-widest ${hasInbound ? 'text-emerald-400' : 'text-amber-400'}`}>
          {hasInbound ? 'Recebendo Webhooks Ativamente' : 'Aguardando 1ª Mensagem (Teste Necessário)'}
        </span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-[11px]">
        <div className="bg-sibila-obsidian/30 p-3 rounded-xl border border-sibila-mist/30">
          <div className="text-[10px] font-bold uppercase tracking-widest text-sibila-smoke">Total Recebido</div>
          <div className="text-2xl font-black tabular-nums mt-1 text-sibila-moonlight">{binding.inbound_count}</div>
        </div>
        <div className="bg-sibila-obsidian/30 p-3 rounded-xl border border-sibila-mist/30">
          <div className="text-[10px] font-bold uppercase tracking-widest text-sibila-smoke">Primeira Mensagem</div>
          <div className="text-xs font-bold mt-2 text-sibila-moonlight">
            {binding.first_inbound_at
              ? new Date(binding.first_inbound_at).toLocaleString('pt-BR')
              : '—'}
          </div>
        </div>
        <div className="bg-sibila-obsidian/30 p-3 rounded-xl border border-sibila-mist/30">
          <div className="text-[10px] font-bold uppercase tracking-widest text-sibila-smoke">Última Mensagem</div>
          <div className="text-xs font-bold mt-2 text-sibila-moonlight">
            {binding.last_inbound_at
              ? new Date(binding.last_inbound_at).toLocaleString('pt-BR')
              : '—'}
          </div>
        </div>
      </div>

      {!hasInbound && (
        <p className="text-xs text-sibila-fog mt-4 flex items-center gap-2 bg-amber-500/10 p-3 rounded-xl border border-amber-500/20">
          <AlertTriangle className="w-4 h-4 text-amber-400" />
          Envie uma mensagem do seu próprio celular para o número conectado para ativar o webhook. 
          Costuma chegar em 1-2 segundos.
        </p>
      )}
    </div>
  );
}


function ObservabilityPanel() {
  const statsQ = useQuery({
    queryKey: ['wa-inbound-stats'],
    queryFn: integrationsApi.whatsapp.inboundStats,
    refetchInterval: 15_000,
  });
  const logsQ = useQuery({
    queryKey: ['wa-inbound-logs'],
    queryFn: () => integrationsApi.whatsapp.inboundLogs({ limit: 30 }),
    refetchInterval: 30_000,
  });

  const stats = statsQ.data;
  const logs = logsQ.data?.logs ?? [];

  if (!stats) {
    return null;
  }

  const events = stats.events_last_24h || {};
  const errorEvents = ['error', 'rate_limited', 'hmac_invalid', 'tenant_resolve_miss'].filter(
    (k) => (events[k] || 0) > 0,
  );
  const hasErrors = errorEvents.length > 0;

  const eventColor: Record<string, string> = {
    rate_limited: 'text-amber-300',
    hmac_invalid: 'text-rose-400',
    tenant_resolve_miss: 'text-amber-300',
    error: 'text-rose-400',
    first_inbound: 'text-emerald-400',
  };

  return (
    <div className="bg-sibila-obsidian/40 border border-sibila-mist/50 rounded-2xl p-6 space-y-4 shadow-inset-veil backdrop-blur-sm">
      <div className="flex items-center justify-between border-b border-sibila-mist/30 pb-3">
        <h4 className="text-xs font-bold uppercase tracking-widest text-sibila-moonlight flex items-center gap-2">
          <Activity className="w-4 h-4 text-sibila-amethyst" />
          Observabilidade do Webhook
        </h4>
        {hasErrors && (
          <span className="text-[10px] text-amber-400 font-bold flex items-center gap-1.5 px-2 py-1 bg-amber-500/10 rounded-lg border border-amber-500/20">
            <AlertTriangle className="w-3.5 h-3.5" />
            {errorEvents.length} tipo{errorEvents.length === 1 ? '' : 's'} de erro nas últimas 24h
          </span>
        )}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-[11px]">
        <div className="bg-sibila-veil/50 border border-sibila-mist/40 rounded-xl p-4 shadow-inner">
          <div className="text-[10px] font-bold uppercase tracking-widest text-sibila-smoke mb-1">Capacidade / Rate Atual</div>
          <div className="text-xl font-black tabular-nums text-sibila-moonlight">
            {stats.rate_limiter.tokens_remaining}<span className="text-sibila-fog text-sm font-medium">/{stats.rate_limiter.burst_capacity}</span>
          </div>
          <div className="text-[10px] text-sibila-fog mt-1">
            Recarrega a {stats.rate_limiter.rate_per_min}/min
          </div>
        </div>
        <div className="bg-sibila-veil/50 border border-sibila-mist/40 rounded-xl p-4 shadow-inner">
          <div className="text-[10px] font-bold uppercase tracking-widest text-sibila-smoke mb-1">Eventos 24h</div>
          <div className="text-xl font-black tabular-nums text-sibila-moonlight">
            {Object.values(events).reduce((a, b) => a + b, 0)}
          </div>
          <div className="text-[10px] text-sibila-fog mt-1">Requisições processadas</div>
        </div>
        <div className="bg-sibila-veil/50 border border-sibila-mist/40 rounded-xl p-4 shadow-inner">
          <div className="text-[10px] font-bold uppercase tracking-widest text-sibila-smoke mb-1">Total Histórico</div>
          <div className="text-xl font-black tabular-nums text-sibila-moonlight">
            {stats.inbound_count_total}
          </div>
          <div className="text-[10px] text-sibila-fog mt-1">Desde a conexão inicial</div>
        </div>
      </div>

      {hasErrors && (
        <div className="space-y-1.5 bg-rose-500/5 p-3 rounded-xl border border-rose-500/20">
          <div className="text-[10px] uppercase tracking-widest text-rose-400 font-bold mb-2">Erros Detectados</div>
          {errorEvents.map((evt) => (
            <div key={evt} className={`text-xs font-bold flex items-center justify-between bg-sibila-obsidian/50 px-3 py-1.5 rounded-lg border border-sibila-mist/30 ${eventColor[evt] || 'text-sibila-smoke'}`}>
              <span className="uppercase">{evt}</span>
              <span className="tabular-nums px-2 py-0.5 bg-sibila-veil rounded-md">{events[evt]}</span>
            </div>
          ))}
        </div>
      )}

      {logs.length > 0 && (
        <details className="group border border-sibila-mist/30 rounded-xl overflow-hidden bg-sibila-veil/30">
          <summary className="cursor-pointer text-xs text-sibila-moonlight uppercase tracking-widest font-bold list-none flex items-center justify-between p-4 hover:bg-sibila-veil/50 transition-colors">
            <div className="flex items-center gap-2">
              <span className="group-open:rotate-90 transition-transform">▸</span>
              Logs Recentes de Webhook
            </div>
            <span className="text-[10px] text-sibila-smoke bg-sibila-obsidian px-2 py-1 rounded-md">{logs.length} registros</span>
          </summary>
          <div className="px-4 pb-4 space-y-2 max-h-64 overflow-y-auto custom-scrollbar">
            {logs.map((log) => (
              <div
                key={log.id}
                className="bg-sibila-obsidian/50 border border-sibila-mist/30 rounded-lg p-3 text-[11px] flex items-start gap-3 shadow-inner"
              >
                <span className={`font-bold uppercase tracking-widest px-2 py-0.5 rounded-md text-[9px] ${
                  eventColor[log.event_type] ? eventColor[log.event_type].replace('text-', 'bg-').replace('400', '500/20') + ' ' + eventColor[log.event_type] : 'bg-sibila-mist/20 text-sibila-smoke'
                } flex-shrink-0`}>
                  {log.event_type}
                </span>
                <span className="text-sibila-fog font-mono truncate flex-1 leading-relaxed">{log.message || 'Sem descrição'}</span>
                <span className="text-sibila-smoke text-[9px] flex-shrink-0 tabular-nums">
                  {new Date(log.created_at).toLocaleTimeString('pt-BR')}
                </span>
              </div>
            ))}
          </div>
        </details>
      )}
    </div>
  );
}


function TestSendForm() {
  const [to, setTo] = useState('');
  const [body, setBody] = useState('');
  const [result, setResult] = useState<
    { ok: true; message_id: string } | { ok: false; message: string } | null
  >(null);

  const sendMut = useMutation({
    mutationFn: () =>
      integrationsApi.whatsapp.testSend({
        to: to.trim(),
        body: body.trim() || undefined,
      }),
    onSuccess: (res) => {
      if (res.ok && res.message_id) {
        setResult({ ok: true, message_id: res.message_id });
        toast.success('Mensagem enviada — confira o WhatsApp do destinatário');
      } else {
        const msg =
          res.graph_error?.message ||
          (typeof res.error === 'string' ? res.error : 'Erro desconhecido');
        setResult({ ok: false, message: msg });
      }
    },
    onError: handleApiError('Erro ao enviar'),
  });

  const valid = to.trim().replace(/[^0-9]/g, '').length >= 10;

  return (
    <div className="bg-sibila-obsidian/40 border border-sibila-mist/50 rounded-2xl p-6 space-y-4 shadow-inset-veil backdrop-blur-sm">
      <div className="flex items-center gap-2 mb-2 border-b border-sibila-mist/30 pb-3">
        <Send className="w-4 h-4 text-sibila-amethyst" />
        <h4 className="text-xs font-bold uppercase tracking-widest text-sibila-moonlight">
          Enviar mensagem de teste
        </h4>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-[200px_1fr_auto] gap-3">
        <input
          type="tel"
          value={to}
          onChange={(e) => setTo(e.target.value)}
          placeholder="55119xxxxxxxx"
          className="bg-sibila-veil/50 border border-sibila-mist/60 focus:border-sibila-amethyst/50 focus:ring-1 focus:ring-sibila-amethyst/50 rounded-xl px-4 py-2.5 text-xs font-mono text-sibila-moonlight outline-none transition-all shadow-inner"
        />
        <input
          type="text"
          value={body}
          onChange={(e) => setBody(e.target.value)}
          placeholder="Mensagem (deixe vazio pra usar default)"
          className="bg-sibila-veil/50 border border-sibila-mist/60 focus:border-sibila-amethyst/50 focus:ring-1 focus:ring-sibila-amethyst/50 rounded-xl px-4 py-2.5 text-xs text-sibila-moonlight outline-none transition-all shadow-inner"
          maxLength={500}
        />
        <button
          onClick={() => sendMut.mutate()}
          disabled={!valid || sendMut.isPending}
          className="px-6 py-2.5 bg-gradient-to-r from-sibila-amethyst to-[#9d89c4] hover:brightness-110 disabled:opacity-30 disabled:hover:brightness-100 text-white rounded-xl text-[11px] font-black uppercase tracking-widest shadow-[0_0_15px_rgba(124,106,153,0.3)] transition-all transform hover:scale-[1.02] active:scale-[0.98]"
        >
          {sendMut.isPending ? 'Enviando…' : 'Enviar Teste'}
        </button>
      </div>
      <div className="text-[10px] text-sibila-smoke">
        Número em formato E.164 sem o '+'. Exemplo: <code className="bg-sibila-obsidian/50 px-1.5 py-0.5 rounded border border-sibila-mist/30">5511999999999</code>.
        <br />*Custos normais da Meta Cloud API serão aplicados.
      </div>
      {result && (
        <div
          className={`text-[11px] flex items-start gap-1.5 p-3 rounded-xl border ${
            result.ok ? 'text-emerald-400 bg-emerald-500/10 border-emerald-500/30' : 'text-rose-400 bg-rose-500/10 border-rose-500/30'
          }`}
        >
          {result.ok ? (
            <CheckCircle2 className="w-4 h-4 mt-0.5 flex-shrink-0" />
          ) : (
            <XCircle className="w-4 h-4 mt-0.5 flex-shrink-0" />
          )}
          <span className="font-medium">
            {result.ok
              ? `Enviado com sucesso! WAMID: ${result.message_id}`
              : `Erro: ${result.message}`}
          </span>
        </div>
      )}
    </div>
  );
}

function Row({
  label, value, onCopy, mono,
}: {
  label: string;
  value: string;
  onCopy: (t: string, l?: string) => void;
  mono?: boolean;
}) {
  return (
    <div className="flex items-center justify-between gap-3 text-xs border-b border-sibila-mist/20 pb-2 last:border-0 last:pb-0">
      <span className="text-sibila-smoke uppercase tracking-widest text-[10px] font-bold">{label}</span>
      <div className="flex items-center gap-2 min-w-0">
        <code className={`bg-sibila-obsidian/50 border border-sibila-mist/40 px-2 py-1 rounded-md shadow-inner text-sibila-moonlight truncate ${mono ? 'font-mono' : ''}`}>
          {value}
        </code>
        <button
          onClick={() => onCopy(value, `${label} copiado`)}
          className="text-sibila-smoke hover:text-sibila-amethyst transition-colors p-1 bg-sibila-veil/50 hover:bg-sibila-veil rounded-md border border-transparent hover:border-sibila-mist/50 flex-shrink-0"
          title="Copiar para a área de transferência"
        >
          <Copy className="w-3.5 h-3.5" />
        </button>
      </div>
    </div>
  );
}

function EditForm({
  draft, setDraft, showSecret, setShowSecret,
  testResult, onTest, testing,
  onSave, saving, onCancel, validDraft, isUpdate,
}: {
  draft: {
    access_token: string;
    phone_number_id: string;
    waba_id: string;
    app_secret: string;
    verify_token: string;
    skip_validation: boolean;
  };
  setDraft: (d: typeof draft) => void;
  showSecret: boolean;
  setShowSecret: (b: boolean) => void;
  testResult: { ok: boolean; message: string } | null;
  onTest: () => void;
  testing: boolean;
  onSave: () => void;
  saving: boolean;
  onCancel: () => void;
  validDraft: boolean;
  isUpdate: boolean;
}) {
  return (
    <div className="bg-sibila-obsidian/40 border border-sibila-mist/50 rounded-2xl p-6 space-y-5 shadow-inset-veil backdrop-blur-sm relative overflow-hidden">
      {/* Decorative gradient blob */}
      <div className="absolute -top-24 -right-24 w-48 h-48 bg-sibila-amethyst/20 rounded-full blur-3xl pointer-events-none" />

      <Field label="Access Token (System User Permanente)" hint="Acesse o Painel Meta → Business Settings → Users → System Users → Generate Token. Requer as permissões: whatsapp_business_messaging e whatsapp_business_management.">
        <div className="relative group">
          <input
            type={showSecret ? 'text' : 'password'}
            value={draft.access_token}
            onChange={(e) => setDraft({ ...draft, access_token: e.target.value })}
            placeholder="EAAB..."
            className="w-full bg-sibila-veil/50 border border-sibila-mist/60 focus:border-sibila-amethyst/50 focus:ring-1 focus:ring-sibila-amethyst/50 rounded-xl px-4 py-3 text-xs font-mono text-sibila-moonlight outline-none transition-all shadow-inner pr-10"
          />
          <button
            type="button"
            onClick={() => setShowSecret(!showSecret)}
            className="absolute right-3 top-1/2 -translate-y-1/2 text-sibila-smoke hover:text-sibila-amethyst transition-colors"
          >
            {showSecret ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
          </button>
        </div>
      </Field>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Field label="Phone Number ID" hint="ID numérico do seu número de telefone registrado na Meta.">
          <input
            type="text"
            value={draft.phone_number_id}
            onChange={(e) => setDraft({ ...draft, phone_number_id: e.target.value })}
            placeholder="123456789012345"
            className="w-full bg-sibila-veil/50 border border-sibila-mist/60 focus:border-sibila-amethyst/50 focus:ring-1 focus:ring-sibila-amethyst/50 rounded-xl px-4 py-3 text-xs font-mono text-sibila-moonlight outline-none transition-all shadow-inner"
          />
        </Field>

        <Field label="WABA ID" hint="WhatsApp Business Account ID (Recomendado para otimizar conexão).">
          <input
            type="text"
            value={draft.waba_id}
            onChange={(e) => setDraft({ ...draft, waba_id: e.target.value })}
            placeholder="987654321098765"
            className="w-full bg-sibila-veil/50 border border-sibila-mist/60 focus:border-sibila-amethyst/50 focus:ring-1 focus:ring-sibila-amethyst/50 rounded-xl px-4 py-3 text-xs font-mono text-sibila-moonlight outline-none transition-all shadow-inner"
          />
        </Field>
      </div>

      <Field label="App Secret (Avançado)" hint="Utilizado para validação HMAC avançada do webhook isolado por Tenant. Deixe vazio para usar a segurança global.">
        <input
          type="password"
          value={draft.app_secret}
          onChange={(e) => setDraft({ ...draft, app_secret: e.target.value })}
          placeholder="(Deixe vazio para usar configuração global)"
          className="w-full bg-sibila-veil/50 border border-sibila-mist/60 focus:border-sibila-amethyst/50 focus:ring-1 focus:ring-sibila-amethyst/50 rounded-xl px-4 py-3 text-xs font-mono text-sibila-moonlight outline-none transition-all shadow-inner"
        />
      </Field>

      <Field label="Verify Token Customizado" hint="Se vazio, o sistema de segurança gerará um token criptográfico robusto e aleatório.">
        <input
          type="text"
          value={draft.verify_token}
          onChange={(e) => setDraft({ ...draft, verify_token: e.target.value })}
          placeholder="(Gerar Automaticamente)"
          className="w-full bg-sibila-veil/50 border border-sibila-mist/60 focus:border-sibila-amethyst/50 focus:ring-1 focus:ring-sibila-amethyst/50 rounded-xl px-4 py-3 text-xs font-mono text-sibila-moonlight outline-none transition-all shadow-inner"
        />
      </Field>

      <label className="flex items-center gap-3 text-xs text-sibila-smoke cursor-pointer hover:text-sibila-moonlight transition-colors p-2 bg-sibila-veil/30 rounded-xl border border-sibila-mist/30">
        <input
          type="checkbox"
          checked={draft.skip_validation}
          onChange={(e) => setDraft({ ...draft, skip_validation: e.target.checked })}
          className="w-4 h-4 rounded border-sibila-mist text-sibila-amethyst focus:ring-sibila-amethyst bg-sibila-obsidian"
        />
        Pular validação estrita contra Meta Graph API (Use apenas em ambiente local / dev offline)
      </label>

      <div className="flex items-center gap-4 pt-4 border-t border-sibila-mist/50">
        <button
          onClick={onTest}
          disabled={!validDraft || testing}
          className="px-5 py-2.5 bg-sibila-veil/50 border border-sibila-mist hover:border-sibila-amethyst/50 disabled:opacity-50 disabled:hover:border-sibila-mist rounded-xl text-xs font-bold flex items-center gap-2 text-sibila-moonlight transition-all shadow-sm"
        >
          <Shield className="w-4 h-4 text-sibila-amethyst" />
          {testing ? 'Testando Conexão...' : 'Validar Credenciais'}
        </button>
        {testResult && (
          <span className={`text-xs font-medium flex items-center gap-1.5 px-3 py-1.5 rounded-lg border shadow-inner ${testResult.ok ? 'text-emerald-400 bg-emerald-500/10 border-emerald-500/30' : 'text-rose-400 bg-rose-500/10 border-rose-500/30'}`}>
            {testResult.ok ? <CheckCircle2 className="w-4 h-4" /> : <XCircle className="w-4 h-4" />}
            {testResult.message}
          </span>
        )}
      </div>

      <div className="flex gap-3 pt-2">
        <button
          onClick={onCancel}
          className="flex-1 px-5 py-3 bg-sibila-veil/50 hover:bg-sibila-veil border border-sibila-mist rounded-xl text-xs font-bold text-sibila-moonlight transition-colors"
        >
          Cancelar Edição
        </button>
        <button
          onClick={onSave}
          disabled={!validDraft || saving}
          className="flex-[2] px-5 py-3 bg-gradient-to-r from-sibila-amethyst to-[#9d89c4] hover:brightness-110 disabled:opacity-50 disabled:hover:brightness-100 text-white rounded-xl text-xs font-black uppercase tracking-widest shadow-[0_0_15px_rgba(124,106,153,0.3)] transition-all transform hover:scale-[1.01] active:scale-[0.99]"
        >
          {saving ? 'Gravando no Cofre...' : (isUpdate ? 'Atualizar Conexão' : 'Conectar à Nuvem')}
        </button>
      </div>
    </div>
  );
}

function SetupInstructions({
  data, onCopy,
}: {
  data: { verify_token: string; webhook_url: string; instructions: string[] };
  onCopy: (t: string, l?: string) => void;
}) {
  return (
    <div className="bg-amber-500/10 border border-amber-500/30 rounded-2xl p-6 space-y-4 shadow-inner">
      <h4 className="text-base font-display flex items-center gap-2 text-amber-400">
        <Webhook className="w-5 h-5" />
        Configure o Webhook na Meta Business
      </h4>
      <p className="text-xs text-amber-200/70">
        Para finalizar, você precisa informar à Meta para onde enviar as mensagens recebidas.
        Copie os dados abaixo e cole no painel da Meta Cloud API.
      </p>
      
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-[11px]">
        <div className="bg-sibila-obsidian/50 border border-amber-500/20 rounded-xl p-4">
          <div className="text-[10px] font-bold uppercase tracking-widest text-amber-300/60 mb-1.5">Callback URL (Webhook)</div>
          <div className="flex items-center justify-between gap-3 bg-sibila-veil/50 border border-sibila-mist/30 px-3 py-2 rounded-lg">
            <code className="font-mono text-xs text-amber-100 truncate">{data.webhook_url}</code>
            <button
              onClick={() => onCopy(data.webhook_url, 'URL copiada com sucesso!')}
              className="text-amber-300 hover:text-white transition-colors bg-amber-500/10 hover:bg-amber-500/30 p-1.5 rounded-md"
              title="Copiar Callback URL"
            >
              <Copy className="w-4 h-4" />
            </button>
          </div>
        </div>
        <div className="bg-sibila-obsidian/50 border border-amber-500/20 rounded-xl p-4">
          <div className="text-[10px] font-bold uppercase tracking-widest text-amber-300/60 mb-1.5">Verify Token (Token de Verificação)</div>
          <div className="flex items-center justify-between gap-3 bg-sibila-veil/50 border border-sibila-mist/30 px-3 py-2 rounded-lg">
            <code className="font-mono text-xs text-amber-100 truncate">{data.verify_token}</code>
            <button
              onClick={() => onCopy(data.verify_token, 'Token copiado com sucesso!')}
              className="text-amber-300 hover:text-white transition-colors bg-amber-500/10 hover:bg-amber-500/30 p-1.5 rounded-md"
              title="Copiar Verify Token"
            >
              <Copy className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>
      <div className="bg-amber-500/5 border border-amber-500/20 rounded-xl p-4 mt-2">
        <h5 className="text-[10px] uppercase tracking-widest font-bold text-amber-300/80 mb-2">Instruções Passo a Passo</h5>
        <ol className="text-xs text-amber-100/90 space-y-2 list-decimal list-inside pl-1">
          {data.instructions.map((step, i) => (
            <li key={i} className="pl-1 leading-relaxed border-l-2 border-amber-500/30 ml-1.5">{step}</li>
          ))}
        </ol>
      </div>
    </div>
  );
}

function Field({
  label, hint, children,
}: {
  label: string;
  hint?: string;
  children: React.ReactNode;
}) {
  return (
    <div className="space-y-1.5">
      <label className="block text-xs font-bold uppercase tracking-wider text-sibila-moonlight ml-1">
        {label}
      </label>
      {children}
      {hint && <p className="text-[10px] text-sibila-smoke ml-1 leading-relaxed max-w-lg">{hint}</p>}
    </div>
  );
}
