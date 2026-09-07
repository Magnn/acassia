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
      {/* Barra de ferramentas */}
      {/* Barra de ferramentas LAILLA Style */}
      <div className="h-[64px] bg-white border-b border-slate-200 px-4 flex items-center justify-between flex-shrink-0 z-20">
        
        {/* Left Actions */}
        <div className="flex items-center gap-2">
          <Link
            to="/flows"
            className="w-[38px] h-[38px] rounded-lg bg-[#9333ea] hover:bg-[#7e22ce] text-white flex items-center justify-center transition-colors shadow-sm"
            title="Voltar"
          >
            <ArrowLeft className="w-5 h-5" />
          </Link>
          <button
            onClick={() => {}}
            className="w-[38px] h-[38px] rounded-lg bg-[#f97316] hover:bg-[#ea580c] text-white flex items-center justify-center transition-colors shadow-sm"
            title="Cancelar"
          >
            <XCircle className="w-5 h-5" />
          </button>
          <button
            onClick={() => {
               if (confirm(isPublished ? `Desativar fluxo?` : `Ativar fluxo?`)) {
                  publishMutation.mutate();
               }
            }}
            disabled={publishMutation.isPending}
            className={`w-[38px] h-[38px] rounded-lg flex items-center justify-center transition-colors shadow-sm ${isPublished ? 'bg-[#10b981] hover:bg-[#059669] text-white' : 'bg-slate-200 text-slate-500 hover:bg-slate-300'}`}
            title={isPublished ? "Fluxo Ativo (Clique para desativar)" : "Ativar Fluxo"}
          >
            <Zap className="w-5 h-5" />
          </button>
        </div>

        {/* Center Tabs */}
        <div className="absolute left-1/2 -translate-x-1/2 flex flex-col items-center gap-1.5">
           <div className="flex items-center gap-2 text-[13px] font-bold text-slate-800">
              <Bot className="w-4 h-4 text-blue-600" />
              {blueprint.title}
              <span className="bg-[#10b981] text-white text-[9px] px-1.5 py-0.5 rounded tracking-widest uppercase">
                 {fs.status === 'saving' ? 'Salvando...' : fs.error ? 'Erro' : 'Salvo'}
              </span>
           </div>
           
           <div className="flex items-center bg-slate-100 p-1 rounded-full text-[11px] font-bold text-slate-500">
              <button className="px-4 py-1.5 rounded-full hover:text-slate-700 transition-colors">Logs</button>
              <button className="px-4 py-1.5 rounded-full bg-[#9333ea] text-white shadow-sm transition-colors">Automação</button>
              <button className="px-4 py-1.5 rounded-full hover:text-slate-700 transition-colors">Relatórios</button>
           </div>
        </div>

        {/* Right Actions */}
        <div className="flex items-center gap-2">
          <button
             onClick={() => setRightPanel((p) => (p === 'simulator' ? null : 'simulator'))}
             className="w-[38px] h-[38px] rounded-lg bg-[#9333ea] hover:bg-[#7e22ce] text-white flex items-center justify-center transition-colors shadow-sm"
             title="Simulador"
          >
             <Play className="w-5 h-5" />
          </button>
          
          <button
            onClick={() => setRightPanel((p) => (p === 'versions' ? null : 'versions'))}
            className="w-[38px] h-[38px] rounded-lg bg-[#9333ea] hover:bg-[#7e22ce] text-white flex items-center justify-center transition-colors shadow-sm"
            title="Versões"
          >
            <HistoryIcon className="w-5 h-5" />
          </button>

          <button
            className="w-[38px] h-[38px] rounded-lg bg-[#9333ea] hover:bg-[#7e22ce] text-white flex items-center justify-center transition-colors shadow-sm"
            title="Inteligência Artificial"
          >
            <BrainCircuit className="w-5 h-5" />
          </button>
          
          <button
            className="w-[38px] h-[38px] rounded-lg bg-[#9333ea] hover:bg-[#7e22ce] text-white flex items-center justify-center transition-colors shadow-sm"
            title="Configurações"
          >
            <Settings className="w-5 h-5" />
          </button>

          <button
            onClick={() => validateMutation.mutate()}
            className="w-[38px] h-[38px] rounded-lg bg-[#84cc16] hover:bg-[#65a30d] text-white flex items-center justify-center transition-colors shadow-sm"
            title="Salvar e Validar"
          >
            <CheckCircle2 className="w-5 h-5" />
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
