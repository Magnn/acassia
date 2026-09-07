import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  ArrowLeft,
  Bot,
  BrainCircuit,
  CheckCircle2,
  Download,
  HelpCircle,
  History as HistoryIcon,
  Play,
  Redo2,
  Rocket,
  Settings,
  Square,
  Undo2,
  XCircle,
  Zap,
} from 'lucide-react';
import { blueprintsApi, type BlueprintDetail } from '../api/blueprints';
import Canvas from '../builder/Canvas';
import LintPanel from '../builder/LintPanel';
import Palette from '../builder/Palette';
import SaveIndicator from '../builder/SaveIndicator';
import VersionsSidebar from '../builder/VersionsSidebar';
import { issuesByNode, lintGraph } from '../builder/lint';
import { useFlowState } from '../builder/useFlowState';
import Inspector from '../inspector/Inspector';
import Simulator from '../simulator/Simulator';
import ShortcutsModal from '../components/ShortcutsModal';
import { reactFlowToDocument } from '../lib/serialize';
import { exportBlueprint } from '../lib/exportImport';
import { toast } from '../lib/toast';
import type { MeuMisterioDocument } from '../lib/types';
import type { FlowNodeData } from '../lib/adapt';

export default function Builder() {
  const { id } = useParams<{ id: string }>();
  const blueprintId = Number(id);

  const { data, isLoading, error } = useQuery({
    queryKey: ['blueprint', blueprintId],
    queryFn: () => blueprintsApi.get(blueprintId),
    enabled: Number.isFinite(blueprintId) && blueprintId > 0,
  });

  if (!Number.isFinite(blueprintId) || blueprintId <= 0) {
    return (
      <div className="p-6 text-red-400">
        ID de blueprint inválido. <Link className="underline" to="/blueprints">Voltar</Link>
      </div>
    );
  }

  if (isLoading) {
    return <div className="p-6 text-secondary">Carregando fluxo…</div>;
  }
  if (error || !data) {
    return (
      <div className="p-6 text-red-400">
        Erro carregando fluxo: {(error as Error)?.message ?? 'desconhecido'}.{' '}
        <Link className="underline" to="/blueprints">Voltar</Link>
      </div>
    );
  }

  return <BuilderInner blueprint={data} />;
}

type RightPanel = 'inspector' | 'simulator' | 'versions' | null;

