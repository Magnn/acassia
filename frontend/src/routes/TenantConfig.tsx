import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { KeyRound, Plus, Trash2, Variable } from 'lucide-react';
import { tenantConfigApi } from '../api/tenantConfig';
import { toast } from '../lib/toast';

type Tab = 'variables' | 'secrets';

export default function TenantConfig() {
  const [tab, setTab] = useState<Tab>('variables');

  return (
    <div className="p-8 max-w-4xl mx-auto text-slate-100">
      <h2 className="text-2xl font-bold mb-2 font-display">Variáveis & Segredos</h2>
      <p className="text-sm text-slate-400 mb-6">
        Valores reutilizáveis pelos blocos do construtor — variáveis em JSON
        (não-sensíveis) e segredos cifrados (chaves de API, tokens).
      </p>

      <div className="flex gap-1 mb-6 border-b border-cigana-border">
        <TabBtn active={tab === 'variables'} onClick={() => setTab('variables')}>
          <Variable className="w-3.5 h-3.5" />
          Variáveis
        </TabBtn>
        <TabBtn active={tab === 'secrets'} onClick={() => setTab('secrets')}>
          <KeyRound className="w-3.5 h-3.5" />
          Segredos
        </TabBtn>
      </div>

      {tab === 'variables' ? <VariablesPanel /> : <SecretsPanel />}
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
        'flex items-center gap-1.5 px-4 py-2 text-sm border-b-2 -mb-px transition-colors',
        active
          ? 'border-cigana-purple text-slate-100'
          : 'border-transparent text-slate-400 hover:text-slate-200',
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
      toast.success('Variável salva.');
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
    if (!k) return toast.warning('Informe uma chave.');
    let parsed: unknown = newValue;
    // Tenta parsear JSON se parecer JSON; senão guarda como string.
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
    <div className="space-y-4">
      <div className="bg-cigana-surface border border-cigana-border rounded-xl p-4 space-y-2">
        <div className="text-[11px] uppercase tracking-wide text-slate-400">
          Adicionar variável
        </div>
        <div className="flex gap-2">
          <input
            value={newKey}
            onChange={(e) => setNewKey(e.target.value)}
            placeholder="chave (ex.: oferta_principal_url)"
            className="flex-1 rounded border border-cigana-border bg-cigana-bg px-3 py-1.5 text-sm focus:outline-none focus:border-cigana-purple font-mono"
          />
          <input
            value={newValue}
            onChange={(e) => setNewValue(e.target.value)}
            placeholder='valor (string ou JSON: 42, true, "x", {"k":1})'
            className="flex-[2] rounded border border-cigana-border bg-cigana-bg px-3 py-1.5 text-sm focus:outline-none focus:border-cigana-purple"
          />
          <button
            onClick={handleAdd}
            disabled={setVar.isPending}
            className="px-3 py-1.5 rounded bg-cigana-purple text-white text-sm hover:brightness-110 disabled:opacity-50 flex items-center gap-1"
          >
            <Plus className="w-3.5 h-3.5" />
            Salvar
          </button>
        </div>
      </div>

      {isLoading && <p className="text-xs text-slate-500">Carregando…</p>}
      {!isLoading && variables.length === 0 && (
        <p className="text-xs text-slate-500">Nenhuma variável definida.</p>
      )}

      <ul className="bg-cigana-surface border border-cigana-border rounded-xl divide-y divide-cigana-border/50 overflow-hidden">
        {variables.map((v) => (
          <li
            key={v.key}
            className="px-4 py-3 flex items-center gap-3 hover:bg-cigana-bg/40"
          >
            <div className="flex-1 min-w-0">
              <div className="font-mono text-sm text-slate-200 truncate">{v.key}</div>
              <div className="font-mono text-xs text-slate-500 break-all">
                {JSON.stringify(v.value)}
              </div>
            </div>
            <button
              onClick={() => {
                if (confirm(`Remover variável "${v.key}"?`)) delVar.mutate(v.key);
              }}
              className="p-1.5 rounded text-slate-400 hover:text-red-400 hover:bg-cigana-bg"
              title="Remover"
            >
              <Trash2 className="w-3.5 h-3.5" />
            </button>
          </li>
        ))}
      </ul>
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
      toast.success('Segredo salvo.');
      qc.invalidateQueries({ queryKey: ['tenant-secrets'] });
      setNewKey('');
      setNewValue('');
    },
    onError: (e) => toast.error((e as Error).message),
  });

  const delSecret = useMutation({
    mutationFn: (key: string) => tenantConfigApi.deleteSecret(key),
    onSuccess: () => {
      toast.success('Segredo removido.');
      qc.invalidateQueries({ queryKey: ['tenant-secrets'] });
    },
    onError: (e) => toast.error((e as Error).message),
  });

  const errMsg = (error as Error | undefined)?.message;
  const isMissingKey = errMsg?.includes('ACASSIA_FLOW_SECRETS_KEY');

  return (
    <div className="space-y-4">
      {isMissingKey && (
        <div className="rounded-xl border border-amber-500/30 bg-amber-950/30 px-4 py-3 text-xs text-amber-200">
          <strong>ACASSIA_FLOW_SECRETS_KEY</strong> não está configurada no
          servidor — segredos exigem essa chave de criptografia. Defina no .env
          e reinicie.
        </div>
      )}

      <div className="bg-cigana-surface border border-cigana-border rounded-xl p-4 space-y-2">
        <div className="text-[11px] uppercase tracking-wide text-slate-400">
          Adicionar segredo
        </div>
        <div className="flex gap-2">
          <input
            value={newKey}
            onChange={(e) => setNewKey(e.target.value)}
            placeholder="chave (ex.: stripe_api_key)"
            className="flex-1 rounded border border-cigana-border bg-cigana-bg px-3 py-1.5 text-sm focus:outline-none focus:border-cigana-purple font-mono"
          />
          <input
            type="password"
            value={newValue}
            onChange={(e) => setNewValue(e.target.value)}
            placeholder="valor (será cifrado)"
            className="flex-[2] rounded border border-cigana-border bg-cigana-bg px-3 py-1.5 text-sm focus:outline-none focus:border-cigana-purple font-mono"
            autoComplete="new-password"
          />
          <button
            onClick={() => {
              const k = newKey.trim();
              if (!k) return toast.warning('Informe uma chave.');
              if (!newValue) return toast.warning('Informe um valor.');
              setSecret.mutate({ key: k, value: newValue });
            }}
            disabled={setSecret.isPending || isMissingKey}
            className="px-3 py-1.5 rounded bg-cigana-purple text-white text-sm hover:brightness-110 disabled:opacity-50 flex items-center gap-1"
          >
            <Plus className="w-3.5 h-3.5" />
            Salvar
          </button>
        </div>
        <p className="text-[10px] text-slate-500">
          Valores são cifrados em repouso. Após salvar, só os 4 últimos
          caracteres aparecem mascarados.
        </p>
      </div>

      {isLoading && <p className="text-xs text-slate-500">Carregando…</p>}
      {!isLoading && !error && secrets.length === 0 && (
        <p className="text-xs text-slate-500">Nenhum segredo armazenado.</p>
      )}

      {!isMissingKey && secrets.length > 0 && (
        <ul className="bg-cigana-surface border border-cigana-border rounded-xl divide-y divide-cigana-border/50 overflow-hidden">
          {secrets.map((s) => (
            <li
              key={s.key}
              className="px-4 py-3 flex items-center gap-3 hover:bg-cigana-bg/40"
            >
              <div className="flex-1 min-w-0">
                <div className="font-mono text-sm text-slate-200 truncate">
                  {s.key}
                </div>
                <div className="font-mono text-xs text-slate-500">{s.masked}</div>
              </div>
              <span className="text-[10px] text-slate-500">
                {s.updated_at ? new Date(s.updated_at).toLocaleDateString() : '—'}
              </span>
              <button
                onClick={() => {
                  if (confirm(`Remover segredo "${s.key}"?`)) delSecret.mutate(s.key);
                }}
                className="p-1.5 rounded text-slate-400 hover:text-red-400 hover:bg-cigana-bg"
                title="Remover"
              >
                <Trash2 className="w-3.5 h-3.5" />
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
