import { useEffect, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  AlertTriangle,
  ArrowLeft,
  Building2,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  ExternalLink,
  Pencil,
  Phone,
  Plus,
  PowerOff,
  QrCode,
  Save,
  Send,
  Server,
  ShieldCheck,
  X,
} from 'lucide-react';
import {
  type ProviderMode,
  type WhatsAppConfig,
  whatsappApi,
} from '../../api/whatsapp';
import { toast } from '../../lib/toast';

const EMPTY_CONFIG: WhatsAppConfig = {
  provider: 'meta_cloud',
  meta_cloud: { phone_number_id: '', waba_id: '', has_access_token: false },
  coex: { api_url: '', instance: '', has_api_key: false },
  evolution: { server_url: '', instance: '', has_api_key: false },
};

interface ProviderMeta {
  id: ProviderMode;
  Icon: typeof ShieldCheck;
  title: string;
  badge: string;
  badgeTone: string;
  description: string;
}

const PROVIDERS: ProviderMeta[] = [
  {
    id: 'meta_cloud',
    Icon: ShieldCheck,
    title: 'Meta Cloud (nativo)',
    badge: 'oficial',
    badgeTone: 'bg-sibila-amethyst/20 text-sibila-amethyst border-sibila-amethyst/40',
    description: 'API oficial Meta. Voc├¬ fornece phone_number_id, waba_id e access_token.',
  },
  {
    id: 'coex',
    Icon: Building2,
    title: 'Coex (BSP parceiro)',
    badge: 'oficial ┬À BSP',
    badgeTone: 'bg-sibila-ember/20 text-sibila-ember border-sibila-ember/40',
    description: 'Integra├º├úo via BSP ÔÇö Coex repassa pra Cloud API. Pague taxa, evite App Review.',
  },
  {
    id: 'evolution',
    Icon: Server,
    title: 'Evolution (n├úo oficial)',
    badge: 'risco ┬À n├úo oficial',
    badgeTone: 'bg-sibila-crimson/20 text-sibila-crimson border-sibila-crimson/40',
    description: 'WhatsApp Web por baixo, conex├úo por QR. Mais barato; pode ser banido.',
  },
];

