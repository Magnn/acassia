import { useEffect, useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  Bot,
  Camera,
  CheckCircle2,
  FileText,
  HelpCircle,
  Library,
  Plus,
  Rocket,
  Sparkles,
  Trash2,
} from 'lucide-react';
import { agentsApi, type AgentDraft, type AgentSummary } from '../api/agents';
import { toast } from '../lib/toast';

type Tab = 'personalidade' | 'instrucoes' | 'base' | 'faq';

const TABS: { id: Tab; label: string; Icon: typeof Sparkles }[] = [
  { id: 'personalidade', label: 'Personalidade', Icon: Sparkles },
  { id: 'instrucoes', label: 'Instruções', Icon: FileText },
  { id: 'base', label: 'Base de Conhecimento', Icon: Library },
  { id: 'faq', label: 'FAQ', Icon: HelpCircle },
];

export default function AgentStudio() {
  const qc = useQueryClient();
  const [selectedId, setSelectedId] = useState<number | null>(null);

  const { data: agents = [] } = useQuery({
    queryKey: ['studio-agents'],
    queryFn: agentsApi.list,
  });

  const { data: pubStatus } = useQuery({
    queryKey: ['studio-publish-status'],
    queryFn: agentsApi.publishStatus,
  });

  // Auto-seleciona o primeiro
  useEffect(() => {
    if (selectedId == null && agents.length > 0) setSelectedId(agents[0].id);
  }, [agents, selectedId]);

  const createMutation = useMutation({
    mutationFn: agentsApi.create,
    onSuccess: (res) => {
      toast.success('Agente criado.');
      qc.invalidateQueries({ queryKey: ['studio-agents'] });
      setSelectedId(res.agent.id);
    },
    onError: (e) => toast.error((e as Error).message),
  });

  const removeMutation = useMutation({
    mutationFn: agentsApi.remove,
    onSuccess: () => {
      toast.success('Agente removido.');
      qc.invalidateQueries({ queryKey: ['studio-agents'] });
      setSelectedId(null);
    },
    onError: (e) => toast.error((e as Error).message),
  });

  const handleNew = () => {
    const name = window.prompt('Nome do agente:');
    if (name && name.trim()) createMutation.mutate({ name: name.trim() });
  };

  const selectedAgent = agents.find((a) => a.id === selectedId) ?? null;
  const publishedVersionId = pubStatus?.published?.version_id ?? null;

  return (
    <div className="flex h-full bg-sibila-onyx text-sibila-moonlight">
      {/* Lista */}
      <aside className="w-64 flex-shrink-0 border-r border-sibila-mist bg-sibila-obsidian flex flex-col">
        <div className="px-3 py-3 border-b border-sibila-mist flex items-center justify-between">
          <span className="text-[11px] uppercase tracking-wide text-sibila-fog flex items-center gap-1.5">
            <Bot className="w-3.5 h-3.5" />
            Agentes
          </span>
          <button
            onClick={handleNew}
            disabled={createMutation.isPending}
            className="text-xs px-2 py-0.5 rounded bg-sibila-amethyst text-white hover:brightness-110 flex items-center gap-1"
          >
            <Plus className="w-3 h-3" />
            Novo
          </button>
        </div>
        <ul className="flex-1 overflow-y-auto">
          {agents.length === 0 && (
            <li className="px-3 py-3 text-xs text-sibila-smoke">
              Nenhum agente. Crie o primeiro.
            </li>
          )}
          {agents.map((a) => (
            <li key={a.id}>
              <button
                onClick={() => setSelectedId(a.id)}
                className={[
                  'w-full text-left px-3 py-2.5 flex items-center gap-2 border-l-2 transition-colors',
                  selectedId === a.id
                    ? 'bg-sibila-onyx/60 border-sibila-amethyst'
                    : 'border-transparent hover:bg-sibila-onyx/40',
                ].join(' ')}
              >
                <span
                  className="w-6 h-6 rounded-full flex items-center justify-center text-[10px] font-bold text-white flex-shrink-0"
                  style={{ backgroundColor: a.avatar || '#7c3aed' }}
                >
                  {a.name?.charAt(0).toUpperCase() || '?'}
                </span>
                <span className="flex-1 min-w-0">
                  <div className="text-sm text-sibila-moonlight truncate">{a.name}</div>
                  <div className="text-[10px] text-sibila-smoke">
                    #{a.id}
                    {a.published_version_id && (
                      <span className="ml-2 text-emerald-400">● ativo</span>
                    )}
                  </div>
                </span>
              </button>
            </li>
          ))}
        </ul>
      </aside>

      {/* Editor */}
      <main className="flex-1 min-w-0 overflow-y-auto">
        {selectedAgent ? (
          <AgentEditor
            key={selectedAgent.id}
            agent={selectedAgent}
            publishedVersionId={publishedVersionId}
            onDelete={() => {
              if (confirm(`Apagar agente "${selectedAgent.name}"?`))
                removeMutation.mutate(selectedAgent.id);
            }}
          />
        ) : (
          <div className="p-12 text-center text-sibila-smoke">
            <Bot className="w-10 h-10 mx-auto opacity-30 mb-3" />
            <p>Selecione ou crie um agente.</p>
          </div>
        )}
      </main>
    </div>
  );
}

