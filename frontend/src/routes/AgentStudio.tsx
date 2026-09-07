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
    <div className="flex h-full bg-bg-primary text-primary">
      {/* Lista */}
      <aside className="w-72 flex-shrink-0 border-r border-border bg-bg-sidebar flex flex-col">
        <div className="px-4 py-4 border-b border-border flex items-center justify-between bg-bg-sidebar/50">
          <span className="text-[10px] uppercase tracking-widest font-black text-secondary flex items-center gap-2">
            <Bot className="w-4 h-4 text-accent-amethyst" />
            Agentes
          </span>
          <button
            onClick={handleNew}
            disabled={createMutation.isPending}
            className="text-[10px] uppercase font-bold px-3 py-1.5 rounded-lg bg-accent-amethyst text-white hover:brightness-110 flex items-center gap-1.5 shadow-sm transition-all"
          >
            <Plus className="w-3 h-3" />
            Novo
          </button>
        </div>
        <ul className="flex-1 overflow-y-auto py-2">
          {agents.length === 0 && (
            <li className="px-4 py-8 text-center text-xs text-secondary italic">
              Nenhum agente cadastrado.
            </li>
          )}
          {agents.map((a) => (
            <li key={a.id} className="px-2">
              <button
                onClick={() => setSelectedId(a.id)}
                className={[
                  'w-full text-left px-3 py-3 flex items-center gap-3 rounded-xl transition-all',
                  selectedId === a.id
                    ? 'bg-bg-primary shadow-sm ring-1 ring-border'
                    : 'hover:bg-bg-primary/50 opacity-70 hover:opacity-100',
                ].join(' ')}
              >
                <span
                  className="w-8 h-8 rounded-xl flex items-center justify-center text-xs font-black text-white flex-shrink-0 shadow-sm"
                  style={{ backgroundColor: a.avatar || 'var(--accent-amethyst)' }}
                >
                  {a.name?.charAt(0).toUpperCase() || '?'}
                </span>
                <span className="flex-1 min-w-0">
                  <div className="text-sm font-bold text-primary truncate leading-tight">{a.name}</div>
                  <div className="text-[10px] text-secondary font-medium mt-0.5 flex items-center gap-2">
                    ID #{a.id}
                    {a.published_version_id && (
                      <span className="flex items-center gap-1 text-emerald-500 font-bold">
                        <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
                        ativo
                      </span>
                    )}
                  </div>
                </span>
              </button>
            </li>
          ))}
        </ul>
      </aside>

      {/* Editor */}
      <main className="flex-1 min-w-0 overflow-y-auto bg-bg-primary/20">
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
          <div className="h-full flex flex-col items-center justify-center text-center p-12">
            <div className="w-20 h-20 rounded-3xl bg-bg-surface border border-border flex items-center justify-center mb-6 shadow-xl">
              <Bot className="w-10 h-10 text-secondary opacity-40" />
            </div>
            <h3 className="text-xl font-bold text-primary mb-2">Seu estúdio de IA</h3>
            <p className="text-sm text-secondary max-w-xs">
              Selecione um agente à esquerda ou crie um novo para começar a treinar sua inteligência.
            </p>
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
    <div className="p-8 max-w-4xl mx-auto space-y-8">
      {/* Header do agente */}
      <div className="flex items-center gap-4 bg-bg-surface p-6 rounded-3xl border border-border shadow-sm">
        <span
          className="w-16 h-16 rounded-2xl flex items-center justify-center text-2xl font-black text-white flex-shrink-0 shadow-lg"
          style={{ backgroundColor: agent.avatar || 'var(--accent-amethyst)' }}
        >
          {(name || agent.name).charAt(0).toUpperCase() || '?'}
        </span>
        <div className="flex-1 min-w-0">
          <input
            type="text"
            value={name}
            onChange={(e) => {
              setName(e.target.value);
              setDirty(true);
            }}
            className="w-full text-2xl font-black bg-transparent outline-none border-b-2 border-transparent focus:border-accent-amethyst transition-all px-0"
            placeholder="Nome do agente"
          />
          <div className="flex items-center gap-3 mt-1.5">
             <span className="text-[10px] uppercase font-bold tracking-widest text-secondary">Draft v{agent.draft_version || 1}</span>
             {dirty && <span className="flex items-center gap-1 text-[10px] uppercase font-black text-amber-500 animate-pulse">● Alterações pendentes</span>}
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => saveMutation.mutate()}
            disabled={!dirty || saveMutation.isPending}
            className="px-4 py-2 rounded-xl bg-accent-amethyst text-white text-xs font-bold shadow-sm hover:brightness-110 transition-all disabled:opacity-40"
          >
            {saveMutation.isPending ? 'Salvando…' : 'Salvar Rascunho'}
          </button>
          <button
            onClick={() => {
              const note = window.prompt('Nota da versão (opcional):') ?? '';
              snapshotMutation.mutate(note);
            }}
            disabled={snapshotMutation.isPending}
            className="px-4 py-2 rounded-xl border border-border bg-bg-primary text-xs font-bold hover:border-accent-amethyst flex items-center gap-2 shadow-sm transition-all"
          >
            <Camera className="w-3.5 h-3.5" />
            Snapshot
          </button>
          <button
            onClick={onDelete}
            className="p-2.5 rounded-xl border border-border bg-bg-primary hover:border-red-500 hover:text-red-500 transition-all"
            title="Apagar agente"
          >
            <Trash2 className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-2 p-1.5 bg-bg-surface rounded-2xl border border-border shadow-sm">
        {TABS.map((t) => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className={[
              'flex-1 flex items-center justify-center gap-2 px-4 py-2.5 text-xs font-bold rounded-xl transition-all',
              tab === t.id
                ? 'bg-accent-amethyst text-white shadow-md'
                : 'text-secondary hover:bg-bg-primary hover:text-primary',
            ].join(' ')}
          >
            <t.Icon className="w-4 h-4" />
            {t.label}
          </button>
        ))}
      </div>

      {/* Conteúdo da aba */}
      <div className="bg-bg-surface border border-border rounded-3xl shadow-sm overflow-hidden min-h-[400px] flex flex-col">
        {tab === 'personalidade' && (
          <textarea
            value={draft.personalidade ?? ''}
            onChange={(e) => update({ personalidade: e.target.value })}
            className="w-full flex-1 bg-transparent p-6 text-sm text-primary leading-relaxed focus:outline-none placeholder:text-secondary/50 resize-none"
            placeholder="Como o agente se comporta? Defina o tom de voz, vocabulário, estilo de saudação e limites de atuação…"
          />
        )}
        {tab === 'instrucoes' && (
          <textarea
            value={draft.instrucoes ?? ''}
            onChange={(e) => update({ instrucoes: e.target.value })}
            className="w-full flex-1 bg-transparent p-6 text-sm text-primary leading-relaxed focus:outline-none placeholder:text-secondary/50 resize-none"
            placeholder="Instruções operacionais — o que o agente DEVE e o que ele JAMAIS deve fazer (guardrails)."
          />
        )}
        {tab === 'base' && (
          <textarea
            value={draft.base_conhecimento ?? ''}
            onChange={(e) => update({ base_conhecimento: e.target.value })}
            className="w-full flex-1 bg-transparent p-6 text-sm text-primary leading-relaxed focus:outline-none placeholder:text-secondary/50 resize-none"
            placeholder="Todo o conhecimento que o agente domina — detalhes de produtos, tabelas de preços, políticas da empresa…"
          />
        )}
        {tab === 'faq' && (
          <div className="p-6">
            <FaqEditor
              faqs={draft.faqs ?? []}
              onChange={(faqs) => update({ faqs })}
            />
          </div>
        )}
      </div>

      {/* Versões */}
      <div className="bg-bg-surface border border-border rounded-3xl p-6 shadow-sm">
        <h3 className="font-black text-xs uppercase tracking-widest text-secondary mb-6 flex items-center gap-2.5">
          <Rocket className="w-4 h-4 text-accent-amethyst" />
          Timeline de Versões
        </h3>
        {versions.length === 0 ? (
          <div className="text-center py-8">
            <p className="text-xs text-secondary italic">
              Nenhuma versão definitiva ainda. Utilize o botão <strong>Snapshot</strong> acima para congelar o rascunho atual em uma versão publicável.
            </p>
          </div>
        ) : (
          <ul className="space-y-3">
            {versions.map((v) => {
              const isActive = v.id === publishedVersionId;
              return (
                <li
                  key={v.id}
                  className={[
                    "flex items-center justify-between p-4 rounded-2xl border transition-all",
                    isActive ? "bg-emerald-500/5 border-emerald-500/20 shadow-sm" : "bg-bg-primary/50 border-border"
                  ].join(" ")}
                >
                  <div className="flex items-center gap-4">
                    <span className="w-10 h-10 rounded-xl bg-bg-surface border border-border flex items-center justify-center font-mono font-bold text-xs shadow-inner">
                      v{v.version_number}
                    </span>
                    <div>
                      <div className="text-xs font-bold text-primary">
                        {v.note || `Versão #${v.version_number}`}
                      </div>
                      <div className="text-[10px] text-secondary mt-1">
                        {v.created_at ? new Date(v.created_at).toLocaleString() : ''}
                      </div>
                    </div>
                    {isActive && (
                      <span className="ml-2 px-2 py-0.5 rounded-full bg-emerald-500 text-white text-[9px] font-black uppercase tracking-widest flex items-center gap-1.5 shadow-sm">
                        <CheckCircle2 className="w-3 h-3" />
                        Ativo
                      </span>
                    )}
                  </div>
                  {!isActive && (
                    <button
                      onClick={() => {
                        if (confirm(`Publicar v${v.version_number}? Este será o agente ativo respondendo aos seus leads.`))
                          publishMutation.mutate(v.id);
                      }}
                      className="text-[10px] uppercase font-black px-4 py-2 rounded-xl bg-emerald-600 text-white hover:bg-emerald-500 shadow-sm transition-all"
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
    <div className="space-y-4">
      {faqs.map((f, i) => (
        <div
          key={i}
          className="bg-bg-primary/50 border border-border rounded-2xl p-4 space-y-3 shadow-inner"
        >
          <div className="flex items-center justify-between">
            <span className="text-[10px] uppercase font-black tracking-widest text-secondary">
              FAQ #{i + 1}
            </span>
            <button
              onClick={() => remove(i)}
              className="p-1.5 rounded-lg text-secondary hover:text-red-500 hover:bg-red-500/10 transition-all"
            >
              <Trash2 className="w-4 h-4" />
            </button>
          </div>
          <div className="space-y-2">
            <input
              type="text"
              value={f.q}
              onChange={(e) => update(i, { q: e.target.value })}
              placeholder="A pergunta do usuário…"
              className="w-full bg-bg-surface border border-border rounded-xl px-4 py-2.5 text-sm font-bold focus:outline-none focus:border-accent-amethyst shadow-sm"
            />
            <textarea
              value={f.a}
              onChange={(e) => update(i, { a: e.target.value })}
              placeholder="A resposta que o agente deve dar…"
              rows={3}
              className="w-full bg-bg-surface border border-border rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:border-accent-amethyst shadow-sm resize-none"
            />
          </div>
        </div>
      ))}
      <button
        onClick={add}
        className="w-full py-4 rounded-2xl border-2 border-dashed border-border text-secondary hover:text-accent-amethyst hover:border-accent-amethyst hover:bg-accent-amethyst/5 flex items-center justify-center gap-2 font-bold text-sm transition-all"
      >
        <Plus className="w-4 h-4" />
        Adicionar Nova FAQ
      </button>
    </div>
  );
}
