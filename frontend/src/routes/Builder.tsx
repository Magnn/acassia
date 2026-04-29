import { useCallback, useEffect, useMemo, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  ArrowLeft,
  CheckCircle2,
  Download,
  HelpCircle,
  History as HistoryIcon,
  Play,
  Redo2,
  Rocket,
  Square,
  Undo2,
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
import type { AcassiaDocument } from '../lib/types';
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
  const initialDoc = (blueprint.body ?? {}) as AcassiaDocument;
  const fs = useFlowState({ blueprintId: blueprint.id, initialDoc });
  const qc = useQueryClient();

  const issues = useMemo(() => lintGraph(fs.nodes, fs.edges), [fs.nodes, fs.edges]);
  const issueLevels = useMemo(() => issuesByNode(issues), [issues]);

  const [rightPanel, setRightPanel] = useState<RightPanel>(null);
  const [simCurrent, setSimCurrent] = useState<string | null>(null);
  const [focusRequest, setFocusRequest] = useState<{ id: string; ts: number } | null>(null);
  const [shortcutsOpen, setShortcutsOpen] = useState(false);

  const decoratedNodes = useMemo(
    () =>
      fs.nodes.map((n) => ({
        ...n,
        data: {
          ...n.data,
          lintLevel: issueLevels.get(n.id),
          simActive: simCurrent === n.id || undefined,
        },
      })),
    [fs.nodes, issueLevels, simCurrent],
  );

  const requestFocus = useCallback((nodeId: string) => {
    setFocusRequest({ id: nodeId, ts: Date.now() });
  }, []);

  const handleUpdateSelected = useCallback(
    (patch: Partial<FlowNodeData>) => {
      if (fs.selectedNodeId) fs.updateNode(fs.selectedNodeId, patch);
    },
    [fs],
  );

  const handleCloseInspector = useCallback(() => {
    if (!fs.selectedNodeId) return;
    fs.onNodesChange([{ type: 'select', id: fs.selectedNodeId, selected: false }]);
  }, [fs]);

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

  // Publish
  const publishMutation = useMutation({
    mutationFn: () => blueprintsApi.publish(blueprint.id),
    onSuccess: () => {
      toast.success(`"${blueprint.title}" publicado.`);
      qc.invalidateQueries({ queryKey: ['publish-status'] });
    },
    onError: (e) => toast.error(`Falha ao publicar: ${(e as Error).message}`),
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
        if (fs.selectedNodeId) {
          handleCloseInspector();
          return;
        }
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [fs, handleCloseInspector, shortcutsOpen, rightPanel]);

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
  } else if (fs.selectedNode) {
    sidePanel = (
      <Inspector
        node={fs.selectedNode}
        onUpdate={handleUpdateSelected}
        onClose={handleCloseInspector}
      />
    );
  }

  const editable = rightPanel !== 'simulator';

  return (
    <div className="h-full flex flex-col bg-bg-primary">
      {/* Barra de ferramentas */}
      <div className="h-[60px] border-b border-border bg-bg-header backdrop-blur-sm px-4 flex items-center justify-between flex-shrink-0 z-20">
        <div className="flex items-center gap-4">
          <Link
            to="/flows"
            className="p-2 rounded-md text-secondary hover:text-primary hover:bg-bg-surface transition-colors"
            title="Voltar para lista"
          >
            <ArrowLeft className="w-5 h-5" />
          </Link>
          <div>
            <h2 className="font-display text-base text-primary leading-tight flex items-center gap-2">
              {blueprint.title}
              <span className="text-[10px] bg-bg-surface px-1.5 py-0.5 rounded border border-border text-secondary font-mono font-normal uppercase tracking-wider">
                {blueprint.slug}
              </span>
            </h2>
            <div className="text-[11px] text-secondary">
              última alteração: {blueprint.updated_at ? new Date(blueprint.updated_at).toLocaleString() : '—'}
            </div>
          </div>
        </div>
        
        <div className="flex items-center gap-3 text-xs text-secondary">
          <span>
            {fs.nodes.length} nodes · {fs.edges.length} arestas
          </span>

          <div className="flex items-center gap-1 border-l border-border pl-3">
            <button
              onClick={fs.undo}
              disabled={!fs.canUndo}
              className="p-1.5 rounded text-secondary hover:text-primary hover:bg-bg-surface disabled:opacity-30"
              title="Desfazer (Ctrl+Z)"
            >
              <Undo2 className="w-4 h-4" />
            </button>
            <button
              onClick={fs.redo}
              disabled={!fs.canRedo}
              className="p-1.5 rounded text-secondary hover:text-primary hover:bg-bg-surface disabled:opacity-30"
              title="Refazer (Ctrl+Y)"
            >
              <Redo2 className="w-4 h-4" />
            </button>
            <button
              onClick={() => setShortcutsOpen(true)}
              className="p-1.5 rounded text-secondary hover:text-primary hover:bg-bg-surface"
              title="Atalhos"
            >
              <HelpCircle className="w-3.5 h-3.5" />
            </button>
          </div>

          <SaveIndicator status={fs.status} error={fs.error} />

          {/* Ações de fluxo */}
          <div className="flex items-center gap-1 border-l border-border pl-3">
            <button
              type="button"
              onClick={() => validateMutation.mutate()}
              disabled={validateMutation.isPending}
              title="Validar no servidor"
              className="px-2 py-1 rounded text-xs flex items-center gap-1 border border-border hover:border-accent-amethyst text-primary bg-bg-surface disabled:opacity-50"
            >
              <CheckCircle2 className="w-3 h-3" />
              {validateMutation.isPending ? 'Validando…' : 'Validar'}
            </button>
            <button
              type="button"
              onClick={() => exportBlueprint(blueprint.id, blueprint.slug)}
              title="Exportar JSON"
              className="px-2 py-1 rounded text-xs flex items-center gap-1 border border-border hover:border-accent-amethyst text-primary bg-bg-surface"
            >
              <Download className="w-3 h-3" />
              Export
            </button>
            <button
              type="button"
              onClick={() =>
                setRightPanel((p) => (p === 'versions' ? null : 'versions'))
              }
              title="Histórico de versões"
              className={[
                'px-2 py-1 rounded text-xs flex items-center gap-1 transition-all',
                rightPanel === 'versions'
                  ? 'bg-accent-amethyst text-white shadow-glow-amethyst'
                  : 'border border-border bg-bg-surface hover:border-accent-amethyst text-primary',
              ].join(' ')}
            >
              <HistoryIcon className="w-3 h-3" />
              Versões
            </button>
          <button
            type="button"
            onClick={() => {
              if (
                confirm(
                  isPublished
                    ? `"${blueprint.title}" já está publicado. Republicar?`
                    : `Publicar "${blueprint.title}"? Será o fluxo ativo no motor.`,
                )
              )
                publishMutation.mutate();
            }}
            disabled={publishMutation.isPending}
            title={isPublished ? 'Republicar' : 'Publicar fluxo'}
            className={[
              'px-3 py-1 rounded-lg text-xs font-bold flex items-center gap-1.5 transition-all shadow-sm',
              isPublished
                ? 'bg-emerald-500/10 text-emerald-500 border border-emerald-500/30 hover:bg-emerald-500/20'
                : 'bg-emerald-600 text-white hover:bg-emerald-500 hover:shadow-glow-emerald',
              'disabled:opacity-50',
            ].join(' ')}
          >
            <Rocket className="w-3.5 h-3.5" />
            {publishMutation.isPending
              ? 'Publicando…'
              : isPublished
              ? 'Republicar'
              : 'Publicar'}
          </button>
        </div>

        <button
          type="button"
          onClick={() =>
            setRightPanel((p) => (p === 'simulator' ? null : 'simulator'))
          }
          className={[
            'px-4 py-2 rounded-xl text-xs font-bold flex items-center gap-2 transition-all',
            rightPanel === 'simulator'
              ? 'bg-accent-amethyst text-white shadow-glow-amethyst ring-2 ring-accent-amethyst/20'
              : 'bg-bg-surface border border-border hover:border-accent-amethyst text-primary shadow-sm hover:shadow-md',
          ].join(' ')}
        >
            {rightPanel === 'simulator' ? (
              <>
                <Square className="w-3 h-3" fill="currentColor" />
                Fechar simulador
              </>
            ) : (
              <>
                <Play className="w-3 h-3" fill="currentColor" />
                Simular
              </>
            )}
          </button>
        </div>
      </div>
      <div className="flex-1 min-h-0 flex">
        <Palette />
        <div className="flex-1 min-w-0 flex flex-col">
          <div className="flex-1 min-h-0">
            <Canvas
              nodes={decoratedNodes}
              edges={fs.edges}
              editable={editable}
              focusRequest={focusRequest}
              onNodesChange={fs.onNodesChange}
              onEdgesChange={fs.onEdgesChange}
              onConnect={fs.onConnect}
              onAddNode={fs.addNode}
            />
          </div>
          <LintPanel issues={issues} onFocus={requestFocus} />
        </div>
        {sidePanel}
      </div>
      <ShortcutsModal open={shortcutsOpen} onClose={() => setShortcutsOpen(false)} />
    </div>
  );
}