// ── Editor ────────────────────────────────────────────────────────────

function AgentEditor({
  agent,
  publishedVersionId,
  onDelete,
}: {
  agent: AgentSummary;
  publishedVersionId: number | null;
  onDelete: () => void;
}) {
  const qc = useQueryClient();
  const [tab, setTab] = useState<Tab>('personalidade');
  const [draft, setDraft] = useState<AgentDraft>(agent.draft ?? {});
  const [name, setName] = useState(agent.name);
  const [dirty, setDirty] = useState(false);

  // Sincroniza quando troca de agente.
  useEffect(() => {
    setDraft(agent.draft ?? {});
    setName(agent.name);
    setDirty(false);
  }, [agent.id]);

  const saveMutation = useMutation({
    mutationFn: () => agentsApi.update(agent.id, { name, draft }),
    onSuccess: () => {
      setDirty(false);
      toast.success('Rascunho salvo.');
      qc.invalidateQueries({ queryKey: ['studio-agents'] });
    },
    onError: (e) => toast.error((e as Error).message),
  });

  const snapshotMutation = useMutation({
    mutationFn: (note: string) => agentsApi.snapshot(agent.id, note),
    onSuccess: () => {
      toast.success('Versão criada.');
      qc.invalidateQueries({ queryKey: ['studio-agents'] });
    },
    onError: (e) => toast.error((e as Error).message),
  });

  const publishMutation = useMutation({
    mutationFn: (versionId: number) => agentsApi.publish(agent.id, versionId),
    onSuccess: (res) => {
      toast.success(`Versão #${res.published_version_id} publicada.`);
      qc.invalidateQueries({ queryKey: ['studio-publish-status'] });
    },
    onError: (e) => toast.error((e as Error).message),
  });

  const versions = useMemo(
    () =>
      [...(agent.versions ?? [])].sort(
        (a, b) => b.version_number - a.version_number,
      ),
    [agent.versions],
  );

  const update = (patch: Partial<AgentDraft>) => {
    setDraft((d) => ({ ...d, ...patch }));
    setDirty(true);
  };

  return (
    <div className="p-6 max-w-4xl mx-auto space-y-5">
      {/* Header do agente */}
      <div className="flex items-center gap-3">
        <span
          className="w-12 h-12 rounded-xl flex items-center justify-center text-lg font-bold text-white flex-shrink-0"
          style={{ backgroundColor: agent.avatar || '#7c3aed' }}
        >
          {(name || agent.name).charAt(0).toUpperCase() || '?'}
        </span>
        <input
          type="text"
          value={name}
          onChange={(e) => {
            setName(e.target.value);
            setDirty(true);
          }}
          className="flex-1 text-xl font-bold bg-transparent outline-none border-b border-transparent focus:border-sibila-amethyst"
        />
        <div className="flex items-center gap-2 text-xs text-sibila-smoke">
          {dirty && <span className="text-amber-400">● não salvo</span>}
          <button
            onClick={() => saveMutation.mutate()}
            disabled={!dirty || saveMutation.isPending}
            className="px-2 py-1 rounded bg-sibila-amethyst text-white disabled:opacity-40"
          >
            {saveMutation.isPending ? 'Salvando…' : 'Salvar'}
          </button>
          <button
            onClick={() => {
              const note = window.prompt('Nota da versão (opcional):') ?? '';
              snapshotMutation.mutate(note);
            }}
            disabled={snapshotMutation.isPending}
            className="px-2 py-1 rounded border border-sibila-mist hover:border-sibila-amethyst flex items-center gap-1"
          >
            <Camera className="w-3 h-3" />
            Snapshot
          </button>
          <button
            onClick={onDelete}
            className="px-2 py-1 rounded border border-sibila-mist hover:border-red-500 hover:text-red-400"
            title="Apagar agente"
          >
            <Trash2 className="w-3 h-3" />
          </button>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 border-b border-sibila-mist">
        {TABS.map((t) => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className={[
              'flex items-center gap-1.5 px-4 py-2 text-sm border-b-2 -mb-px transition-colors',
              tab === t.id
                ? 'border-sibila-amethyst text-sibila-moonlight'
                : 'border-transparent text-sibila-fog hover:text-sibila-moonlight',
            ].join(' ')}
          >
            <t.Icon className="w-3.5 h-3.5" />
            {t.label}
          </button>
        ))}
      </div>

      {/* Conteúdo da aba */}
      {tab === 'personalidade' && (
        <textarea
          value={draft.personalidade ?? ''}
          onChange={(e) => update({ personalidade: e.target.value })}
          rows={12}
          placeholder="Como o agente se comporta? Tom, vocabulário, estilo, limites…"
          className="w-full bg-sibila-obsidian border border-sibila-mist rounded-lg px-3 py-2 text-sm text-sibila-moonlight focus:outline-none focus:border-sibila-amethyst"
        />
      )}
      {tab === 'instrucoes' && (
        <textarea
          value={draft.instrucoes ?? ''}
          onChange={(e) => update({ instrucoes: e.target.value })}
          rows={12}
          placeholder="Instruções operacionais — o que o agente DEVE e NÃO DEVE fazer."
          className="w-full bg-sibila-obsidian border border-sibila-mist rounded-lg px-3 py-2 text-sm text-sibila-moonlight focus:outline-none focus:border-sibila-amethyst"
        />
      )}
      {tab === 'base' && (
        <textarea
          value={draft.base_conhecimento ?? ''}
          onChange={(e) => update({ base_conhecimento: e.target.value })}
          rows={12}
          placeholder="Conhecimento que o agente domina — produtos, preços, políticas…"
          className="w-full bg-sibila-obsidian border border-sibila-mist rounded-lg px-3 py-2 text-sm text-sibila-moonlight focus:outline-none focus:border-sibila-amethyst"
        />
      )}
      {tab === 'faq' && (
        <FaqEditor
          faqs={draft.faqs ?? []}
          onChange={(faqs) => update({ faqs })}
        />
      )}

      {/* Versões */}
      <div className="bg-sibila-obsidian border border-sibila-mist rounded-xl p-4 mt-6">
        <h3 className="font-bold text-sm mb-3 flex items-center gap-2">
          <Rocket className="w-4 h-4 text-sibila-amethyst" />
          Versões publicáveis
        </h3>
        {versions.length === 0 ? (
          <p className="text-xs text-sibila-smoke">
            Nenhuma versão ainda. Faça <strong>Snapshot</strong> pra criar a primeira.
          </p>
        ) : (
          <ul className="space-y-1.5">
            {versions.map((v) => {
              const isActive = v.id === publishedVersionId;
              return (
                <li
                  key={v.id}
                  className="flex items-center justify-between text-sm"
                >
                  <span>
                    <span className="font-mono text-sibila-fog">v{v.version_number}</span>{' '}
                    <span className="text-xs text-sibila-smoke">
                      {v.created_at ? new Date(v.created_at).toLocaleString() : ''}
                    </span>
                    {isActive && (
                      <span className="ml-2 text-[10px] uppercase tracking-wide text-emerald-400 flex items-center gap-1 inline-flex">
                        <CheckCircle2 className="w-2.5 h-2.5" />
                        ativo no motor
                      </span>
                    )}
                  </span>
                  {!isActive && (
                    <button
                      onClick={() => {
                        if (confirm(`Publicar v${v.version_number}? Será o agente ativo.`))
                          publishMutation.mutate(v.id);
                      }}
                      className="text-xs px-2 py-0.5 rounded bg-emerald-600 text-white hover:bg-emerald-500"
                    >
                      Publicar
                    </button>
                  )}
                </li>
              );
            })}
          </ul>
        )}
      </div>
    </div>
  );
}

