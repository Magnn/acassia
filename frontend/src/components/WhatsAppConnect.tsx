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
      <header className="flex items-start justify-between gap-4">
        <div>
          <h3 className="text-xl font-black tracking-tight flex items-center gap-2">
            <Phone className="w-5 h-5 text-accent-amethyst" />
            WhatsApp Cloud API
          </h3>
          <p className="text-xs text-secondary mt-1">
            Conecte seu número Meta WhatsApp Business — credenciais são salvas
            criptografadas por tenant.
          </p>
        </div>
        {binding && !editing && (
          <button
            onClick={() => {
              if (confirm('Remover conexão? Você precisará reconectar para receber mensagens.')) {
                removeMut.mutate();
              }
            }}
            className="text-xs text-rose-400 hover:underline flex items-center gap-1 font-bold"
          >
            <Trash2 className="w-3 h-3" />
            Remover
          </button>
        )}
      </header>

      {!editing && binding ? (
        <>
          <BindingView
            binding={binding}
            webhookUrl={data!.webhook_url}
            onEdit={() => setEditing(true)}
            onCopy={copy}
            onRotate={() => rotateMut.mutate()}
            rotating={rotateMut.isPending}
            onSubscribe={() => subscribeMut.mutate()}
            subscribing={subscribeMut.isPending}
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
    <div className="bg-bg-primary border border-dashed border-border rounded-2xl p-6 text-center space-y-3">
      <Webhook className="w-8 h-8 mx-auto text-secondary" />
      <div className="text-sm font-bold">Nenhum número conectado ainda</div>
      <p className="text-xs text-secondary">
        Você precisa de um app aprovado no Meta Business + um número WhatsApp Cloud API
        com System User token permanente.
      </p>
      <div className="text-[11px] text-secondary">
        Webhook URL: <code className="bg-bg-surface px-1.5 py-0.5 rounded">{webhookUrl}</code>
      </div>
      <button
        onClick={onStart}
        className="px-5 py-2.5 bg-accent-amethyst hover:bg-accent-amethyst/90 text-white rounded-xl text-xs font-black uppercase tracking-widest"
      >
        Conectar WhatsApp
      </button>
      <a
        href="https://developers.facebook.com/docs/whatsapp/cloud-api/get-started"
        target="_blank"
        rel="noreferrer"
        className="inline-flex items-center gap-1 text-[11px] text-accent-amethyst hover:underline"
      >
        Documentação Meta
        <ExternalLink className="w-3 h-3" />
      </a>
    </div>
  );
}