function BuilderInner({ blueprint }: { blueprint: BlueprintDetail }) {
  const initialDoc = (blueprint.body ?? {}) as MeuMisterioDocument;
  const fs = useFlowState({ blueprintId: blueprint.id, initialDoc });
  const qc = useQueryClient();

  const issues = useMemo(() => lintGraph(fs.nodes, fs.edges), [fs.nodes, fs.edges]);
  const issueLevels = useMemo(() => issuesByNode(issues), [issues]);

  const [rightPanel, setRightPanel] = useState<RightPanel>(null);
  const [simCurrent, setSimCurrent] = useState<string | null>(null);
  const [focusRequest, setFocusRequest] = useState<{ id: string; ts: number } | null>(null);
  const [shortcutsOpen, setShortcutsOpen] = useState(false);

  // Separate editing state from selection — clicking a node selects it (for drag),
  // but only the Edit button opens the inspector.
  const [editingNodeId, setEditingNodeId] = useState<string | null>(null);

  // Track inspector dirty state to block close when unsaved
  const inspectorDirtyRef = useRef(false);
  const inspectorRequestCloseRef = useRef<(() => void) | null>(null);

  // ── A/B Analytics: fetch e inject nos nós ab_split ──
  const hasAbNodes = useMemo(
    () => fs.nodes.some((n) => n.data.meumisterioType === 'ab_split'),
    [fs.nodes],
  );
  const { data: abData } = useQuery({
    queryKey: ['ab-analytics', blueprint.id],
    queryFn: () => blueprintsApi.abAnalytics(blueprint.id),
    enabled: hasAbNodes,
    refetchInterval: 30_000, // Poll a cada 30s
    retry: false,
  });

  const decoratedNodes = useMemo(
    () =>
      fs.nodes.map((n) => {
        const base = {
          ...n.data,
          lintLevel: issueLevels.get(n.id),
          simActive: simCurrent === n.id || undefined,
          onEdit: () => setEditingNodeId(n.id),
          onDuplicate: () => fs.duplicateNode(n.id),
          onDelete: () => fs.deleteNode(n.id),
        };
        // Inject AB stats into ab_split nodes
        if (n.data.meumisterioType === 'ab_split' && abData?.nodes?.[n.id]) {
          const nodeStats = abData.nodes[n.id];
          base.config = {
            ...base.config,
            ab_stats: {
              ...nodeStats.variants,
              winner: nodeStats.winner,
              total_revenue: nodeStats.total_revenue,
              confidence: nodeStats.confidence,
            },
          };
        }
        return { ...n, data: base };
      }),
    [fs.nodes, issueLevels, simCurrent, fs.duplicateNode, abData],
  );

  const requestFocus = useCallback((nodeId: string) => {
    setFocusRequest({ id: nodeId, ts: Date.now() });
  }, []);

  const handleUpdateEditing = useCallback(
    (patch: Partial<FlowNodeData>) => {
      if (editingNodeId) fs.updateNode(editingNodeId, patch);
    },
    [fs, editingNodeId],
  );

  const handleCloseInspector = useCallback(() => {
    setEditingNodeId(null);
  }, []);

  // Wrap onNodesChange to intercept deselection when inspector is dirty
  const guardedOnNodesChange = useCallback(
    (changes: any[]) => {
      // If inspector is dirty and the editing node is being deselected, block it
      if (inspectorDirtyRef.current && editingNodeId) {
        const isDeselecting = changes.some(
          (c: any) => c.type === 'select' && c.id === editingNodeId && !c.selected
        );
        if (isDeselecting) {
          inspectorRequestCloseRef.current?.();
          const filtered = changes.filter(
            (c: any) => !(c.type === 'select' && c.id === editingNodeId && !c.selected)
          );
          if (filtered.length > 0) fs.onNodesChange(filtered);
          return;
        }
      }
      fs.onNodesChange(changes);
    },
    [fs, editingNodeId],
  );

  // Validate (server-side)
  const validateMutation = useMutation({
    mutationFn: () => {
      const doc = reactFlowToDocument(initialDoc, fs.nodes, fs.edges);
      return blueprintsApi.validate(doc as Record<string, unknown>);
    },
    onSuccess: (rep) => {
      const errs = rep.errors?.length ?? 0;
      const warns = rep.warnings?.length ?? 0;
      if (rep.ok && errs === 0) {
        toast.success(
          warns > 0
            ? `Validação OK · ${warns} aviso(s)`
            : 'Validação OK — fluxo está consistente.',
        );
      } else {
        toast.error(`Validação reprovou: ${errs} erro(s), ${warns} aviso(s)`);
      }
    },
    onError: (e) => toast.error(`Falha ao validar: ${(e as Error).message}`),
  });

  // Publish / unpublish
  const publishMutation = useMutation({
    mutationFn: async () => {
      if (isPublished) return blueprintsApi.unpublish(blueprint.id);
      await fs.saveNow();
      return blueprintsApi.publish(blueprint.id);
    },
    onSuccess: () => {
      toast.success(
        isPublished
          ? `"${blueprint.title}" desativado.`
          : `"${blueprint.title}" publicado.`,
      );
      qc.invalidateQueries({ queryKey: ['publish-status'] });
    },
    onError: (e) => toast.error(`Falha ao alterar publicação: ${(e as Error).message}`),
  });

  // Status atual de publicação (pra mostrar badge "publicado")
  const { data: pubStatus } = useQuery({
    queryKey: ['publish-status'],
    queryFn: () => blueprintsApi.publishStatus(),
  });
  const isPublished =
    pubStatus?.published?.blueprint_id === blueprint.id;

  // Atalhos globais do builder
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement | null;
      const isTyping =
        target &&
        (target.tagName === 'INPUT' ||
          target.tagName === 'TEXTAREA' ||
          target.tagName === 'SELECT' ||
          target.isContentEditable);

      const isMod = e.ctrlKey || e.metaKey;

      if (isMod && e.key.toLowerCase() === 'z' && !e.shiftKey) {
        e.preventDefault();
        fs.undo();
        return;
      }
      if (
        (isMod && e.key.toLowerCase() === 'z' && e.shiftKey) ||
        (isMod && e.key.toLowerCase() === 'y')
      ) {
        e.preventDefault();
        fs.redo();
        return;
      }
      if (e.key === '?' && !isTyping) {
        e.preventDefault();
        setShortcutsOpen((v) => !v);
        return;
      }
      if (e.key === 'Escape') {
        if (shortcutsOpen) {
          setShortcutsOpen(false);
          return;
        }
        if (rightPanel) {
          setRightPanel(null);
          return;
        }
        if (editingNodeId) {
          if (inspectorDirtyRef.current) {
            inspectorRequestCloseRef.current?.();
          } else {
            handleCloseInspector();
          }
          return;
        }
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [fs, handleCloseInspector, shortcutsOpen, rightPanel, editingNodeId]);

  // Quando uma versão é restaurada, recarrega o blueprint e reseta painel
  const handleVersionRestored = useCallback(() => {
    qc.invalidateQueries({ queryKey: ['blueprint', blueprint.id] });
    setRightPanel(null);
  }, [qc, blueprint.id]);

  // Side panel: prioridade — versions > simulator > inspector (auto se selecionou nó)
  let sidePanel: React.ReactNode = null;
  if (rightPanel === 'versions') {
    sidePanel = (
      <VersionsSidebar
        blueprintId={blueprint.id}
        onClose={() => setRightPanel(null)}
        onRestored={handleVersionRestored}
      />
    );
  } else if (rightPanel === 'simulator') {
    sidePanel = (
      <Simulator
        nodes={fs.nodes}
        edges={fs.edges}
        onCurrentNodeChange={setSimCurrent}
        onClose={() => {
          setSimCurrent(null);
          setRightPanel(null);
        }}
      />
    );
  } else if (editingNodeId) {
    const editingNode = fs.nodes.find((n) => n.id === editingNodeId) ?? null;
    if (editingNode) {
      sidePanel = (
        <Inspector
          node={editingNode}
          onUpdate={handleUpdateEditing}
          onClose={handleCloseInspector}
          onDirtyChange={(dirty) => { inspectorDirtyRef.current = dirty; }}
          onRequestCloseRef={inspectorRequestCloseRef}
        />
      );
    }
  }

  const editable = rightPanel !== 'simulator';

  return (
    <div className="h-full flex flex-col bg-bg-primary">
      {/* Modern ChatbotX / Linear Glass Navbar */}
      <div className="h-14 bg-white/95 dark:bg-zinc-950/95 border-b border-zinc-200 dark:border-zinc-800/80 px-4 flex items-center justify-between flex-shrink-0 z-20 backdrop-blur-md">
        
        {/* Left: Back + Title + Status Badges */}
        <div className="flex items-center gap-3">
          <Link
            to="/blueprints"
            className="w-8 h-8 rounded-xl border border-zinc-200 dark:border-zinc-800 text-zinc-600 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-white hover:bg-zinc-100 dark:hover:bg-zinc-800 flex items-center justify-center transition-all shadow-xs"
            title="Voltar aos Funis"
          >
            <ArrowLeft className="w-4 h-4" />
          </Link>

          <div className="h-4 w-px bg-zinc-200 dark:bg-zinc-800" />

          <div className="flex items-center gap-2">
            <span className="text-sm font-semibold text-zinc-900 dark:text-zinc-100 truncate max-w-[200px]">
              {blueprint.title}
            </span>

            {isPublished ? (
              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-50 text-emerald-600 dark:bg-emerald-950/50 dark:text-emerald-400 border border-emerald-200/60 dark:border-emerald-800/50">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
                Publicado
              </span>
            ) : (
              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-zinc-100 text-zinc-600 dark:bg-zinc-800 dark:text-zinc-400 border border-zinc-200 dark:border-zinc-700">
                Rascunho
              </span>
            )}

            <span className="text-[11px] text-zinc-400 dark:text-zinc-500 font-medium ml-1">
              {fs.status === 'saving' ? (
                <span className="text-amber-500 animate-pulse">Salvando…</span>
              ) : fs.error ? (
                <span className="text-rose-500">Erro ao salvar</span>
              ) : (
                <span className="text-zinc-400 flex items-center gap-1">
                  <CheckCircle2 className="w-3 h-3 text-emerald-500" /> Salvo
                </span>
              )}
            </span>
          </div>
        </div>

        {/* Center: Canvas / Simulator / Versions Switcher */}
        <div className="hidden md:flex items-center bg-zinc-100 dark:bg-zinc-900/90 p-0.5 rounded-xl border border-zinc-200/80 dark:border-zinc-800/80 text-xs font-semibold">
          <button
            onClick={() => setRightPanel(null)}
            className={`px-3 py-1.5 rounded-lg transition-all ${
              rightPanel === null
                ? 'bg-white dark:bg-zinc-800 text-zinc-900 dark:text-white shadow-xs'
                : 'text-zinc-500 hover:text-zinc-900 dark:hover:text-zinc-200'
            }`}
          >
            Canvas do Funil
          </button>
          <button
            onClick={() => setRightPanel((p) => (p === 'simulator' ? null : 'simulator'))}
            className={`px-3 py-1.5 rounded-lg transition-all flex items-center gap-1.5 ${
              rightPanel === 'simulator'
                ? 'bg-white dark:bg-zinc-800 text-indigo-600 dark:text-indigo-400 shadow-xs'
                : 'text-zinc-500 hover:text-zinc-900 dark:hover:text-zinc-200'
            }`}
          >
            <Play className="w-3.5 h-3.5 fill-current" />
            Simulador Zap
          </button>
          <button
            onClick={() => setRightPanel((p) => (p === 'versions' ? null : 'versions'))}
            className={`px-3 py-1.5 rounded-lg transition-all flex items-center gap-1.5 ${
              rightPanel === 'versions'
                ? 'bg-white dark:bg-zinc-800 text-zinc-900 dark:text-white shadow-xs'
                : 'text-zinc-500 hover:text-zinc-900 dark:hover:text-zinc-200'
            }`}
          >
            <HistoryIcon className="w-3.5 h-3.5" />
            Versões
          </button>
        </div>

        {/* Right: Undo/Redo + Validate + Publish Action */}
        <div className="flex items-center gap-2">
          {/* Undo / Redo */}
          <div className="flex items-center bg-zinc-100 dark:bg-zinc-900 rounded-xl p-0.5 border border-zinc-200/80 dark:border-zinc-800/80">
            <button
              onClick={() => fs.undo()}
              disabled={!fs.canUndo}
              className="p-1.5 text-zinc-500 hover:text-zinc-900 dark:hover:text-zinc-200 disabled:opacity-30 disabled:hover:text-zinc-500 rounded-lg transition-colors"
              title="Desfazer (Ctrl+Z)"
            >
              <Undo2 className="w-3.5 h-3.5" />
            </button>
            <button
              onClick={() => fs.redo()}
              disabled={!fs.canRedo}
              className="p-1.5 text-zinc-500 hover:text-zinc-900 dark:hover:text-zinc-200 disabled:opacity-30 disabled:hover:text-zinc-500 rounded-lg transition-colors"
              title="Refazer (Ctrl+Y)"
            >
              <Redo2 className="w-3.5 h-3.5" />
            </button>
          </div>

          {/* Validar */}
          <button
            onClick={() => validateMutation.mutate()}
            disabled={validateMutation.isPending}
            className="px-2.5 py-1.5 text-xs font-semibold rounded-xl border border-zinc-200 dark:border-zinc-800 text-zinc-700 dark:text-zinc-300 hover:bg-zinc-100 dark:hover:bg-zinc-800 transition-colors flex items-center gap-1.5 shadow-xs"
            title="Validar Consistência do Grafo"
          >
            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500" />
            Validar
          </button>

          {/* Ativar / Publicar */}
          <button
            onClick={() => {
              if (confirm(isPublished ? 'Deseja desativar este funil?' : 'Deseja publicar e ativar este funil?')) {
                publishMutation.mutate();
              }
            }}
            disabled={publishMutation.isPending}
            className={`px-3.5 py-1.5 text-xs font-semibold rounded-xl transition-all flex items-center gap-1.5 shadow-xs ${
              isPublished
                ? 'bg-emerald-600 hover:bg-emerald-700 text-white shadow-emerald-500/20'
                : 'bg-indigo-600 hover:bg-indigo-700 text-white shadow-indigo-500/20'
            }`}
          >
            <Zap className="w-3.5 h-3.5 fill-current" />
            {isPublished ? 'Ativo no Zap' : 'Publicar Fluxo'}
          </button>
        </div>
      </div>
      <div className="flex-1 min-h-0 flex relative">
        <Palette />
        <div className="flex-1 min-w-0 flex flex-col">
          <div className="flex-1 min-h-0">
            <Canvas
              nodes={decoratedNodes}
              edges={fs.edges}
              editable={editable}
              focusRequest={focusRequest}
              onNodesChange={guardedOnNodesChange}
              onEdgesChange={fs.onEdgesChange}
              onConnect={fs.onConnect}
              onAddNode={fs.addNode}
            />
          </div>
        </div>
        {sidePanel}
      </div>
      <ShortcutsModal open={shortcutsOpen} onClose={() => setShortcutsOpen(false)} />
    </div>
  );
}
