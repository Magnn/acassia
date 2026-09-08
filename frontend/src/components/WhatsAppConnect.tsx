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
    return (
      <div className="flex items-center justify-center p-12 text-secondary text-sm">
        <RefreshCw className="w-5 h-5 animate-spin mr-2 text-emerald-500" />
        Carregando credenciais Meta...
      </div>
    );
  }

  const binding = data?.binding;
  const validDraft =
    draft.access_token.trim().length > 20 &&
    draft.phone_number_id.trim().length >= 6;

  return (
    <div className="space-y-6">
      <header className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-border pb-5">
        <div>
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-[#25D366]">
              <Phone className="w-4 h-4" />
            </div>
            <h3 className="text-xl font-bold text-primary tracking-tight">
              Meta Cloud API Oficial
            </h3>
          </div>
          <p className="text-xs text-secondary mt-1.5 leading-relaxed max-w-2xl">
            Credenciais encriptadas ponta-a-ponta e isoladas por Workspace. Permite envio de mensagens ativas, botões de ação e Webhooks em tempo real.
          </p>
        </div>
        {binding && !editing && (
          <button
            onClick={() => {
              if (confirm('Deseja realmente remover a conexão? Suas automações pararão de funcionar imediatamente.')) {
                removeMut.mutate();
              }
            }}
            className="px-4 py-2 bg-red-500/10 hover:bg-red-500/20 border border-red-500/30 text-red-400 rounded-xl text-xs font-bold transition-all flex items-center gap-2 shadow-sm self-start sm:self-auto"
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
    <div className="bg-bg-surface border border-dashed border-border rounded-2xl p-8 text-center space-y-5 relative overflow-hidden">
      <div className="relative z-10 w-16 h-16 mx-auto rounded-2xl bg-[#25D366]/10 border border-[#25D366]/20 flex items-center justify-center text-[#25D366] shadow-lg">
        <Webhook className="w-8 h-8" strokeWidth={1.5} />
      </div>
      <div className="relative z-10">
        <div className="text-lg font-bold text-primary mb-1">Nenhum número conectado</div>
        <p className="text-xs text-secondary max-w-md mx-auto leading-relaxed">
          Você precisa de um App aprovado no Meta Business e um número de telefone com Token de Usuário de Sistema permanente.
        </p>
      </div>
      <div className="relative z-10 inline-flex flex-col items-center gap-1.5 bg-bg-primary border border-border px-5 py-3 rounded-xl">
        <span className="text-[10px] uppercase tracking-wider text-secondary font-bold">Callback URL gerada para seu tenant:</span>
        <code className="text-xs font-mono text-primary bg-bg-surface px-3 py-1 rounded-lg border border-border">
          {webhookUrl}
        </code>
      </div>
      <div className="relative z-10 pt-2 flex flex-col items-center gap-3">
        <button
          onClick={onStart}
          className="px-6 py-2.5 bg-gradient-to-r from-[#25D366] to-[#128C7E] hover:brightness-110 text-white rounded-xl text-xs font-bold uppercase tracking-wider shadow-lg shadow-[#25D366]/20 transition-all"
        >
          Inserir Credenciais Meta
        </button>
        <a
          href="https://developers.facebook.com/docs/whatsapp/cloud-api/get-started"
          target="_blank"
          rel="noreferrer"
          className="inline-flex items-center gap-1.5 text-xs text-secondary hover:text-primary transition-colors font-medium"
        >
          <ExternalLink className="w-3.5 h-3.5" />
          Documentação Oficial da Meta
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
  }[binding.status] || 'text-secondary bg-bg-primary border-border';

  return (
    <div className="bg-bg-surface border border-border rounded-2xl p-6 space-y-4">
      <div className="flex items-center justify-between pb-3 border-b border-border">
        <div className="flex items-center gap-3">
          {binding.status === 'active' ? (
            <div className="w-8 h-8 rounded-xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center">
              <CheckCircle2 className="w-4 h-4 text-emerald-400" />
            </div>
          ) : (
            <div className="w-8 h-8 rounded-xl bg-amber-500/10 border border-amber-500/20 flex items-center justify-center animate-pulse">
              <AlertTriangle className="w-4 h-4 text-amber-400" />
            </div>
          )}
          <span className="font-mono text-lg font-bold text-primary tracking-tight">
            {binding.display_phone_number || binding.phone_number_id}
          </span>
        </div>
        <span className={`text-[10px] font-black uppercase tracking-widest px-3 py-1 rounded-full border ${statusColor}`}>
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

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs pt-1">
        <div className="bg-bg-primary p-3 rounded-xl border border-border">
          <span className="text-[10px] uppercase tracking-wider text-secondary block mb-0.5 font-bold">Verify Token</span>
          <span className="text-primary font-medium">{binding.has_verify_token ? '✓ Definido no Tenant' : '— Global .env'}</span>
        </div>
        <div className="bg-bg-primary p-3 rounded-xl border border-border">
          <span className="text-[10px] uppercase tracking-wider text-secondary block mb-0.5 font-bold">App Secret</span>
          <span className="text-primary font-medium">{binding.has_app_secret ? '✓ Definido no Tenant' : '— Global .env'}</span>
        </div>
      </div>

      {binding.last_verified_at && (
        <div className="text-[11px] text-secondary flex items-center gap-1.5">
          <Shield className="w-3.5 h-3.5 text-emerald-400" />
          Última validação da Graph API: {new Date(binding.last_verified_at).toLocaleString('pt-BR')}
        </div>
      )}
      {binding.last_error && (
        <div className="text-[11px] text-rose-400 bg-rose-500/10 border border-rose-500/30 rounded-xl p-3">
          <strong>Erro na última verificação:</strong> {binding.last_error}
        </div>
      )}

      <div className="bg-bg-primary border border-border rounded-xl p-3.5 text-[11px]">
        <div className="flex items-center gap-3">
          {binding.subscribed_at ? (
            <>
              <div className="w-5 h-5 rounded-full bg-emerald-500/20 flex items-center justify-center">
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
              </div>
              <span className="text-emerald-400 font-bold text-xs">Webhooks Subscritos no WABA</span>
              <span className="text-secondary text-[10px] ml-auto font-mono">
                {new Date(binding.subscribed_at).toLocaleString('pt-BR')}
              </span>
            </>
          ) : (
            <>
              <div className="w-5 h-5 rounded-full bg-amber-500/20 flex items-center justify-center animate-pulse">
                <AlertTriangle className="w-3.5 h-3.5 text-amber-400" />
              </div>
              <span className="text-amber-400 font-bold text-xs">App não subscrita aos Webhooks WABA</span>
              <button
                onClick={onSubscribe}
                disabled={subscribing}
                className="ml-auto text-xs text-blue-400 hover:text-blue-300 hover:underline font-bold flex items-center gap-1.5 transition-colors"
              >
                <RefreshCw className={`w-3 h-3 ${subscribing ? 'animate-spin' : ''}`} />
                {subscribing ? 'Subscrevendo…' : 'Subscrever'}
              </button>
            </>
          )}
        </div>
        {binding.subscribe_error && !binding.subscribed_at && (
          <div className="text-[11px] text-rose-400 mt-2 bg-rose-500/10 p-2 rounded-lg">{binding.subscribe_error}</div>
        )}
      </div>

      <div className="flex flex-wrap gap-2.5 pt-3 border-t border-border">
        <button
          onClick={onEdit}
          className="px-3.5 py-2 bg-bg-primary hover:bg-bg-surface border border-border hover:border-[#25D366]/40 rounded-xl text-xs font-bold text-primary flex items-center gap-2 transition-all shadow-sm"
        >
          <KeyRound className="w-3.5 h-3.5 text-[#25D366]" />
          Atualizar Credenciais
        </button>
        <button
          onClick={onRotate}
          disabled={rotating}
          className="px-3.5 py-2 bg-bg-primary hover:bg-bg-surface border border-border hover:border-amber-500/40 rounded-xl text-xs font-bold text-primary flex items-center gap-2 transition-all shadow-sm disabled:opacity-50"
        >
          <RefreshCw className={`w-3.5 h-3.5 text-amber-400 ${rotating ? 'animate-spin' : ''}`} />
          Rotacionar Verify Token
        </button>
        {binding.webhook_path && (
          <button
            onClick={onRotatePath}
            disabled={rotatingPath}
            className="px-3.5 py-2 bg-bg-primary hover:bg-bg-surface border border-border hover:border-blue-500/40 rounded-xl text-xs font-bold text-primary flex items-center gap-2 transition-all shadow-sm disabled:opacity-50"
            title="Gera nova URL per-tenant"
          >
            <RefreshCw className={`w-3.5 h-3.5 text-blue-400 ${rotatingPath ? 'animate-spin' : ''}`} />
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
      className={`rounded-2xl p-5 border transition-colors ${
        hasInbound
          ? 'bg-emerald-500/5 border-emerald-500/20'
          : 'bg-amber-500/5 border-amber-500/20'
      }`}
    >
      <div className="flex items-center gap-2.5 mb-3">
        <div className={`w-7 h-7 rounded-lg flex items-center justify-center ${hasInbound ? 'bg-emerald-500/10 text-emerald-400' : 'bg-amber-500/10 text-amber-400'}`}>
          {hasInbound ? (
            <Inbox className="w-4 h-4" />
          ) : (
            <Activity className="w-4 h-4 animate-pulse" />
          )}
        </div>
        <span className={`text-[10px] font-bold uppercase tracking-wider ${hasInbound ? 'text-emerald-400' : 'text-amber-400'}`}>
          {hasInbound ? 'Recebendo Webhooks Ativamente' : 'Aguardando 1ª Mensagem do Chip'}
        </span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-[11px]">
        <div className="bg-bg-primary p-3 rounded-xl border border-border">
          <div className="text-[10px] font-bold uppercase tracking-wider text-secondary">Total Recebido</div>
          <div className="text-xl font-black tabular-nums mt-0.5 text-primary">{binding.inbound_count}</div>
        </div>
        <div className="bg-bg-primary p-3 rounded-xl border border-border">
          <div className="text-[10px] font-bold uppercase tracking-wider text-secondary">Primeira Mensagem</div>
          <div className="text-xs font-mono font-bold mt-1 text-primary">
            {binding.first_inbound_at
              ? new Date(binding.first_inbound_at).toLocaleString('pt-BR')
              : '—'}
          </div>
        </div>
        <div className="bg-bg-primary p-3 rounded-xl border border-border">
          <div className="text-[10px] font-bold uppercase tracking-wider text-secondary">Última Mensagem</div>
          <div className="text-xs font-mono font-bold mt-1 text-primary">
            {binding.last_inbound_at
              ? new Date(binding.last_inbound_at).toLocaleString('pt-BR')
              : '—'}
          </div>
        </div>
      </div>

      {!hasInbound && (
        <p className="text-xs text-secondary mt-3 flex items-center gap-2 bg-amber-500/10 p-2.5 rounded-xl border border-amber-500/20 text-amber-200">
          <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0" />
          Envie um "Oi" do seu celular pessoal para o número conectado para validar o webhook em tempo real.
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

  if (!stats) return null;

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
    <div className="bg-bg-surface border border-border rounded-2xl p-6 space-y-4">
      <div className="flex items-center justify-between border-b border-border pb-3">
        <h4 className="text-xs font-bold uppercase tracking-wider text-primary flex items-center gap-2">
          <Activity className="w-4 h-4 text-emerald-400" />
          Observabilidade do Webhook
        </h4>
        {hasErrors && (
          <span className="text-[10px] text-amber-400 font-bold flex items-center gap-1 px-2 py-0.5 bg-amber-500/10 rounded-lg border border-amber-500/20">
            <AlertTriangle className="w-3 h-3" />
            {errorEvents.length} erro{errorEvents.length === 1 ? '' : 's'} (24h)
          </span>
        )}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-[11px]">
        <div className="bg-bg-primary border border-border rounded-xl p-3">
          <div className="text-[10px] font-bold uppercase tracking-wider text-secondary mb-0.5">Taxa de Processamento</div>
          <div className="text-lg font-black tabular-nums text-primary">
            {stats.rate_limiter.tokens_remaining}<span className="text-secondary text-xs font-medium">/{stats.rate_limiter.burst_capacity}</span>
          </div>
          <div className="text-[10px] text-secondary mt-0.5">Recarrega a {stats.rate_limiter.rate_per_min}/min</div>
        </div>
        <div className="bg-bg-primary border border-border rounded-xl p-3">
          <div className="text-[10px] font-bold uppercase tracking-wider text-secondary mb-0.5">Eventos 24h</div>
          <div className="text-lg font-black tabular-nums text-primary">
            {Object.values(events).reduce((a, b) => a + b, 0)}
          </div>
          <div className="text-[10px] text-secondary mt-0.5">Requisições processadas</div>
        </div>
        <div className="bg-bg-primary border border-border rounded-xl p-3">
          <div className="text-[10px] font-bold uppercase tracking-wider text-secondary mb-0.5">Total Histórico</div>
          <div className="text-lg font-black tabular-nums text-primary">
            {stats.inbound_count_total}
          </div>
          <div className="text-[10px] text-secondary mt-0.5">Desde o primeiro binding</div>
        </div>
      </div>

      {hasErrors && (
        <div className="space-y-1.5 bg-rose-500/5 p-3 rounded-xl border border-rose-500/20">
          <div className="text-[10px] uppercase tracking-wider text-rose-400 font-bold mb-1">Erros Detectados</div>
          {errorEvents.map((evt) => (
            <div key={evt} className={`text-xs font-bold flex items-center justify-between bg-bg-primary px-3 py-1.5 rounded-lg border border-border ${eventColor[evt] || 'text-secondary'}`}>
              <span className="uppercase">{evt}</span>
              <span className="tabular-nums px-2 py-0.5 bg-bg-surface rounded-md">{events[evt]}</span>
            </div>
          ))}
        </div>
      )}

      {logs.length > 0 && (
        <details className="group border border-border rounded-xl overflow-hidden bg-bg-primary">
          <summary className="cursor-pointer text-xs text-primary uppercase tracking-wider font-bold list-none flex items-center justify-between p-3 hover:bg-bg-surface transition-colors">
            <div className="flex items-center gap-2">
              <span className="group-open:rotate-90 transition-transform">▸</span>
              Logs Recentes de Webhook
            </div>
            <span className="text-[10px] text-secondary bg-bg-surface border border-border px-2 py-0.5 rounded-md">{logs.length} registros</span>
          </summary>
          <div className="px-3 pb-3 space-y-1.5 max-h-56 overflow-y-auto">
            {logs.map((log) => (
              <div
                key={log.id}
                className="bg-bg-surface border border-border rounded-lg p-2.5 text-[11px] flex items-start gap-2.5"
              >
                <span className={`font-bold uppercase tracking-wider px-1.5 py-0.5 rounded text-[9px] ${
                  eventColor[log.event_type] ? eventColor[log.event_type].replace('text-', 'bg-').replace('400', '500/20') + ' ' + eventColor[log.event_type] : 'bg-border text-secondary'
                } shrink-0`}>
                  {log.event_type}
                </span>
                <span className="text-secondary font-mono truncate flex-1">{log.message || 'Sem descrição'}</span>
                <span className="text-secondary text-[9px] shrink-0 font-mono">
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
    <div className="bg-bg-surface border border-border rounded-2xl p-6 space-y-4">
      <div className="flex items-center gap-2 border-b border-border pb-3">
        <Send className="w-4 h-4 text-emerald-400" />
        <h4 className="text-xs font-bold uppercase tracking-wider text-primary">
          Enviar Mensagem de Teste Direto
        </h4>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-[200px_1fr_auto] gap-3">
        <input
          type="tel"
          value={to}
          onChange={(e) => setTo(e.target.value)}
          placeholder="55119xxxxxxxx"
          className="bg-bg-primary border border-border focus:border-[#25D366] rounded-xl px-3.5 py-2 text-xs font-mono text-primary outline-none transition-all"
        />
        <input
          type="text"
          value={body}
          onChange={(e) => setBody(e.target.value)}
          placeholder="Mensagem (deixe vazio para usar mensagem padrão de teste)"
          className="bg-bg-primary border border-border focus:border-[#25D366] rounded-xl px-3.5 py-2 text-xs text-primary outline-none transition-all"
          maxLength={500}
        />
        <button
          onClick={() => sendMut.mutate()}
          disabled={!valid || sendMut.isPending}
          className="px-5 py-2 bg-gradient-to-r from-[#25D366] to-[#128C7E] hover:brightness-110 disabled:opacity-40 text-white rounded-xl text-xs font-bold uppercase tracking-wider transition-all"
        >
          {sendMut.isPending ? 'Enviando…' : 'Enviar Teste'}
        </button>
      </div>
      <div className="text-[10px] text-secondary">
        Formato E.164 (com DDI e DDD, sem símbolos). Ex: <code className="bg-bg-primary px-1.5 py-0.5 rounded border border-border">556981051492</code>.
      </div>
      {result && (
        <div
          className={`text-xs flex items-start gap-2 p-3 rounded-xl border ${
            result.ok ? 'text-emerald-400 bg-emerald-500/10 border-emerald-500/30' : 'text-rose-400 bg-rose-500/10 border-rose-500/30'
          }`}
        >
          {result.ok ? (
            <CheckCircle2 className="w-4 h-4 mt-0.5 shrink-0" />
          ) : (
            <XCircle className="w-4 h-4 mt-0.5 shrink-0" />
          )}
          <span>
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
    <div className="flex items-center justify-between gap-3 text-xs border-b border-border/50 pb-2.5 last:border-0 last:pb-0">
      <span className="text-secondary uppercase tracking-wider text-[10px] font-bold">{label}</span>
      <div className="flex items-center gap-2 min-w-0">
        <code className={`bg-bg-primary border border-border px-2 py-1 rounded-lg text-primary truncate ${mono ? 'font-mono' : ''}`}>
          {value}
        </code>
        <button
          onClick={() => onCopy(value, `${label} copiado`)}
          className="text-secondary hover:text-primary transition-colors p-1 bg-bg-primary hover:bg-bg-surface rounded-lg border border-border shrink-0"
          title="Copiar"
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
    <div className="bg-bg-surface border border-border rounded-2xl p-6 space-y-5">
      <Field label="Access Token Permanente (System User)" hint="Painel Meta → Business Settings → Users → System Users → Generate Token. Permissões necessárias: whatsapp_business_messaging e whatsapp_business_management.">
        <div className="relative">
          <input
            type={showSecret ? 'text' : 'password'}
            value={draft.access_token}
            onChange={(e) => setDraft({ ...draft, access_token: e.target.value })}
            placeholder="EAAB..."
            className="w-full bg-bg-primary border border-border focus:border-[#25D366] rounded-xl px-4 py-2.5 text-xs font-mono text-primary outline-none transition-all pr-10"
          />
          <button
            type="button"
            onClick={() => setShowSecret(!showSecret)}
            className="absolute right-3 top-1/2 -translate-y-1/2 text-secondary hover:text-primary transition-colors"
          >
            {showSecret ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
          </button>
        </div>
      </Field>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Field label="Phone Number ID" hint="ID numérico do número registrado na Meta Developer.">
          <input
            type="text"
            value={draft.phone_number_id}
            onChange={(e) => setDraft({ ...draft, phone_number_id: e.target.value })}
            placeholder="Ex: 574220792437648"
            className="w-full bg-bg-primary border border-border focus:border-[#25D366] rounded-xl px-4 py-2.5 text-xs font-mono text-primary outline-none transition-all"
          />
        </Field>

        <Field label="WABA ID" hint="WhatsApp Business Account ID.">
          <input
            type="text"
            value={draft.waba_id}
            onChange={(e) => setDraft({ ...draft, waba_id: e.target.value })}
            placeholder="Ex: 112233445566778"
            className="w-full bg-bg-primary border border-border focus:border-[#25D366] rounded-xl px-4 py-2.5 text-xs font-mono text-primary outline-none transition-all"
          />
        </Field>
      </div>

      <Field label="App Secret (Opcional)" hint="Utilizado para validação de assinatura HMAC dos webhooks. Deixe vazio para usar segurança padrão.">
        <input
          type="password"
          value={draft.app_secret}
          onChange={(e) => setDraft({ ...draft, app_secret: e.target.value })}
          placeholder="(Opcional)"
          className="w-full bg-bg-primary border border-border focus:border-[#25D366] rounded-xl px-4 py-2.5 text-xs font-mono text-primary outline-none transition-all"
        />
      </Field>

      <Field label="Verify Token Customizado (Opcional)" hint="Token para validação inicial do webhook na Meta. Se vazio, será gerado automaticamente.">
        <input
          type="text"
          value={draft.verify_token}
          onChange={(e) => setDraft({ ...draft, verify_token: e.target.value })}
          placeholder="(Gerar automaticamente)"
          className="w-full bg-bg-primary border border-border focus:border-[#25D366] rounded-xl px-4 py-2.5 text-xs font-mono text-primary outline-none transition-all"
        />
      </Field>

      <label className="flex items-center gap-3 text-xs text-secondary cursor-pointer hover:text-primary transition-colors p-2.5 bg-bg-primary rounded-xl border border-border">
        <input
          type="checkbox"
          checked={draft.skip_validation}
          onChange={(e) => setDraft({ ...draft, skip_validation: e.target.checked })}
          className="w-4 h-4 rounded border-border text-[#25D366] focus:ring-[#25D366] bg-bg-surface"
        />
        Pular validação imediata contra Meta Graph API (útil para pré-cadastro em desenvolvimento)
      </label>

      <div className="flex items-center gap-4 pt-3 border-t border-border">
        <button
          onClick={onTest}
          disabled={!validDraft || testing}
          className="px-4 py-2.5 bg-bg-primary border border-border hover:border-[#25D366]/50 disabled:opacity-40 rounded-xl text-xs font-bold flex items-center gap-2 text-primary transition-all shadow-sm"
        >
          <Shield className="w-4 h-4 text-[#25D366]" />
          {testing ? 'Testando Conexão...' : 'Validar Credenciais'}
        </button>
        {testResult && (
          <span className={`text-xs font-medium flex items-center gap-1.5 px-3 py-1.5 rounded-lg border ${testResult.ok ? 'text-emerald-400 bg-emerald-500/10 border-emerald-500/30' : 'text-rose-400 bg-rose-500/10 border-rose-500/30'}`}>
            {testResult.ok ? <CheckCircle2 className="w-4 h-4" /> : <XCircle className="w-4 h-4" />}
            {testResult.message}
          </span>
        )}
      </div>

      <div className="flex gap-3 pt-2">
        <button
          onClick={onCancel}
          className="flex-1 px-4 py-2.5 bg-bg-primary hover:bg-bg-surface border border-border rounded-xl text-xs font-bold text-secondary hover:text-primary transition-colors"
        >
          Cancelar
        </button>
        <button
          onClick={onSave}
          disabled={!validDraft || saving}
          className="flex-[2] px-4 py-2.5 bg-gradient-to-r from-[#25D366] to-[#128C7E] hover:brightness-110 disabled:opacity-40 text-white rounded-xl text-xs font-bold uppercase tracking-wider shadow-md transition-all"
        >
          {saving ? 'Gravando...' : (isUpdate ? 'Atualizar Conexão' : 'Conectar Meta WhatsApp')}
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
    <div className="bg-amber-500/5 border border-amber-500/25 rounded-2xl p-6 space-y-4">
      <h4 className="text-sm font-bold flex items-center gap-2 text-amber-400">
        <Webhook className="w-4 h-4" />
        Configuração do Webhook no Meta Business Manager
      </h4>
      <p className="text-xs text-secondary leading-relaxed">
        Cole a URL de retorno e o token de verificação na seção <strong>WhatsApp &gt; Configuração &gt; Webhook</strong> do seu Meta App:
      </p>
      
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-[11px]">
        <div className="bg-bg-primary border border-border rounded-xl p-3">
          <div className="text-[10px] font-bold uppercase tracking-wider text-secondary mb-1">Callback URL (Webhook)</div>
          <div className="flex items-center justify-between gap-2 bg-bg-surface border border-border px-3 py-2 rounded-lg">
            <code className="font-mono text-xs text-primary truncate">{data.webhook_url}</code>
            <button
              onClick={() => onCopy(data.webhook_url, 'URL copiada!')}
              className="text-secondary hover:text-primary p-1 rounded"
              title="Copiar"
            >
              <Copy className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
        <div className="bg-bg-primary border border-border rounded-xl p-3">
          <div className="text-[10px] font-bold uppercase tracking-wider text-secondary mb-1">Verify Token</div>
          <div className="flex items-center justify-between gap-2 bg-bg-surface border border-border px-3 py-2 rounded-lg">
            <code className="font-mono text-xs text-primary truncate">{data.verify_token}</code>
            <button
              onClick={() => onCopy(data.verify_token, 'Token copiado!')}
              className="text-secondary hover:text-primary p-1 rounded"
              title="Copiar"
            >
              <Copy className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      </div>
      <div className="bg-bg-primary/50 border border-border rounded-xl p-3.5 mt-2">
        <h5 className="text-[10px] uppercase tracking-wider font-bold text-secondary mb-1.5">Passo a Passo</h5>
        <ol className="text-xs text-secondary space-y-1 list-decimal list-inside pl-1">
          {data.instructions.map((step, i) => (
            <li key={i} className="leading-relaxed">{step}</li>
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
      <label className="block text-xs font-bold text-primary">
        {label}
      </label>
      {children}
      {hint && <p className="text-[11px] text-secondary leading-relaxed">{hint}</p>}
    </div>
  );
}
