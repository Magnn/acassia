import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { AlertCircle, KeyRound, Plus, Trash2, Variable } from 'lucide-react';
import { tenantConfigApi } from '../api/tenantConfig';
import { toast } from '../lib/toast';

type Tab = 'variables' | 'secrets';

export default function TenantConfig() {
  const [tab, setTab] = useState<Tab>('variables');

  return (
    <div className="p-8 max-w-4xl mx-auto text-primary space-y-8">
      <div>
        <h2 className="text-3xl font-black tracking-tight mb-2">Variáveis & Segredos</h2>
        <p className="text-sm text-secondary max-w-2xl leading-relaxed">
          Valores reutilizáveis pelos blocos do construtor — variáveis em JSON
          (não-sensíveis) e segredos cifrados (chaves de API, tokens).
        </p>
      </div>

      <div className="flex gap-2 p-1.5 bg-bg-surface rounded-2xl border border-border shadow-sm max-w-md">
        <TabBtn active={tab === 'variables'} onClick={() => setTab('variables')}>
          <Variable className="w-4 h-4" />
          Variáveis
        </TabBtn>
        <TabBtn active={tab === 'secrets'} onClick={() => setTab('secrets')}>
          <KeyRound className="w-4 h-4" />
          Segredos
        </TabBtn>
      </div>

      <div className="mt-8">
        {tab === 'variables' ? <VariablesPanel /> : <SecretsPanel />}
      </div>
    </div>
  );
}

function TabBtn({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      onClick={onClick}
      className={[
        'flex-1 flex items-center justify-center gap-2 px-6 py-2.5 text-xs font-bold rounded-xl transition-all',
        active
          ? 'bg-accent-amethyst text-white shadow-md'
          : 'text-secondary hover:bg-bg-primary hover:text-primary',
      ].join(' ')}
    >
      {children}
    </button>
  );
}

// ── Variables ────────────────────────────────────────────────────────

