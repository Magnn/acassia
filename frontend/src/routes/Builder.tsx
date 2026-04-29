import { useCallback, useEffect, useMemo, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  ArrowLeft,
  CheckCircle2,
  Download,
  HelpCircle,
  History,
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
    return <div className="p-6 text-slate-400">Carregando fluxo…</div>;
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
    <div className="h-full flex flex-col">
      <div className="border-b border-cigana-border bg-cigana-surface px-4 py-2 flex items-center justify-between flex-shrink-0">
        <div className="flex items-center gap-3">
          <Link to="/blueprints" className="text-xs text-slate-400 hover:text-slate-200 flex items-center gap-1">
            <ArrowLeft className="w-3.5 h-3.5" />
            <span>Fluxos</span>
          </Link>
          <h2 className="text-sm font-medium">{blueprint.title}</h2>
          <span className="text-xs text-slate-500">
            #{blueprint.id} · {blueprint.slug}
          </span>
          {isPublished && (
            <span
              className="text-[10px] uppercase tracking-wider px-1.5 py-0.5 rounded bg-emerald-500/15 text-emerald-300 border border-emerald-500/30 flex items-center gap-1"
              title="Este fluxo está ativo no motor"
            >
              <CheckCircle2 className="w-2.5 h-2.5" />
              publicado
            </span>
          )}
          <a
            href="/dashboard?legacy=1"
            className="text-[11px] text-slate-500 hover:text-slate-300 flex items-center gap-1 hover:underline underline-offset-2"
            title="Abrir o builder antigo (dashboard.html) — fallback de emergência"
          >
            <History className="w-3 h-3" />
            <span>builder antigo</span>
          </a>
        </div>
        <div className="flex items-center gap-3 text-xs text-slate-500">
          <span>
            {fs.nodes.length} nodes · {fs.edges.length} arestas
          </span>

          <div className="flex items-center gap-1 border-l border-cigana-border pl-3">
            <button
              type="button"
              onClick={fs.undo}
              disabled={!fs.canUndo}
              title="Desfazer (Ctrl+Z)"
              className="p-1 rounded hover:bg-cigana-bg disabled:opacity-30 disabled:hover:bg-transparent"
            >
              <Undo2 className="w-3.5 h-3.5" />
            </button>
            <button
              type="button"
              onClick={fs.redo}
              disabled={!fs.canRedo}
              title="Refazer (Ctrl+Shift+Z)"
              className="p-1 rounded hover:bg-cigana-bg disabled:opacity-30 disabled:hover:bg-transparent"
            >
              <Redo2 className="w-3.5 h-3.5" />
            </button>
            <button
              type="button"
              onClick={() => setShortcutsOpen(true)}
              title="Atalhos (?)"
              className="p-1 rounded hover:bg-cigana-bg"
            >
              <HelpCircle className="w-3.5 h-3.5" />
            </button>
          </div>

          <SaveIndicator status={fs.status} error={fs.error} />

          {/* Ações de fluxo */}
          <div className="flex items-center gap-1 border-l border-cigana-border pl-3">
            <button
              type="button"
              onClick={() => validateMutation.mutate()}
              disabled={validateMutation.isPending}
              title="Validar no servidor"
              className="px-2 py-1 rounded text-xs flex items-center gap-1 border border-cigana-border hover:border-cigana-purple disabled:opacity-50"
            >
              <CheckCircle2 className="w-3 h-3" />
              {validateMutation.isPending ? 'Validando…' : 'Validar'}
            </button>
            <button
              type="button"
              onClick={() => exportBlueprint(blueprint.id, blueprint.slug)}
              title="Exportar JSON"
              className="px-2 py-1 rounded text-xs flex items-center gap-1 border border-cigana-border hover:border-cigana-purple"
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
                'px-2 py-1 rounded text-xs flex items-center gap-1',
                rightPanel === 'versions'
                  ? 'bg-cigana-purple text-white'
                  : 'border border-cigana-border hover:border-cigana-purple',
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
                'px-2 py-1 rounded text-xs flex items-center gap-1',
                isPublished
                  ? 'border border-emerald-500/40 text-emerald-300 hover:border-emerald-500'
                  : 'bg-emerald-600 text-white hover:bg-emerald-500',
                'disabled:opacity-50',
              ].join(' ')}
            >
              <Rocket className="w-3 h-3" />
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
              'px-2 py-1 rounded text-xs flex items-center gap-1',
              rightPanel === 'simulator'
                ? 'bg-cigana-purple text-white'
                : 'border border-cigana-border hover:border-cigana-purple',
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