function BindingView({
  binding, webhookUrl, onEdit, onCopy, onRotate, rotating,
  onSubscribe, subscribing,
}: {
  binding: import('../api/integrations').WaBinding;
  webhookUrl: string;
  onEdit: () => void;
  onCopy: (text: string, label?: string) => void;
  onRotate: () => void;
  rotating: boolean;
  onSubscribe: () => void;
  subscribing: boolean;
}) {
  const statusColor = {
    active: 'text-emerald-400 bg-emerald-400/10 border-emerald-400/30',
    pending: 'text-amber-400 bg-amber-400/10 border-amber-400/30',
    failed: 'text-rose-400 bg-rose-400/10 border-rose-400/30',
  }[binding.status] || 'text-secondary bg-bg-primary border-border';

  return (
    <div className="bg-bg-primary border border-border rounded-2xl p-5 space-y-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          {binding.status === 'active' ? (
            <CheckCircle2 className="w-5 h-5 text-emerald-400" />
          ) : (
            <AlertTriangle className="w-5 h-5 text-amber-400" />
          )}
          <span className="font-black text-base">
            {binding.display_phone_number || binding.phone_number_id}
          </span>
        </div>
        <span className={`text-[10px] font-black uppercase tracking-widest px-2 py-0.5 rounded border ${statusColor}`}>
          {binding.status}
        </span>
      </div>

      <Row label="phone_number_id" value={binding.phone_number_id} onCopy={onCopy} mono />
      {binding.waba_id && (
        <Row label="waba_id" value={binding.waba_id} onCopy={onCopy} mono />
      )}
      <Row label="Webhook URL" value={webhookUrl} onCopy={onCopy} mono />

      <div className="grid grid-cols-2 gap-2 text-[11px] pt-1">
        <div className="text-secondary">
          verify_token: {binding.has_verify_token ? '✓ definido' : '— global'}
        </div>
        <div className="text-secondary">
          app_secret: {binding.has_app_secret ? '✓ definido' : '— global'}
        </div>
      </div>

      {binding.last_verified_at && (
        <div className="text-[10px] text-secondary">
          Última validação: {new Date(binding.last_verified_at).toLocaleString('pt-BR')}
        </div>
      )}
      {binding.last_error && (
        <div className="text-[11px] text-rose-400 bg-rose-400/10 border border-rose-400/30 rounded p-2">
          {binding.last_error}
        </div>
      )}

      <div className="bg-bg-surface border border-border rounded-lg p-2.5 text-[11px]">
        <div className="flex items-center gap-2">
          {binding.subscribed_at ? (
            <>
              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
              <span className="text-emerald-400 font-bold">Subscrita ao WABA</span>
              <span className="text-secondary text-[10px] ml-auto">
                {new Date(binding.subscribed_at).toLocaleString('pt-BR')}
              </span>
            </>
          ) : (
            <>
              <AlertTriangle className="w-3.5 h-3.5 text-amber-400" />
              <span className="text-amber-300 font-bold">App não subscrita ao WABA</span>
              <button
                onClick={onSubscribe}
                disabled={subscribing}
                className="ml-auto text-[10px] text-accent-amethyst hover:underline font-bold flex items-center gap-1"
              >
                <RefreshCw className={`w-3 h-3 ${subscribing ? 'animate-spin' : ''}`} />
                {subscribing ? 'Subscrevendo…' : 'Tentar subscrever'}
              </button>
            </>
          )}
        </div>
        {binding.subscribe_error && !binding.subscribed_at && (
          <div className="text-[10px] text-rose-400 mt-1.5">{binding.subscribe_error}</div>
        )}
      </div>

      <div className="flex gap-2 pt-2 border-t border-border">
        <button
          onClick={onEdit}
          className="px-3 py-1.5 bg-bg-surface border border-border hover:border-accent-amethyst/30 rounded-lg text-[11px] font-bold flex items-center gap-1.5"
        >
          <KeyRound className="w-3 h-3" />
          Atualizar credenciais
        </button>
        <button
          onClick={onRotate}
          disabled={rotating}
          className="px-3 py-1.5 bg-bg-surface border border-border hover:border-accent-amethyst/30 rounded-lg text-[11px] font-bold flex items-center gap-1.5"
        >
          <RefreshCw className={`w-3 h-3 ${rotating ? 'animate-spin' : ''}`} />
          Rotacionar verify_token
        </button>
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
      className={`rounded-2xl p-4 border ${
        hasInbound
          ? 'bg-emerald-500/5 border-emerald-500/30'
          : 'bg-amber-500/5 border-amber-500/30'
      }`}
    >
      <div className="flex items-center gap-2 mb-2">
        {hasInbound ? (
          <Inbox className="w-4 h-4 text-emerald-400" />
        ) : (
          <Activity className="w-4 h-4 text-amber-300" />
        )}
        <span className={`text-[10px] font-black uppercase tracking-widest ${hasInbound ? 'text-emerald-400' : 'text-amber-300'}`}>
          {hasInbound ? 'Recebendo mensagens' : 'Aguardando primeira mensagem'}
        </span>
      </div>

      <div className="grid grid-cols-3 gap-3 text-[11px]">
        <div>
          <div className="text-[9px] uppercase tracking-widest text-secondary">Total inbound</div>
          <div className="text-xl font-black tabular-nums mt-0.5">{binding.inbound_count}</div>
        </div>
        <div>
          <div className="text-[9px] uppercase tracking-widest text-secondary">1ª msg</div>
          <div className="text-[11px] font-bold mt-0.5">
            {binding.first_inbound_at
              ? new Date(binding.first_inbound_at).toLocaleString('pt-BR')
              : '—'}
          </div>
        </div>
        <div>
          <div className="text-[9px] uppercase tracking-widest text-secondary">Última msg</div>
          <div className="text-[11px] font-bold mt-0.5">
            {binding.last_inbound_at
              ? new Date(binding.last_inbound_at).toLocaleString('pt-BR')
              : '—'}
          </div>
        </div>
      </div>

      {!hasInbound && (
        <p className="text-[11px] text-secondary mt-2">
          Mande uma msg do seu celular para o número conectado pra confirmar
          o webhook. Costuma chegar em 1-2 segundos.
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
    <div className="bg-bg-primary border border-border rounded-2xl p-4 space-y-3">
      <div className="flex items-center justify-between">
        <h4 className="text-[10px] font-black uppercase tracking-widest flex items-center gap-1.5">
          <Activity className="w-3 h-3 text-accent-amethyst" />
          Observabilidade do webhook
        </h4>
        {hasErrors && (
          <span className="text-[10px] text-amber-300 font-bold flex items-center gap-1">
            <AlertTriangle className="w-3 h-3" />
            {errorEvents.length} tipo{errorEvents.length === 1 ? '' : 's'} de evento nas últimas 24h
          </span>
        )}
      </div>

      <div className="grid grid-cols-3 gap-3 text-[11px]">
        <div className="bg-bg-surface border border-border rounded-lg p-2">
          <div className="text-[9px] uppercase tracking-widest text-secondary">Rate atual</div>
          <div className="text-xs font-black tabular-nums mt-0.5">
            {stats.rate_limiter.tokens_remaining}/{stats.rate_limiter.burst_capacity}
          </div>
          <div className="text-[9px] text-secondary mt-0.5">
            {stats.rate_limiter.rate_per_min}/min
          </div>
        </div>
        <div className="bg-bg-surface border border-border rounded-lg p-2">
          <div className="text-[9px] uppercase tracking-widest text-secondary">Inbound 24h</div>
          <div className="text-xs font-black tabular-nums mt-0.5">
            {Object.values(events).reduce((a, b) => a + b, 0)}
          </div>
          <div className="text-[9px] text-secondary mt-0.5">eventos logados</div>
        </div>
        <div className="bg-bg-surface border border-border rounded-lg p-2">
          <div className="text-[9px] uppercase tracking-widest text-secondary">Total inbound</div>
          <div className="text-xs font-black tabular-nums mt-0.5">
            {stats.inbound_count_total}
          </div>
          <div className="text-[9px] text-secondary mt-0.5">desde a conexão</div>
        </div>
      </div>

      {hasErrors && (
        <div className="space-y-1">
          {errorEvents.map((evt) => (
            <div key={evt} className={`text-[11px] font-bold ${eventColor[evt] || 'text-secondary'}`}>
              {evt}: {events[evt]}
            </div>
          ))}
        </div>
      )}

      {logs.length > 0 && (
        <details className="group">
          <summary className="cursor-pointer text-[10px] text-secondary hover:text-primary uppercase tracking-widest font-bold list-none flex items-center gap-1">
            <span className="group-open:rotate-90 transition-transform">▸</span>
            Eventos recentes ({logs.length})
          </summary>
          <div className="mt-2 space-y-1 max-h-48 overflow-y-auto">
            {logs.map((log) => (
              <div
                key={log.id}
                className="bg-bg-surface border border-border rounded p-1.5 text-[10px] flex items-start gap-2"
              >
                <span className={`font-bold uppercase tracking-widest ${eventColor[log.event_type] || 'text-secondary'} flex-shrink-0`}>
                  {log.event_type}
                </span>
                <span className="text-secondary truncate flex-1">{log.message || ''}</span>
                <span className="text-secondary text-[9px] flex-shrink-0">
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
    <div className="bg-bg-primary border border-border rounded-2xl p-4 space-y-3">
      <div className="flex items-center gap-2">
        <Send className="w-4 h-4 text-accent-amethyst" />
        <h4 className="text-[10px] font-black uppercase tracking-widest">
          Enviar mensagem de teste
        </h4>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-[200px_1fr_auto] gap-2">
        <input
          type="tel"
          value={to}
          onChange={(e) => setTo(e.target.value)}
          placeholder="55119xxxxxxxx"
          className="bg-bg-surface border border-border rounded-xl px-3 py-2 text-xs font-mono"
        />
        <input
          type="text"
          value={body}
          onChange={(e) => setBody(e.target.value)}
          placeholder="Mensagem (deixe vazio pra usar default)"
          className="bg-bg-surface border border-border rounded-xl px-3 py-2 text-xs"
          maxLength={500}
        />
        <button
          onClick={() => sendMut.mutate()}
          disabled={!valid || sendMut.isPending}
          className="px-4 py-2 bg-accent-amethyst hover:bg-accent-amethyst/90 disabled:opacity-30 text-white rounded-xl text-[11px] font-black uppercase tracking-widest"
        >
          {sendMut.isPending ? 'Enviando…' : 'Enviar'}
        </button>
      </div>
      <div className="text-[10px] text-secondary">
        Em E.164 sem +. Ex.: <code className="bg-bg-surface px-1 rounded">5511999999999</code>.
        Custos da Meta aplicam-se normalmente.
      </div>
      {result && (
        <div
          className={`text-[11px] flex items-start gap-1 ${
            result.ok ? 'text-emerald-400' : 'text-rose-400'
          }`}
        >
          {result.ok ? (
            <CheckCircle2 className="w-3 h-3 mt-0.5 flex-shrink-0" />
          ) : (
            <XCircle className="w-3 h-3 mt-0.5 flex-shrink-0" />
          )}
          <span>
            {result.ok
              ? `wamid: ${result.message_id}`
              : result.message}
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
    <div className="flex items-center justify-between gap-2 text-[11px]">
      <span className="text-secondary uppercase tracking-widest text-[9px] font-black">{label}</span>
      <div className="flex items-center gap-1.5 min-w-0">
        <code className={`bg-bg-surface border border-border px-1.5 py-0.5 rounded truncate ${mono ? 'font-mono' : ''}`}>
          {value}
        </code>
        <button
          onClick={() => onCopy(value, `${label} copiado`)}
          className="text-secondary hover:text-accent-amethyst flex-shrink-0"
        >
          <Copy className="w-3 h-3" />
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
    <div className="bg-bg-primary border border-border rounded-2xl p-5 space-y-4">
      <Field label="Access Token (System User permanente)" hint="Painel Meta → Business Settings → Users → System Users → Generate Token. Permissões: whatsapp_business_messaging, whatsapp_business_management.">
        <div className="relative">
          <input
            type={showSecret ? 'text' : 'password'}
            value={draft.access_token}
            onChange={(e) => setDraft({ ...draft, access_token: e.target.value })}
            placeholder="EAAxxx..."
            className="w-full bg-bg-surface border border-border rounded-xl px-3 py-2 text-xs font-mono pr-9"
          />
          <button
            type="button"
            onClick={() => setShowSecret(!showSecret)}
            className="absolute right-2 top-1/2 -translate-y-1/2 text-secondary hover:text-primary"
          >
            {showSecret ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
          </button>
        </div>
      </Field>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        <Field label="Phone Number ID" hint="ID numérico do número (não o número em si).">
          <input
            type="text"
            value={draft.phone_number_id}
            onChange={(e) => setDraft({ ...draft, phone_number_id: e.target.value })}
            placeholder="123456789012345"
            className="w-full bg-bg-surface border border-border rounded-xl px-3 py-2 text-xs font-mono"
          />
        </Field>

        <Field label="WABA ID (opcional mas recomendado)">
          <input
            type="text"
            value={draft.waba_id}
            onChange={(e) => setDraft({ ...draft, waba_id: e.target.value })}
            placeholder="987654321098765"
            className="w-full bg-bg-surface border border-border rounded-xl px-3 py-2 text-xs font-mono"
          />
        </Field>
      </div>

      <Field label="App Secret (opcional)" hint="Para validação HMAC do webhook por tenant. Se vazio, usa o secret global do .env.">
        <input
          type="password"
          value={draft.app_secret}
          onChange={(e) => setDraft({ ...draft, app_secret: e.target.value })}
          placeholder="(deixe vazio pra usar global)"
          className="w-full bg-bg-surface border border-border rounded-xl px-3 py-2 text-xs font-mono"
        />
      </Field>

      <Field label="Verify Token customizado (opcional)" hint="Se vazio, geramos um aleatório forte ao salvar.">
        <input
          type="text"
          value={draft.verify_token}
          onChange={(e) => setDraft({ ...draft, verify_token: e.target.value })}
          placeholder="(auto)"
          className="w-full bg-bg-surface border border-border rounded-xl px-3 py-2 text-xs font-mono"
        />
      </Field>

      <label className="flex items-center gap-2 text-[11px] text-secondary cursor-pointer">
        <input
          type="checkbox"
          checked={draft.skip_validation}
          onChange={(e) => setDraft({ ...draft, skip_validation: e.target.checked })}
        />
        Pular validação contra Graph API (dev offline)
      </label>

      <div className="flex items-center gap-3 pt-3 border-t border-border">
        <button
          onClick={onTest}
          disabled={!validDraft || testing}
          className="px-4 py-2 bg-bg-surface border border-border hover:border-accent-amethyst/30 disabled:opacity-30 rounded-xl text-[11px] font-bold flex items-center gap-2"
        >
          <Shield className="w-3 h-3" />
          {testing ? 'Testando…' : 'Testar credenciais'}
        </button>
        {testResult && (
          <span className={`text-[11px] flex items-center gap-1 ${testResult.ok ? 'text-emerald-400' : 'text-rose-400'}`}>
            {testResult.ok ? <CheckCircle2 className="w-3 h-3" /> : <XCircle className="w-3 h-3" />}
            {testResult.message}
          </span>
        )}
      </div>

      <div className="flex gap-2 pt-2">
        <button
          onClick={onCancel}
          className="flex-1 px-4 py-2 bg-bg-surface border border-border rounded-xl text-[11px] font-bold"
        >
          Cancelar
        </button>
        <button
          onClick={onSave}
          disabled={!validDraft || saving}
          className="flex-1 px-4 py-2 bg-accent-amethyst hover:bg-accent-amethyst/90 disabled:opacity-30 text-white rounded-xl text-[11px] font-black uppercase tracking-widest"
        >
          {saving ? 'Salvando…' : (isUpdate ? 'Atualizar' : 'Conectar')}
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
    <div className="bg-amber-500/5 border border-amber-500/30 rounded-2xl p-4 space-y-3">
      <h4 className="text-sm font-black flex items-center gap-2 text-amber-300">
        <Webhook className="w-4 h-4" />
        Configure o webhook na Meta agora
      </h4>
      <div className="space-y-2 text-[11px]">
        <div className="bg-bg-primary border border-border rounded-lg p-2">
          <div className="text-[9px] uppercase tracking-widest text-secondary mb-0.5">Callback URL</div>
          <div className="flex items-center justify-between gap-2">
            <code className="font-mono text-[11px] truncate">{data.webhook_url}</code>
            <button
              onClick={() => onCopy(data.webhook_url, 'URL copiada')}
              className="text-secondary hover:text-accent-amethyst"
            >
              <Copy className="w-3 h-3" />
            </button>
          </div>
        </div>
        <div className="bg-bg-primary border border-border rounded-lg p-2">
          <div className="text-[9px] uppercase tracking-widest text-secondary mb-0.5">Verify Token</div>
          <div className="flex items-center justify-between gap-2">
            <code className="font-mono text-[11px] truncate">{data.verify_token}</code>
            <button
              onClick={() => onCopy(data.verify_token, 'Token copiado')}
              className="text-secondary hover:text-accent-amethyst"
            >
              <Copy className="w-3 h-3" />
            </button>
          </div>
        </div>
      </div>
      <ol className="text-[11px] text-amber-100 space-y-1 list-decimal list-inside">
        {data.instructions.map((step, i) => <li key={i}>{step}</li>)}
      </ol>
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
    <div>
      <label className="text-[10px] font-black uppercase tracking-widest text-secondary block mb-1">
        {label}
      </label>
      {children}
      {hint && <div className="text-[10px] text-secondary mt-1">{hint}</div>}
    </div>
  );
}