function VariablesPanel() {
  const qc = useQueryClient();
  const { data: variables = [], isLoading } = useQuery({
    queryKey: ['tenant-variables'],
    queryFn: tenantConfigApi.listVariables,
  });

  const [newKey, setNewKey] = useState('');
  const [newValue, setNewValue] = useState('');

  const setVar = useMutation({
    mutationFn: ({ key, value }: { key: string; value: unknown }) =>
      tenantConfigApi.setVariable(key, value),
    onSuccess: () => {
      toast.success('Variável salva com sucesso.');
      qc.invalidateQueries({ queryKey: ['tenant-variables'] });
      setNewKey('');
      setNewValue('');
    },
    onError: (e) => toast.error((e as Error).message),
  });

  const delVar = useMutation({
    mutationFn: (key: string) => tenantConfigApi.deleteVariable(key),
    onSuccess: () => {
      toast.success('Variável removida.');
      qc.invalidateQueries({ queryKey: ['tenant-variables'] });
    },
    onError: (e) => toast.error((e as Error).message),
  });

  const handleAdd = () => {
    const k = newKey.trim();
    if (!k) return toast.warning('Informe uma chave identificadora.');
    let parsed: unknown = newValue;
    const trimmed = newValue.trim();
    if (
      trimmed.startsWith('{') ||
      trimmed.startsWith('[') ||
      trimmed === 'true' ||
      trimmed === 'false' ||
      trimmed === 'null' ||
      /^-?\d+(\.\d+)?$/.test(trimmed)
    ) {
      try {
        parsed = JSON.parse(trimmed);
      } catch {
        parsed = newValue;
      }
    }
    setVar.mutate({ key: k, value: parsed });
  };

  return (
    <div className="space-y-6">
      <div className="bg-bg-surface border border-border rounded-3xl p-6 shadow-sm space-y-4">
        <div className="text-[10px] uppercase font-black tracking-widest text-secondary">
          Definir Nova Variável
        </div>
        <div className="flex flex-col md:flex-row gap-3">
          <input
            value={newKey}
            onChange={(e) => setNewKey(e.target.value)}
            placeholder="chave (ex.: site_url)"
            className="flex-1 rounded-xl border border-border bg-bg-primary px-4 py-2.5 text-sm font-bold focus:outline-none focus:border-accent-amethyst shadow-inner"
          />
          <input
            value={newValue}
            onChange={(e) => setNewValue(e.target.value)}
            placeholder='valor (string, número ou objeto JSON)'
            className="flex-[2] rounded-xl border border-border bg-bg-primary px-4 py-2.5 text-sm focus:outline-none focus:border-accent-amethyst shadow-inner"
          />
          <button
            onClick={handleAdd}
            disabled={setVar.isPending}
            className="px-6 py-2.5 rounded-xl bg-accent-amethyst text-white text-sm font-bold hover:brightness-110 disabled:opacity-50 flex items-center justify-center gap-2 shadow-sm transition-all"
          >
            <Plus className="w-4 h-4" />
            {setVar.isPending ? 'Salvando...' : 'Salvar'}
          </button>
        </div>
      </div>

      <div className="bg-bg-surface border border-border rounded-3xl shadow-sm overflow-hidden">
        {isLoading && <p className="p-8 text-center text-xs text-secondary animate-pulse">Carregando variáveis…</p>}
        {!isLoading && variables.length === 0 && (
          <p className="p-8 text-center text-xs text-secondary italic">Nenhuma variável global definida para este tenant.</p>
        )}

        {variables.length > 0 && (
          <ul className="divide-y divide-border/40">
            {variables.map((v) => (
              <li
                key={v.key}
                className="px-6 py-4 flex items-center gap-4 hover:bg-bg-primary/10 transition-colors group"
              >
                <div className="w-10 h-10 rounded-xl bg-bg-primary border border-border flex items-center justify-center text-accent-amethyst flex-shrink-0">
                  <Variable className="w-5 h-5" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="font-bold text-sm text-primary truncate">{v.key}</div>
                  <div className="font-mono text-[11px] text-secondary mt-1 break-all bg-bg-primary/50 px-2 py-0.5 rounded border border-border/30 inline-block">
                    {JSON.stringify(v.value)}
                  </div>
                </div>
                <button
                  onClick={() => {
                    if (confirm(`Deseja remover a variável "${v.key}"?`)) delVar.mutate(v.key);
                  }}
                  className="p-2.5 rounded-xl text-secondary hover:text-red-500 hover:bg-red-500/10 transition-all opacity-0 group-hover:opacity-100"
                  title="Remover"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}

// ── Secrets ──────────────────────────────────────────────────────────

function SecretsPanel() {
  const qc = useQueryClient();
  const { data: secrets = [], isLoading, error } = useQuery({
    queryKey: ['tenant-secrets'],
    queryFn: tenantConfigApi.listSecrets,
  });

  const [newKey, setNewKey] = useState('');
  const [newValue, setNewValue] = useState('');

  const setSecret = useMutation({
    mutationFn: ({ key, value }: { key: string; value: string }) =>
      tenantConfigApi.setSecret(key, value),
    onSuccess: () => {
      toast.success('Segredo armazenado com segurança.');
      qc.invalidateQueries({ queryKey: ['tenant-secrets'] });
      setNewKey('');
      setNewValue('');
    },
    onError: (e) => toast.error((e as Error).message),
  });

  const delSecret = useMutation({
    mutationFn: (key: string) => tenantConfigApi.deleteSecret(key),
    onSuccess: () => {
      toast.success('Segredo removido do servidor.');
      qc.invalidateQueries({ queryKey: ['tenant-secrets'] });
    },
    onError: (e) => toast.error((e as Error).message),
  });

  const errMsg = (error as Error | undefined)?.message;
  const isMissingKey = errMsg?.includes('MEU_MISTERIO_FLOW_SECRETS_KEY');

  return (
    <div className="space-y-6">
      {isMissingKey && (
        <div className="rounded-2xl border border-amber-500/30 bg-amber-500/5 p-4 text-xs text-amber-700 flex items-start gap-3">
          <AlertCircle className="w-5 h-5 flex-shrink-0" />
          <span>
            <strong>Configuração Necessária:</strong> A chave de criptografia <strong>MEU_MISTERIO_FLOW_SECRETS_KEY</strong> não foi encontrada no ambiente. Segredos não podem ser salvos até que ela seja definida no arquivo .env do servidor.
          </span>
        </div>
      )}

      <div className="bg-bg-surface border border-border rounded-3xl p-6 shadow-sm space-y-4">
        <div className="text-[10px] uppercase font-black tracking-widest text-secondary">
          Cifrar Novo Segredo
        </div>
        <div className="flex flex-col md:flex-row gap-3">
          <input
            value={newKey}
            onChange={(e) => setNewKey(e.target.value)}
            placeholder="chave (ex.: openai_api_key)"
            className="flex-1 rounded-xl border border-border bg-bg-primary px-4 py-2.5 text-sm font-bold focus:outline-none focus:border-accent-amethyst shadow-inner"
          />
          <input
            type="password"
            value={newValue}
            onChange={(e) => setNewValue(e.target.value)}
            placeholder="valor sensível"
            className="flex-[2] rounded-xl border border-border bg-bg-primary px-4 py-2.5 text-sm focus:outline-none focus:border-accent-amethyst shadow-inner"
            autoComplete="new-password"
          />
          <button
            onClick={() => {
              const k = newKey.trim();
              if (!k) return toast.warning('Informe o nome do segredo.');
              if (!newValue) return toast.warning('Informe o valor do segredo.');
              setSecret.mutate({ key: k, value: newValue });
            }}
            disabled={setSecret.isPending || isMissingKey}
            className="px-6 py-2.5 rounded-xl bg-accent-amethyst text-white text-sm font-bold hover:brightness-110 disabled:opacity-50 flex items-center justify-center gap-2 shadow-sm transition-all"
          >
            <Plus className="w-4 h-4" />
            {setSecret.isPending ? 'Salvando...' : 'Salvar'}
          </button>
        </div>
        <p className="text-[10px] text-secondary italic">
          ⚠️ Os valores são criptografados no servidor. Após salvar, você só poderá visualizar os últimos caracteres para identificação.
        </p>
      </div>

      <div className="bg-bg-surface border border-border rounded-3xl shadow-sm overflow-hidden">
        {isLoading && <p className="p-8 text-center text-xs text-secondary animate-pulse">Carregando segredos…</p>}
        {!isLoading && !error && secrets.length === 0 && (
          <p className="p-8 text-center text-xs text-secondary italic">Nenhum segredo cifrado armazenado.</p>
        )}

        {!isMissingKey && secrets.length > 0 && (
          <ul className="divide-y divide-border/40">
            {secrets.map((s) => (
              <li
                key={s.key}
                className="px-6 py-4 flex items-center gap-4 hover:bg-bg-primary/10 transition-colors group"
              >
                <div className="w-10 h-10 rounded-xl bg-bg-primary border border-border flex items-center justify-center text-amber-500 flex-shrink-0">
                  <KeyRound className="w-5 h-5" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="font-bold text-sm text-primary truncate">{s.key}</div>
                  <div className="font-mono text-xs text-secondary mt-1">{s.masked}</div>
                </div>
                <div className="text-[10px] text-secondary font-medium">
                  {s.updated_at ? new Date(s.updated_at).toLocaleDateString() : '—'}
                </div>
                <button
                  onClick={() => {
                    if (confirm(`Deseja deletar permanentemente o segredo "${s.key}"?`)) delSecret.mutate(s.key);
                  }}
                  className="p-2.5 rounded-xl text-secondary hover:text-red-500 hover:bg-red-500/10 transition-all opacity-0 group-hover:opacity-100"
                  title="Remover"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