export default function Devices() {
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

  const [form, setForm] = useState<WhatsAppConfig | null>(null);
  const [showAddModal, setShowAddModal] = useState(false);
  const [showQrModal, setShowQrModal] = useState(false);
  const [showDetails, setShowDetails] = useState(false);
  const [editingNickname, setEditingNickname] = useState(false);
  const [nickname, setNickname] = useState('');

  useEffect(() => {
    if (config) {
      setForm(config);
    } else if (!isLoading && !form) {
      setForm(EMPTY_CONFIG);
    }
  }, [config, isLoading, form]);

  // Carrega nickname salvo do localStorage por tenant (UX simples).
  useEffect(() => {
    const saved = localStorage.getItem('sibila.device.nickname') || '';
    setNickname(saved);
  }, []);

  const saveMutation = useMutation({
    mutationFn: whatsappApi.saveConfig,
    onSuccess: () => {
      toast.success('Configura├º├úo salva.');
      setShowAddModal(false);
      qc.invalidateQueries({ queryKey: ['whatsapp-config'] });
      refetchStatus();
    },
    onError: (e) => toast.error(`Falha: ${(e as Error).message}`),
  });

  const isConfigured = !!(
    config &&
    ((config.provider === 'meta_cloud' && config.meta_cloud.phone_number_id) ||
      (config.provider === 'coex' && config.coex.api_url) ||
      (config.provider === 'evolution' && config.evolution.server_url))
  );

  const activeProviderMeta = PROVIDERS.find((p) => p.id === (config?.provider ?? 'meta_cloud'))!;

  const handleSaveNickname = () => {
    localStorage.setItem('sibila.device.nickname', nickname.trim());
    setEditingNickname(false);
    toast.success('Apelido salvo.');
  };

  const handleDisconnect = () => {
    if (!confirm('Desconectar este dispositivo? As credenciais salvas permanecem; apenas o provider volta ao padr├úo.')) return;
    whatsappApi
      .saveConfig({
        meta_cloud: { phone_number_id: '', waba_id: '', access_token: '' },
        coex: { api_url: '', instance: '', api_key: '' },
        evolution: { server_url: '', instance: '', api_key: '' },
      })
      .then(() => {
        toast.success('Dispositivo desconectado.');
        qc.invalidateQueries({ queryKey: ['whatsapp-config'] });
        refetchStatus();
      })
      .catch((e) => toast.error((e as Error).message));
  };

  return (
    <div className="px-8 py-8 max-w-6xl mx-auto">
      <div className="flex items-baseline justify-between mb-2">
        <h2 className="font-display text-2xl text-sibila-moonlight">
          Meus dispositivos {isConfigured ? '(1/1)' : '(0/1)'}
        </h2>
      </div>
      <p className="flex items-center gap-1.5 text-sm text-sibila-smoke mb-6">
        <Phone className="w-3.5 h-3.5" />
        Minhas conex├Áes com dispositivos WhatsApp.
      </p>

      {/* Erro de carregamento */}
      {configError && (
        <ErrorBanner error={configError as Error} />
      )}

      {/* Plano atingido (futuro: viria do backend) */}
      {isConfigured && (
        <div className="mb-6 rounded-lg bg-sibila-rose/15 border border-sibila-rose/30 px-4 py-2.5 text-sm text-sibila-moonlight text-center">
          Ôôÿ Voc├¬ atingiu o n├║mero m├íximo de dispositivos no plano atual.{' '}
          <a href="/saas/billing" className="underline hover:text-sibila-ember">
            Atualize seu plano
          </a>
          .
        </div>
      )}

      {/* Tabs Sess├Áes */}
      <div className="flex items-center justify-end gap-6 border-b border-sibila-mist mb-5">
        <button className="text-sm text-sibila-amethyst border-b-2 border-sibila-amethyst pb-2 -mb-px font-medium">
          Sess├Áes Ativas
        </button>
        <button className="text-sm text-sibila-smoke pb-2 -mb-px hover:text-sibila-fog">
          Sess├Áes Inativas
        </button>
      </div>

      {/* Grade de cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        {/* Card "Conectar novo" ÔÇö s├│ aparece se N├âO configurado (1/1 limite) */}
        {!isConfigured && (
          <button
            onClick={() => setShowAddModal(true)}
            className="rounded-xl border-2 border-dashed border-sibila-mist bg-sibila-obsidian/40 p-8 flex flex-col items-center justify-center gap-3 text-sibila-smoke hover:border-sibila-amethyst hover:text-sibila-moonlight transition-all min-h-[220px]"
          >
            <span className="w-14 h-14 rounded-full bg-sibila-veil flex items-center justify-center">
              <Phone className="w-6 h-6 text-sibila-amethyst" strokeWidth={1.5} />
            </span>
            <div className="text-center">
              <div className="text-sm font-medium text-sibila-moonlight">
                Conectar um novo dispositivo
              </div>
              <div className="text-[11px] mt-1">Clique para adicionar um novo whatsapp</div>
            </div>
          </button>
        )}

        {/* Card de dispositivo conectado/aguardando */}
        {isConfigured && config && status && (
          <div
            className={[
              'rounded-xl bg-sibila-obsidian overflow-hidden shadow-inset-veil',
              status.ok
                ? 'border border-sibila-mist'
                : 'border-2 border-sibila-crimson/60',
            ].join(' ')}
          >
            {/* Header com logo do provider + pill status + nickname */}
            <div className="px-4 py-4 flex items-start gap-3">
              <ProviderLogo provider={config.provider} state={status.ok ? 'connected' : 'pending'} />
              <div className="flex-1 min-w-0">
                {status.ok ? (
                  <>
                    <div className="text-[10px] uppercase tracking-wider-2 text-sibila-smoke mb-0.5">
                      {activeProviderMeta.badge}
                    </div>
                    <div className="flex items-center gap-2">
                      {phoneFromConfig(config) && (
                        <span className="inline-block px-2 py-0.5 rounded bg-sibila-amethyst/15 text-sibila-amethyst text-[11px] font-mono">
                          +{phoneFromConfig(config)}
                        </span>
                      )}
                    </div>
                  </>
                ) : (
                  <span className="inline-block px-2 py-0.5 rounded bg-sibila-rose/15 text-sibila-rose text-[11px] font-medium">
                    Aguardando Conex├úo
                  </span>
                )}
                <div className="mt-2 flex items-center gap-2 group">
                  {editingNickname ? (
                    <input
                      autoFocus
                      value={nickname}
                      onChange={(e) => setNickname(e.target.value)}
                      onKeyDown={(e) => e.key === 'Enter' && handleSaveNickname()}
                      onBlur={handleSaveNickname}
                      placeholder="Apelido (ex.: Esmeralda Cigana)"
                      className="bg-sibila-veil border border-sibila-mist rounded px-2 py-0.5 text-sm text-sibila-moonlight focus:outline-none focus:border-sibila-amethyst flex-1"
                    />
                  ) : (
                    <>
                      <span className="text-sm text-sibila-moonlight">
                        {nickname || (status.ok ? 'Dispositivo principal' : 'Novo Dispositivo')}
                      </span>
                      <button
                        onClick={() => setEditingNickname(true)}
                        className="opacity-0 group-hover:opacity-100 text-sibila-smoke hover:text-sibila-amethyst transition-opacity"
                      >
                        <Pencil className="w-3 h-3" />
                      </button>
                    </>
                  )}
                </div>
              </div>
            </div>

            {/* Status banner / Tentativas */}
            {status.ok ? (
              <div className="px-4 py-2 text-center text-sm font-medium bg-sibila-amethyst text-white">
                <CheckCircle2 className="w-3.5 h-3.5 inline mr-1.5" />
                Conex├úo realizada com sucesso!
              </div>
            ) : (
              <div className="px-4 py-2 text-center text-sm font-medium border-y border-sibila-mist text-sibila-fog">
                Tentativas de conex├úo <strong className="text-sibila-moonlight">3</strong> de <strong className="text-sibila-moonlight">3</strong> .
              </div>
            )}

            {/* Mostrar Detalhes */}
            <button
              onClick={() => setShowDetails((v) => !v)}
              className="w-full px-4 py-2.5 text-sm text-sibila-fog hover:bg-sibila-veil/40 border-t border-sibila-mist flex items-center justify-center gap-1.5"
            >
              {showDetails ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
              Mostrar Detalhes
            </button>
            {showDetails && (
              <div className="px-4 py-3 bg-sibila-veil/30 border-t border-sibila-mist text-xs space-y-1.5">
                <DetailRow label="Provider" value={activeProviderMeta.title} />
                {config.provider === 'meta_cloud' && (
                  <>
                    <DetailRow label="phone_number_id" value={config.meta_cloud.phone_number_id || 'ÔÇö'} mono />
                    <DetailRow label="waba_id" value={config.meta_cloud.waba_id || 'ÔÇö'} mono />
                    <DetailRow label="access_token" value={config.meta_cloud.has_access_token ? 'ÔÇóÔÇóÔÇóÔÇóÔÇóÔÇóÔÇóÔÇó' : 'n├úo configurado'} />
                  </>
                )}
                {config.provider === 'coex' && (
                  <>
                    <DetailRow label="api_url" value={config.coex.api_url || 'ÔÇö'} mono />
                    <DetailRow label="instance" value={config.coex.instance || 'ÔÇö'} mono />
                    <DetailRow label="api_key" value={config.coex.has_api_key ? 'ÔÇóÔÇóÔÇóÔÇóÔÇóÔÇóÔÇóÔÇó' : 'n├úo configurado'} />
                  </>
                )}
                {config.provider === 'evolution' && (
                  <>
                    <DetailRow label="server_url" value={config.evolution.server_url || 'ÔÇö'} mono />
                    <DetailRow label="instance" value={config.evolution.instance || 'ÔÇö'} mono />
                    <DetailRow label="api_key" value={config.evolution.has_api_key ? 'ÔÇóÔÇóÔÇóÔÇóÔÇóÔÇóÔÇóÔÇó' : 'n├úo configurado'} />
                    {status?.connection_state && (
                      <DetailRow label="connection_state" value={status.connection_state} />
                    )}
                  </>
                )}
                <div className="pt-2 mt-2 border-t border-sibila-mist/60">
                  <button
                    onClick={() => setShowAddModal(true)}
                    className="text-xs text-sibila-amethyst hover:underline"
                  >
                    Editar credenciais
                  </button>
                </div>
              </div>
            )}

            {/* Gerar QR Code (s├│ Evolution n├úo conectado) */}
            {!status.ok && config.provider === 'evolution' && (
              <button
                onClick={() => setShowQrModal(true)}
                className="w-full px-4 py-2.5 text-sm text-sibila-amethyst hover:bg-sibila-amethyst/10 border-t border-sibila-mist flex items-center justify-center gap-1.5 transition-colors font-medium"
              >
                <QrCode className="w-3.5 h-3.5" />
                Gerar QR Code
              </button>
            )}

            {/* Desconectar */}
            <button
              onClick={handleDisconnect}
              className="w-full px-4 py-2.5 text-sm text-sibila-crimson hover:bg-sibila-crimson/10 border-t border-sibila-mist flex items-center justify-center gap-1.5 transition-colors"
            >
              <PowerOff className="w-3.5 h-3.5" />
              Desconectar
            </button>
          </div>
        )}

        {/* Placeholder vazio quando N├âO configurado para preencher a grid de 2 colunas */}
        {!isConfigured && (
          <div className="hidden md:block rounded-xl border border-sibila-mist/50 bg-sibila-obsidian/20 min-h-[220px]" />
        )}
      </div>

      {/* Modal de configura├º├úo */}
      {showAddModal && form && (
        <ConfigModal
          form={form}
          setForm={setForm}
          onClose={() => setShowAddModal(false)}
          onSave={(patch) => saveMutation.mutate(patch)}
          saving={saveMutation.isPending}
        />
      )}

      {/* Modal QR ÔÇö s├│ pra Evolution n├úo conectado */}
      {showQrModal && (
        <QrModal onClose={() => setShowQrModal(false)} onPaired={() => {
          setShowQrModal(false);
          refetchStatus();
        }} />
      )}
    </div>
  );
}

// ÔöÇÔöÇ Subcomponents ÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇ

function ProviderLogo({
  provider,
  state = 'connected',
}: {
  provider: ProviderMode;
  state?: 'connected' | 'pending';
}) {
  const meta = PROVIDERS.find((p) => p.id === provider)!;
  // Estado pendente: usa cor de Evolution (esmeralda) com Plus circle pra indicar "novo"
  const cls =
    state === 'pending'
      ? 'bg-emerald-500/10 border-emerald-500/30'
      : 'bg-sibila-veil border-sibila-mist';
  const iconColor = state === 'pending' ? 'text-emerald-500' : 'text-sibila-amethyst';
  return (
    <span className={`relative w-12 h-12 rounded-lg border flex items-center justify-center flex-shrink-0 ${cls}`}>
      <meta.Icon className={`w-5 h-5 ${iconColor}`} strokeWidth={1.6} />
      {state === 'pending' && (
        <span className="absolute -top-1 -right-1 w-4 h-4 rounded-full bg-emerald-500 border-2 border-sibila-obsidian flex items-center justify-center">
          <Plus className="w-2.5 h-2.5 text-white" strokeWidth={3} />
        </span>
      )}
    </span>
  );
}

function phoneFromConfig(c: WhatsAppConfig): string {
  // Meta Cloud n├úo tem o n├║mero direto (s├│ phone_number_id), ent├úo mostra o ID
  if (c.provider === 'meta_cloud') return c.meta_cloud.phone_number_id;
  if (c.provider === 'coex') return c.coex.instance;
  if (c.provider === 'evolution') return c.evolution.instance;
  return '';
}

function DetailRow({ label, value, mono }: { label: string; value: string; mono?: boolean }) {
  return (
    <div className="grid grid-cols-[120px,1fr] gap-2">
      <span className="text-sibila-smoke">{label}</span>
      <span
        className={`text-sibila-fog break-all ${mono ? 'font-mono text-[11px]' : ''}`}
      >
        {value}
      </span>
    </div>
  );
}

function ErrorBanner({ error }: { error: Error }) {
  return (
    <div className="mb-6 rounded-lg px-4 py-3 border bg-sibila-crimson/10 border-sibila-crimson/30 flex items-start gap-3">
      <AlertTriangle className="w-4 h-4 text-sibila-crimson mt-0.5 flex-shrink-0" />
      <div className="flex-1 text-sm">
        <div className="font-medium text-sibila-moonlight">
          N├úo consegui ler a config do servidor
        </div>
        <div className="text-xs text-sibila-fog mt-1">{error.message}</div>
        <ul className="text-[11px] text-sibila-smoke mt-2 list-disc list-inside space-y-0.5">
          <li><strong>401</strong>: fa├ºa login em <a className="text-sibila-amethyst hover:underline" href="/saas/login">/saas/login</a></li>
          <li><strong>404</strong>: reinicie o Flask (blueprint <code>saas_whatsapp</code> novo)</li>
          <li><strong>500</strong>: cheque o log do Flask</li>
        </ul>
      </div>
    </div>
  );
}

// ÔöÇÔöÇ Modal de configura├º├úo ÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇ

function ConfigModal({
  form,
  setForm,
  onClose,
  onSave,
  saving,
}: {
  form: WhatsAppConfig;
  setForm: (f: WhatsAppConfig) => void;
  onClose: () => void;
  onSave: (patch: Parameters<typeof whatsappApi.saveConfig>[0]) => void;
  saving: boolean;
}) {
  // Step 1: type picker (compacto, estilo Lailla)
  // Step 2: form contextual do provider escolhido
  const [step, setStep] = useState<'type' | 'form'>(form.provider && (form.meta_cloud.phone_number_id || form.coex.api_url || form.evolution.server_url) ? 'form' : 'type');
  const [mode, setMode] = useState<ProviderMode>(form.provider);
  const [secrets, setSecrets] = useState({
    access_token: '',
    coex_api_key: '',
    evolution_api_key: '',
  });
  const [testNumber, setTestNumber] = useState('');

  const testMutation = useMutation({
    mutationFn: () => whatsappApi.test(testNumber),
    onSuccess: (r) => {
      if (r.ok) toast.success(`Mensagem teste enviada${r.message_id ? ` (id: ${r.message_id})` : ''}.`);
      else toast.error(`Falha no teste: ${r.error || 'desconhecido'}`);
    },
    onError: (e) => toast.error((e as Error).message),
  });

  const handleSave = () => {
    const patch: Parameters<typeof whatsappApi.saveConfig>[0] = {
      provider: mode,
      meta_cloud: {
        phone_number_id: form.meta_cloud.phone_number_id,
        waba_id: form.meta_cloud.waba_id,
      },
      coex: { api_url: form.coex.api_url, instance: form.coex.instance },
      evolution: { server_url: form.evolution.server_url, instance: form.evolution.instance },
    };
    if (secrets.access_token) patch.meta_cloud!.access_token = secrets.access_token;
    if (secrets.coex_api_key) patch.coex!.api_key = secrets.coex_api_key;
    if (secrets.evolution_api_key) patch.evolution!.api_key = secrets.evolution_api_key;
    onSave(patch);
  };

  // ÔöÇÔöÇ Step 1: type picker ÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇ
  if (step === 'type') {
    return (
      <div
        className="fixed inset-0 z-[100] bg-black/60 backdrop-blur-sm flex items-center justify-center p-4"
        onClick={onClose}
      >
        <div
          onClick={(e) => e.stopPropagation()}
          className="bg-white text-slate-800 rounded-2xl shadow-2xl max-w-md w-full overflow-hidden"
        >
          <header className="flex items-center justify-between px-5 py-3 bg-sibila-amethyst text-white">
            <h3 className="font-display text-base">Escolha o tipo de conex├úo</h3>
            <button
              onClick={onClose}
              className="w-7 h-7 rounded-full bg-white/95 hover:bg-white text-slate-700 flex items-center justify-center transition-colors"
              title="Fechar"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          </header>
          <ul className="p-4 space-y-3">
            {PROVIDERS.map((p) => (
              <li key={p.id}>
                <button
                  onClick={() => {
                    setMode(p.id);
                    setStep('form');
                  }}
                  className={[
                    'w-full text-left rounded-xl border-2 px-4 py-3.5 flex items-center gap-3 transition-all',
                    mode === p.id
                      ? 'border-sibila-amethyst shadow-md'
                      : 'border-slate-200 hover:border-sibila-amethyst/50 hover:shadow-sm',
                  ].join(' ')}
                >
                  <span
                    className={[
                      'w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0',
                      p.id === 'meta_cloud' ? 'bg-blue-50 text-blue-600' :
                      p.id === 'coex' ? 'bg-amber-50 text-amber-600' :
                      'bg-emerald-50 text-emerald-600',
                    ].join(' ')}
                  >
                    <p.Icon className="w-5 h-5" strokeWidth={1.8} />
                  </span>
                  <div className="flex-1 min-w-0">
                    <div className="text-sm font-semibold text-slate-800">
                      {modalTitleFor(p.id)}
                    </div>
                    <div className="text-[11px] text-slate-500 mt-0.5">
                      {modalSubtitleFor(p.id)}
                    </div>
                  </div>
                </button>
              </li>
            ))}
          </ul>
        </div>
      </div>
    );
  }

  // ÔöÇÔöÇ Step 2: form ÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇ
  return (
    <div
      className="fixed inset-0 z-[100] bg-black/60 backdrop-blur-sm flex items-center justify-center p-4"
      onClick={onClose}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        className="bg-sibila-obsidian border border-sibila-mist rounded-xl shadow-2xl max-w-2xl w-full max-h-[90vh] overflow-hidden flex flex-col"
      >
        <header className="flex items-center justify-between px-6 py-4 border-b border-sibila-mist flex-shrink-0">
          <div className="flex items-center gap-3">
            <button
              onClick={() => setStep('type')}
              className="text-sibila-fog hover:text-sibila-moonlight p-1 rounded hover:bg-sibila-veil"
              title="Voltar"
            >
              <ArrowLeft className="w-4 h-4" />
            </button>
            <div>
              <h3 className="font-display text-lg text-sibila-moonlight">
                {modalTitleFor(mode)}
              </h3>
              <p className="text-[11px] text-sibila-smoke mt-0.5">
                {modalSubtitleFor(mode)}
              </p>
            </div>
          </div>
          <button onClick={onClose} className="text-sibila-fog hover:text-sibila-moonlight p-1">
            <X className="w-4 h-4" />
          </button>
        </header>

        <div className="overflow-y-auto px-6 py-5 space-y-5">
          {/* Form contextual */}
          {mode === 'meta_cloud' && (
            <div className="space-y-3">
              <Field
                label="phone_number_id"
                hint="num├®rico, da Meta Business"
                value={form.meta_cloud.phone_number_id}
                onChange={(v) => setForm({ ...form, meta_cloud: { ...form.meta_cloud, phone_number_id: v } })}
                placeholder="106540152569312"
                mono
              />
              <Field
                label="waba_id"
                hint="WhatsApp Business Account ID"
                value={form.meta_cloud.waba_id}
                onChange={(v) => setForm({ ...form, meta_cloud: { ...form.meta_cloud, waba_id: v } })}
                placeholder="103845942681542"
                mono
              />
              <Secret
                label="access_token"
                hint={form.meta_cloud.has_access_token ? 'Salvo ┬À digite s├│ pra trocar' : 'System User token (permanente)'}
                value={secrets.access_token}
                onChange={(v) => setSecrets({ ...secrets, access_token: v })}
                placeholder={form.meta_cloud.has_access_token ? 'ÔÇóÔÇóÔÇóÔÇóÔÇóÔÇóÔÇóÔÇóÔÇóÔÇóÔÇóÔÇó' : 'EAAxxx...'}
              />
              <a
                href="https://developers.facebook.com/docs/whatsapp/cloud-api/get-started"
                target="_blank" rel="noreferrer"
                className="inline-flex items-center gap-1 text-xs text-sibila-amethyst hover:underline"
              >
                <ExternalLink className="w-3 h-3" />
                Doc Meta Cloud API
              </a>
            </div>
          )}

          {mode === 'coex' && (
            <div className="space-y-3">
              <div className="rounded border border-sibila-ember/30 bg-sibila-ember/5 px-3 py-2 text-[11px] text-sibila-fog">
                Coex ├® stub estrutural. Forne├ºa as 3 chaves abaixo; o envio real
                fica pendente at├® voc├¬ passar a doc oficial Coex.
              </div>
              <Field
                label="api_url"
                value={form.coex.api_url}
                onChange={(v) => setForm({ ...form, coex: { ...form.coex, api_url: v } })}
                placeholder="https://api.coex.cx/v1/messages"
                mono
              />
              <Field
                label="instance"
                value={form.coex.instance}
                onChange={(v) => setForm({ ...form, coex: { ...form.coex, instance: v } })}
                placeholder="prod-default"
                mono
              />
              <Secret
                label="api_key"
                hint={form.coex.has_api_key ? 'Salva ┬À digite s├│ pra trocar' : ''}
                value={secrets.coex_api_key}
                onChange={(v) => setSecrets({ ...secrets, coex_api_key: v })}
                placeholder={form.coex.has_api_key ? 'ÔÇóÔÇóÔÇóÔÇóÔÇóÔÇóÔÇóÔÇóÔÇóÔÇóÔÇóÔÇó' : 'cx_xxx...'}
              />
            </div>
          )}

          {mode === 'evolution' && (
            <div className="space-y-3">
              <div className="rounded border border-sibila-crimson/30 bg-sibila-crimson/5 px-3 py-2 text-[11px] text-sibila-fog">
                <strong className="text-sibila-crimson">Aten├º├úo:</strong> Evolution viola TOS do WhatsApp ÔÇö n├║meros podem ser banidos. Use s├│ em testes.
              </div>
              <Field
                label="server_url"
                value={form.evolution.server_url}
                onChange={(v) => setForm({ ...form, evolution: { ...form.evolution, server_url: v } })}
                placeholder="https://evo.example.com"
                mono
              />
              <Field
                label="instance"
                value={form.evolution.instance}
                onChange={(v) => setForm({ ...form, evolution: { ...form.evolution, instance: v } })}
                placeholder="cigana-prod"
                mono
              />
              <Secret
                label="api_key"
                hint={form.evolution.has_api_key ? 'Salva ┬À digite s├│ pra trocar' : ''}
                value={secrets.evolution_api_key}
                onChange={(v) => setSecrets({ ...secrets, evolution_api_key: v })}
                placeholder={form.evolution.has_api_key ? 'ÔÇóÔÇóÔÇóÔÇóÔÇóÔÇóÔÇóÔÇóÔÇóÔÇóÔÇóÔÇó' : 'B6xxxx...'}
              />
            </div>
          )}

          {/* Test send */}
          <div className="border-t border-sibila-mist pt-4">
            <div className="text-[11px] uppercase tracking-wider-2 text-sibila-fog mb-2">
              Testar envio
            </div>
            <div className="flex gap-2">
              <input
                value={testNumber}
                onChange={(e) => setTestNumber(e.target.value)}
                placeholder="5511999999999"
                className="flex-1 rounded border border-sibila-mist bg-sibila-onyx px-3 py-1.5 text-sm font-mono text-sibila-moonlight focus:outline-none focus:border-sibila-amethyst"
              />
              <button
                onClick={() => {
                  if (!testNumber.trim()) return toast.warning('Informe um n├║mero.');
                  testMutation.mutate();
                }}
                disabled={testMutation.isPending}
                className="px-3 py-1.5 rounded bg-sibila-sage/30 border border-sibila-sage/50 text-sibila-sage text-sm hover:bg-sibila-sage/40 disabled:opacity-50 flex items-center gap-1.5"
              >
                <Send className="w-3.5 h-3.5" />
                {testMutation.isPending ? 'ÔÇª' : 'Testar'}
              </button>
            </div>
            <p className="text-[10px] text-sibila-smoke mt-1">
              Usa o provider <strong>j├í salvo</strong> ÔÇö salve antes de testar credenciais novas.
            </p>
          </div>
        </div>

        <footer className="border-t border-sibila-mist px-6 py-3 flex items-center justify-between flex-shrink-0">
          <button onClick={onClose} className="text-sm text-sibila-fog hover:text-sibila-moonlight px-3 py-1.5">
            Cancelar
          </button>
          <button
            onClick={handleSave}
            disabled={saving}
            className="flex items-center gap-2 px-4 py-1.5 rounded bg-sibila-amethyst text-white text-sm hover:brightness-110 disabled:opacity-50"
          >
            {saving ? 'ÔÇª' : <><Save className="w-3.5 h-3.5" /> Salvar</>}
          </button>
        </footer>
      </div>
    </div>
  );
}

function Field({
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

function Secret({
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
        className="w-full rounded border border-sibila-mist bg-sibila-onyx px-3 py-1.5 text-sm font-mono text-sibila-moonlight placeholder:text-sibila-smoke focus:outline-none focus:border-sibila-amethyst"
      />
    </label>
  );
}

// ÔöÇÔöÇ QR Modal ÔÇö pareamento Evolution (estilo Lailla) ÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇ

function QrModal({
  onClose,
  onPaired,
}: {
  onClose: () => void;
  onPaired: () => void;
}) {
  const { data, isLoading, error, refetch, isFetching } = useQuery({
    queryKey: ['whatsapp-qr'],
    queryFn: whatsappApi.qr,
    retry: false,
    refetchInterval: 3000, // re-busca cada 3s ÔÇö Evolution rotaciona o QR
  });

  // Detecta estado paired via status; se virar 'open', avisa parent
  const { data: status } = useQuery({
    queryKey: ['whatsapp-status'],
    queryFn: whatsappApi.status,
    retry: false,
    refetchInterval: 2500,
  });

  useEffect(() => {
    if (status?.connection_state === 'open') {
      onPaired();
    }
  }, [status, onPaired]);

  // Extrai QR do payload Evolution v2: { base64?, code?, pairingCode? }
  const qrPayload = (data?.data ?? {}) as Record<string, unknown>;
  const qrBase64 = typeof qrPayload.base64 === 'string' ? qrPayload.base64 : null;
  const qrCode = typeof qrPayload.code === 'string' ? qrPayload.code : null;
  const pairingCode = typeof qrPayload.pairingCode === 'string' ? qrPayload.pairingCode : null;

  return (
    <div
      className="fixed inset-0 z-[100] bg-black/60 backdrop-blur-sm flex items-center justify-center p-4"
      onClick={onClose}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        className="bg-white text-slate-800 rounded-2xl shadow-2xl max-w-2xl w-full overflow-hidden"
      >
        <header className="flex items-center justify-between px-5 py-3 bg-sibila-amethyst text-white">
          <h3 className="font-display text-base">Conectar com n├║mero de telefone</h3>
          <button
            onClick={onClose}
            className="w-7 h-7 rounded-full bg-white/95 hover:bg-white text-slate-700 flex items-center justify-center transition-colors"
            title="Fechar"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        </header>

        <div className="p-6 grid grid-cols-1 md:grid-cols-[1fr,auto] gap-6 items-start">
          {/* Instru├º├Áes */}
          <div className="space-y-3">
            <h4 className="font-display text-lg text-slate-800">Leitura de QR Code</h4>
            <ol className="space-y-2 text-sm text-slate-600">
              <li>Abra o WhatsApp no seu celular.</li>
              <li>
                Toque em <strong>Mais op├º├Áes</strong> ou <strong>Configura├º├Áes</strong> e
                selecione <strong>Aparelhos conectados</strong>.
              </li>
              <li>Toque em <strong>Conectar um aparelho</strong>.</li>
              <li>
                Aponte seu celular para esta tela para capturar o QR code e aguarde a
                conex├úo ser conclu├¡da.
              </li>
            </ol>

            {pairingCode && (
              <div className="rounded-lg bg-slate-50 border border-slate-200 px-3 py-2 mt-3">
                <div className="text-[10px] uppercase tracking-wider text-slate-500 mb-1">
                  C├│digo de pareamento alternativo
                </div>
                <code className="font-mono text-lg font-semibold text-slate-800 tracking-wider">
                  {pairingCode}
                </code>
                <p className="text-[11px] text-slate-500 mt-1">
                  Use no WhatsApp em "Conectar com n├║mero de telefone".
                </p>
              </div>
            )}

            {error && (
              <div className="rounded-lg bg-red-50 border border-red-200 px-3 py-2 text-sm text-red-700">
                <strong>N├úo consegui buscar o QR.</strong>{' '}
                {(error as Error).message}
                <button
                  onClick={() => refetch()}
                  className="block mt-1 text-xs underline hover:text-red-900"
                >
                  Tentar novamente
                </button>
              </div>
            )}

            {!error && status && status.connection_state !== 'open' && (
              <div className="text-[11px] text-slate-500 flex items-center gap-1">
                <span className="w-1.5 h-1.5 rounded-full bg-amber-400 animate-pulse" />
                Aguardando pareamentoÔÇª (atualiza a cada 3s)
              </div>
            )}
          </div>

          {/* QR */}
          <div className="flex items-center justify-center">
            {isLoading || isFetching ? (
              <div className="w-[260px] h-[260px] rounded-lg bg-slate-50 border-2 border-dashed border-slate-200 flex items-center justify-center text-slate-400 text-sm">
                Gerando QRÔÇª
              </div>
            ) : qrBase64 ? (
              <img
                src={qrBase64.startsWith('data:') ? qrBase64 : `data:image/png;base64,${qrBase64}`}
                alt="QR code"
                className="w-[260px] h-[260px] rounded-lg border border-slate-200"
              />
            ) : qrCode ? (
              <div className="w-[260px] h-[260px] rounded-lg bg-slate-50 border border-slate-200 flex items-center justify-center p-3 text-[10px] font-mono text-slate-400 break-all overflow-hidden">
                {qrCode.slice(0, 200)}ÔÇª
              </div>
            ) : (
              <div className="w-[260px] h-[260px] rounded-lg bg-slate-50 border-2 border-dashed border-slate-200 flex flex-col items-center justify-center gap-2 text-slate-400 text-sm">
                <QrCode className="w-10 h-10" strokeWidth={1.2} />
                <span className="text-xs">QR n├úo dispon├¡vel</span>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

function modalTitleFor(p: ProviderMode): string {
  if (p === 'meta_cloud') return 'API Oficial (Meta Cloud)';
  if (p === 'coex') return 'API Oficial ┬À Coex (BSP)';
  return 'WhatsApp Business (n├úo oficial)';
}

function modalSubtitleFor(p: ProviderMode): string {
  if (p === 'meta_cloud') return 'Conecte direto na Graph API da Meta';
  if (p === 'coex') return 'Provedor BSP brasileiro parceiro Meta';
  return 'Conex├úo por QR (Evolution API) ÔÇö pode ser banido';
}

// Marca usado pra evitar warning do TS noUnusedLocals
void Plus;
