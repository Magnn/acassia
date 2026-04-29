import { useEffect, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  AlertTriangle,
  Building2,
  CheckCircle2,
  ExternalLink,
  QrCode,
  Save,
  Send,
  Server,
  ShieldCheck,
  XCircle,
} from 'lucide-react';
import {
  type ProviderMode,
  type WhatsAppConfig,
  whatsappApi,
} from '../api/whatsapp';
import { toast } from '../lib/toast';

interface ProviderMeta {
  id: ProviderMode;
  Icon: typeof ShieldCheck;
  title: string;
  subtitle: string;
  description: string;
  badge: string;
  badgeTone: string;
}

const EMPTY_CONFIG: WhatsAppConfig = {
  provider: 'meta_cloud',
  meta_cloud: { phone_number_id: '', waba_id: '', has_access_token: false },
  coex: { api_url: '', instance: '', has_api_key: false },
  evolution: { server_url: '', instance: '', has_api_key: false },
};

const PROVIDERS: ProviderMeta[] = [
  {
    id: 'meta_cloud',
    Icon: ShieldCheck,
    title: 'Meta Cloud (nativo)',
    subtitle: 'Direto da Meta, sem intermediário',
    description:
      'Você fornece phone_number_id, waba_id e access_token (System User token). Mais barato, mas exige conta Meta Business e App Review.',
    badge: 'oficial',
    badgeTone: 'bg-sibila-amethyst/20 text-sibila-amethyst border-sibila-amethyst/40',
  },
  {
    id: 'coex',
    Icon: Building2,
    title: 'Coex (BSP parceiro)',
    subtitle: 'Solução pronta via Business Solution Provider',
    description:
      'Coex repassa pra Cloud API. Você paga taxa adicional mas evita App Review e on-boarding direto na Meta.',
    badge: 'oficial · BSP',
    badgeTone: 'bg-sibila-ember/20 text-sibila-ember border-sibila-ember/40',
  },
  {
    id: 'evolution',
    Icon: Server,
    title: 'Evolution API (não oficial)',
    subtitle: 'WhatsApp Web por baixo, conexão via QR',
    description:
      'Open source, usa o app de celular como bridge. Mais barato, sem App Review, mas viola TOS do WhatsApp e pode banir o número. Use por conta e risco.',
    badge: 'risco · não oficial',
    badgeTone: 'bg-sibila-crimson/20 text-sibila-crimson border-sibila-crimson/40',
  },
];