function FaqEditor({
  faqs,
  onChange,
}: {
  faqs: { q: string; a: string }[];
  onChange: (faqs: { q: string; a: string }[]) => void;
}) {
  const update = (i: number, patch: Partial<{ q: string; a: string }>) => {
    onChange(faqs.map((f, idx) => (idx === i ? { ...f, ...patch } : f)));
  };
  const remove = (i: number) => onChange(faqs.filter((_, idx) => idx !== i));
  const add = () => onChange([...faqs, { q: '', a: '' }]);

  return (
    <div className="space-y-3">
      {faqs.map((f, i) => (
        <div
          key={i}
          className="bg-sibila-obsidian border border-sibila-mist rounded-lg p-3 space-y-2"
        >
          <div className="flex items-center justify-between">
            <span className="text-[11px] uppercase tracking-wide text-sibila-fog">
              Pergunta {i + 1}
            </span>
            <button
              onClick={() => remove(i)}
              className="text-sibila-smoke hover:text-red-400 p-1 rounded hover:bg-sibila-onyx"
            >
              <Trash2 className="w-3 h-3" />
            </button>
          </div>
          <input
            type="text"
            value={f.q}
            onChange={(e) => update(i, { q: e.target.value })}
            placeholder="Pergunta…"
            className="w-full bg-sibila-onyx border border-sibila-mist rounded px-2 py-1.5 text-sm focus:outline-none focus:border-sibila-amethyst"
          />
          <textarea
            value={f.a}
            onChange={(e) => update(i, { a: e.target.value })}
            placeholder="Resposta…"
            rows={3}
            className="w-full bg-sibila-onyx border border-sibila-mist rounded px-2 py-1.5 text-sm focus:outline-none focus:border-sibila-amethyst"
          />
        </div>
      ))}
      <button
        onClick={add}
        className="w-full text-xs px-2 py-2 rounded border border-dashed border-sibila-mist text-sibila-fog hover:text-sibila-moonlight hover:border-sibila-amethyst flex items-center justify-center gap-1"
      >
        <Plus className="w-3.5 h-3.5" />
        adicionar FAQ
      </button>
    </div>
  );
}