export default function WhatsAppConnect() {
  const qc = useQueryClient();

  const { data: config, isLoading, error: configError } = useQuery({
    queryKey: ['whatsapp-config'],
    queryFn: whatsappApi.getConfig,
    retry: false,
  });

  const { data: status, refetch: refetchStatus } = useQuery({
    queryKey: ['whatsapp-status'],
    queryFn: whatsappApi.status,
    refetchInterval: 30000,
    retry: false,
  });

  const [selectedMode, setSelectedMode] = useState<ProviderMode>('meta_cloud');

  // Form local — separado do server pra permitir edição
  const [form, setForm] = useState<WhatsAppConfig | null>(null);
  // Segredos só são enviados se o user digitar — campos arrancam vazios
  const [secrets, setSecrets] = useState({
    access_token: '',
    coex_api_key: '',
    evolution_api_key: '',
  });
  const [testNumber, setTestNumber] = useState('');

  useEffect(() => {
    if (config) {
      setForm(config);
      setSelectedMode(config.provider);
    } else if (!isLoading && !form) {
      // Backend falhou (401/404/500) — inicializa form vazio pra permitir edição
      setForm(EMPTY_CONFIG);
    }
  }, [config, isLoading, form]);

  const saveMutation = useMutation({
    mutationFn: whatsappApi.saveConfig,
    onSuccess: () => {
      toast.success('Configuração salva.');
      setSecrets({ access_token: '', coex_api_key: '', evolution_api_key: '' });
      qc.invalidateQueries({ queryKey: ['whatsapp-config'] });
      refetchStatus();
    },
    onError: (e) => toast.error(`Falha: ${(e as Error).message}`),
  });

  const testMutation = useMutation({
    mutationFn: () => whatsappApi.test(testNumber),
    onSuccess: (res) => {
      if (res.ok) toast.success(`Mensagem de teste enviada${res.message_id ? ` (id: ${res.message_id})` : ''}.`);
      else toast.error(`Falha no teste: ${res.error || 'desconhecido'}`);
    },
    onError: (e) => toast.error(`Erro: ${(e as Error).message}`),
  });

  const handleSave = () => {
    if (!form) return;
    const patch: Parameters<typeof whatsappApi.saveConfig>[0] = {
      provider: selectedMode,
      meta_cloud: {
        phone_number_id: form.meta_cloud.phone_number_id,
        waba_id: form.meta_cloud.waba_id,
      },
      coex: {
        api_url: form.coex.api_url,
        instance: form.coex.instance,
      },
      evolution: {
        server_url: form.evolution.server_url,
        instance: form.evolution.instance,
      },
    };
    if (secrets.access_token) patch.meta_cloud!.access_token = secrets.access_token;
    if (secrets.coex_api_key) patch.coex!.api_key = secrets.coex_api_key;
    if (secrets.evolution_api_key) patch.evolution!.api_key = secrets.evolution_api_key;
    saveMutation.mutate(patch);
  };

  if (isLoading) {
    return <div className="p-12 text-sibila-smoke text-sm animate-pulse-soft">Lendo configuração…</div>;
  }
  if (!form) {
    return <div className="p-12 text-sibila-smoke text-sm">Inicializando…</div>;
  }

  return (
    <div className="px-8 py-10 max-w-5xl mx-auto">
      <div className="mb-8">
        <h2 className="font-display text-3xl text-sibila-moonlight tracking-tight mb-1">
          Conexão WhatsApp
        </h2>
        <p className="text-sm text-sibila-smoke">
          Escolha como o motor envia mensagens. Você pode alternar entre os
          provedores depois.
        </p>
      </div>

      {/* Erro de carregamento — provavelmente 401 (login) ou 404 (Flask sem reload) */}
      {configError && (
        <div className="mb-6 rounded-lg px-4 py-3 border bg-sibila-crimson/10 border-sibila-crimson/30 flex items-start gap-3">
          <AlertTriangle className="w-4 h-4 text-sibila-crimson mt-0.5 flex-shrink-0" />
          <div className="flex-1 text-sm">
            <div className="font-medium text-sibila-moonlight">
              Não consegui ler a config do servidor
            </div>
            <div className="text-xs text-sibila-fog mt-1">
              {(configError as Error).message}
            </div>
            <ul className="text-[11px] text-sibila-smoke mt-2 list-disc list-inside space-y-0.5">
              <li>
                Se for <strong>401</strong>: faça login em{' '}
                <a href="/saas/auth/login" className="text-sibila-amethyst hover:underline">
                  /saas/auth/login
                </a>
                .
              </li>
              <li>
                Se for <strong>404</strong>: reinicie o Flask para registrar o blueprint
                novo (<code className="text-sibila-fog">saas_whatsapp</code>).
              </li>
              <li>
                Se for <strong>500</strong>: cheque o log do Flask por exceções.
              </li>
            </ul>
            <p className="text-[11px] text-sibila-smoke mt-2">
              Você pode editar o formulário abaixo mesmo assim, mas o Salvar só funciona
              quando o backend estiver acessível.
            </p>
          </div>
        </div>
      )}

      {/* Status atual */}
      {status && (
        <div className={[
          'mb-8 rounded-lg px-4 py-3 border flex items-start gap-3',
          status.ok
            ? 'bg-sibila-sage/10 border-sibila-sage/30'
            : 'bg-sibila-crimson/10 border-sibila-crimson/30',
        ].join(' ')}>
          {status.ok ? (
            <CheckCircle2 className="w-4 h-4 text-sibila-sage mt-0.5 flex-shrink-0" />
          ) : (
            <AlertTriangle className="w-4 h-4 text-sibila-crimson mt-0.5 flex-shrink-0" />
          )}
          <div className="flex-1">
            <div className="text-sm font-medium text-sibila-moonlight">
              {status.ok ? 'Conexão pronta' : 'Conexão pendente'}
              <span className="text-sibila-smoke ml-2 text-xs">
                · {labelFor(status.mode)}
              </span>
            </div>
            {status.hint && (
              <div className="text-xs text-sibila-fog mt-1">{status.hint}</div>
            )}
            {status.connection_state && (
              <div className="text-[11px] text-sibila-smoke mt-1 font-mono">
                state: {status.connection_state}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Picker de modo */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mb-8">
        {PROVIDERS.map((p) => (
          <button
            key={p.id}
            onClick={() => setSelectedMode(p.id)}
            className={[
              'text-left rounded-lg border p-4 transition-all',
              selectedMode === p.id
                ? 'border-sibila-amethyst bg-sibila-veil/60 shadow-glow-amethyst'
                : 'border-sibila-mist bg-sibila-obsidian hover:border-sibila-stone',
            ].join(' ')}
          >
            <div className="flex items-start justify-between mb-2">
              <p.Icon
                className={`w-5 h-5 ${selectedMode === p.id ? 'text-sibila-amethyst' : 'text-sibila-fog'}`}
                strokeWidth={1.8}
              />
              <span className={`text-[10px] uppercase tracking-wider px-1.5 py-0.5 rounded border ${p.badgeTone}`}>
                {p.badge}
              </span>
            </div>
            <h3 className="font-display text-base text-sibila-moonlight leading-tight">
              {p.title}
            </h3>
            <div className="text-[11px] text-sibila-smoke mt-0.5 mb-2">{p.subtitle}</div>
            <p className="text-xs text-sibila-fog leading-relaxed">{p.description}</p>
          </button>
        ))}
      </div>

      {/* Form do provider selecionado */}
      <section className="bg-sibila-obsidian border border-sibila-mist rounded-lg p-5 shadow-inset-veil">
        <h3 className="font-display text-lg text-sibila-moonlight mb-4">
          Credenciais — {labelFor(selectedMode)}
        </h3>

        {selectedMode === 'meta_cloud' && (
          <div className="space-y-3">
            <FormField
              label="phone_number_id"
              hint="numérico, da Meta Business"
              value={form.meta_cloud.phone_number_id}
              onChange={(v) => setForm({ ...form, meta_cloud: { ...form.meta_cloud, phone_number_id: v } })}
              placeholder="106540152569312"
              mono
            />
            <FormField
              label="waba_id"
              hint="WhatsApp Business Account ID"
              value={form.meta_cloud.waba_id}
              onChange={(v) => setForm({ ...form, meta_cloud: { ...form.meta_cloud, waba_id: v } })}
              placeholder="103845942681542"
              mono
            />
            <SecretField
              label="access_token"
              hint={form.meta_cloud.has_access_token ? 'Token salvo · digite só pra trocar' : 'System User token (permanente)'}
              value={secrets.access_token}
              onChange={(v) => setSecrets({ ...secrets, access_token: v })}
              placeholder={form.meta_cloud.has_access_token ? '••••••••••••' : 'EAAxxx...'}
            />
            <a
              href="https://developers.facebook.com/docs/whatsapp/cloud-api/get-started"
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-1 text-xs text-sibila-amethyst hover:underline"
            >
              <ExternalLink className="w-3 h-3" />
              Documentação Meta Cloud API
            </a>
          </div>
        )}

        {selectedMode === 'coex' && (
          <div className="space-y-3">
            <div className="rounded border border-sibila-ember/30 bg-sibila-ember/5 px-3 py-2 text-xs text-sibila-fog">
              Coex é integração via parceiro BSP. As chaves variam por contrato — peça pra Coex
              o endpoint REST, instância e API key. Quando preenchido, o motor passa a usar Coex
              em vez da Meta direta.
            </div>
            <FormField
              label="api_url"
              hint="endpoint REST fornecido pela Coex"
              value={form.coex.api_url}
              onChange={(v) => setForm({ ...form, coex: { ...form.coex, api_url: v } })}
              placeholder="https://api.coex.cx/v1/messages"
              mono
            />
            <FormField
              label="instance"
              hint="identificador da instância Coex"
              value={form.coex.instance}
              onChange={(v) => setForm({ ...form, coex: { ...form.coex, instance: v } })}
              placeholder="prod-default"
              mono
            />
            <SecretField
              label="api_key"
              hint={form.coex.has_api_key ? 'Salva · digite só pra trocar' : 'Bearer token Coex'}
              value={secrets.coex_api_key}
              onChange={(v) => setSecrets({ ...secrets, coex_api_key: v })}
              placeholder={form.coex.has_api_key ? '••••••••••••' : 'cx_xxx...'}
            />
            <div className="rounded border border-sibila-mist bg-sibila-veil/40 px-3 py-2 text-[11px] text-sibila-smoke flex items-center gap-1.5">
              <AlertTriangle className="w-3 h-3 text-sibila-ember flex-shrink-0" />
              Stub — envio real é implementado quando você fornecer doc da Coex.
            </div>
          </div>
        )}

        {selectedMode === 'evolution' && (
          <div className="space-y-3">
            <div className="rounded border border-sibila-crimson/30 bg-sibila-crimson/5 px-3 py-2 text-xs text-sibila-fog">
              <strong className="text-sibila-crimson">Atenção:</strong> Evolution API conecta via
              QR como WhatsApp Web. Viola TOS do WhatsApp — números podem ser banidos. Use só em
              números de teste ou contas que aceitem o risco.
            </div>
            <FormField
              label="server_url"
              hint="URL base do servidor Evolution"
              value={form.evolution.server_url}
              onChange={(v) => setForm({ ...form, evolution: { ...form.evolution, server_url: v } })}
              placeholder="https://evo.example.com"
              mono
            />
            <FormField
              label="instance"
              hint="nome da instância nesse servidor"
              value={form.evolution.instance}
              onChange={(v) => setForm({ ...form, evolution: { ...form.evolution, instance: v } })}
              placeholder="cigana-prod"
              mono
            />
            <SecretField
              label="api_key"
              hint={form.evolution.has_api_key ? 'Salva · digite só pra trocar' : 'apikey global ou da instância'}
              value={secrets.evolution_api_key}
              onChange={(v) => setSecrets({ ...secrets, evolution_api_key: v })}
              placeholder={form.evolution.has_api_key ? '••••••••••••' : 'B6xxxx...'}
            />
            {selectedMode === 'evolution' && status?.mode === 'evolution' && status.connection_state !== 'open' && (
              <button
                type="button"
                onClick={async () => {
                  const r = await whatsappApi.qr();
                  if (r.ok && r.data) toast.info('QR disponível no console do servidor Evolution.');
                  else toast.error(r.error || 'Não foi possível buscar QR.');
                }}
                className="text-xs px-3 py-1.5 rounded border border-sibila-mist hover:border-sibila-amethyst flex items-center gap-1.5"
              >
                <QrCode className="w-3 h-3" />
                Gerar QR pra parear
              </button>
            )}
            <a
              href="https://doc.evolution-api.com"
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-1 text-xs text-sibila-amethyst hover:underline"
            >
              <ExternalLink className="w-3 h-3" />
              Documentação Evolution API
            </a>
          </div>
        )}

        <div className="mt-6 flex justify-end">
          <button
            onClick={handleSave}
            disabled={saveMutation.isPending}
            className="px-4 py-2 rounded-md bg-sibila-amethyst text-white text-sm hover:brightness-110 disabled:opacity-50 flex items-center gap-2"
          >
            <Save className="w-3.5 h-3.5" />
            {saveMutation.isPending ? 'Salvando…' : 'Salvar'}
          </button>
        </div>
      </section>

      {/* Teste de envio */}
      <section className="mt-6 bg-sibila-obsidian border border-sibila-mist rounded-lg p-5 shadow-inset-veil">
        <h3 className="font-display text-base text-sibila-moonlight mb-2">
          Testar conexão
        </h3>
        <p className="text-xs text-sibila-smoke mb-3">
          Manda uma mensagem de teste pro número informado usando o provider
          atualmente <strong className="text-sibila-fog">salvo</strong> (não a edição em curso).
          Use formato internacional sem espaços: 5511999999999.
        </p>
        <div className="flex gap-2">
          <input
            type="text"
            value={testNumber}
            onChange={(e) => setTestNumber(e.target.value)}
            placeholder="5511999999999"
            className="flex-1 rounded border border-sibila-mist bg-sibila-onyx px-3 py-1.5 text-sm text-sibila-moonlight font-mono focus:outline-none focus:border-sibila-amethyst"
          />
          <button
            onClick={() => {
              if (!testNumber.trim()) return toast.warning('Informe um número.');
              testMutation.mutate();
            }}
            disabled={testMutation.isPending}
            className="px-3 py-1.5 rounded-md bg-sibila-sage/30 border border-sibila-sage/50 text-sibila-sage text-sm hover:bg-sibila-sage/40 disabled:opacity-50 flex items-center gap-1.5"
          >
            <Send className="w-3.5 h-3.5" />
            {testMutation.isPending ? 'Enviando…' : 'Enviar teste'}
          </button>
        </div>
      </section>
    </div>
  );
}

function labelFor(mode: ProviderMode): string {
  return PROVIDERS.find((p) => p.id === mode)?.title ?? mode;
}

function FormField({
  label,
  hint,
  value,
  onChange,
  placeholder,
  mono,
}: {
  label: string;
  hint?: string;
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
  mono?: boolean;
}) {
  return (
    <label className="block">
      <div className="flex items-baseline justify-between mb-1">
        <span className="text-[11px] uppercase tracking-wider-2 text-sibila-fog">{label}</span>
        {hint && <span className="text-[10px] text-sibila-smoke">{hint}</span>}
      </div>
      <input
        type="text"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className={`w-full rounded border border-sibila-mist bg-sibila-onyx px-3 py-1.5 text-sm text-sibila-moonlight placeholder:text-sibila-smoke focus:outline-none focus:border-sibila-amethyst ${mono ? 'font-mono' : ''}`}
      />
    </label>
  );
}

function SecretField({
  label,
  hint,
  value,
  onChange,
  placeholder,
}: {
  label: string;
  hint?: string;
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
}) {
  return (
    <label className="block">
      <div className="flex items-baseline justify-between mb-1">
        <span className="text-[11px] uppercase tracking-wider-2 text-sibila-fog">{label}</span>
        {hint && <span className="text-[10px] text-sibila-smoke">{hint}</span>}
      </div>
      <input
        type="password"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        autoComplete="new-password"
        className="w-full rounded border border-sibila-mist bg-sibila-onyx px-3 py-1.5 text-sm text-sibila-moonlight placeholder:text-sibila-smoke focus:outline-none focus:border-sibila-amethyst font-mono"
      />
    </label>
  );
}

// Marca XCircle como usado para evitar warning do TS noUnusedLocals
void XCircle;
