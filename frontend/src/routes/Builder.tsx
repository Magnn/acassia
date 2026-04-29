import { useCallback, useMemo, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { ArrowLeft, History, Play, Square } from 'lucide-react';
import { blueprintsApi, type BlueprintDetail } from '../api/blueprints';
import Canvas from '../builder/Canvas';
import LintPanel from '../builder/LintPanel';
import Palette from '../builder/Palette';
import SaveIndicator from '../builder/SaveIndicator';
import { issuesByNode, lintGraph } from '../builder/lint';
import { useFlowState } from '../builder/useFlowState';
import Inspector from '../inspector/Inspector';
import Simulator from '../simulator/Simulator';
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
        ID de blueprint inválido. <Link className="underline" to="/">Voltar</Link>
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
        <Link className="underline" to="/">Voltar</Link>
      </div>
    );
  }

  return <BuilderInner blueprint={data} />;
}

function BuilderInner({ blueprint }: { blueprint: BlueprintDetail }) {
  const initialDoc = (blueprint.body ?? {}) as AcassiaDocument;
  const fs = useFlowState({ blueprintId: blueprint.id, initialDoc });

  const issues = useMemo(() => lintGraph(fs.nodes, fs.edges), [fs.nodes, fs.edges]);
  const issueLevels = useMemo(() => issuesByNode(issues), [issues]);

  const [simOpen, setSimOpen] = useState(false);
  const [simCurrent, setSimCurrent] = useState<string | null>(null);
  const [focusRequest, setFocusRequest] = useState<{ id: string; ts: number } | null>(null);

  // Decora nodes com lintLevel + simActive sem mexer no estado real.
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

  const sidePanel = simOpen ? (
    <Simulator
      nodes={fs.nodes}
      edges={fs.edges}
      onCurrentNodeChange={setSimCurrent}
      onClose={() => {
        setSimCurrent(null);
        setSimOpen(false);
      }}
    />
  ) : fs.selectedNode ? (
    <Inspector
      node={fs.selectedNode}
      onUpdate={handleUpdateSelected}
      onClose={handleCloseInspector}
    />
  ) : null;

  return (
    <div className="h-full flex flex-col">
      <div className="border-b border-cigana-border bg-cigana-surface px-4 py-2 flex items-center justify-between flex-shrink-0">
        <div className="flex items-center gap-3">
          <Link to="/" className="text-xs text-slate-400 hover:text-slate-200 flex items-center gap-1">
            <ArrowLeft className="w-3.5 h-3.5" />
            <span>Fluxos</span>
          </Link>
          <h2 className="text-sm font-medium">{blueprint.title}</h2>
          <span className="text-xs text-slate-500">
            #{blueprint.id} · {blueprint.slug}
          </span>
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
          <SaveIndicator status={fs.status} error={fs.error} />
          <button
            type="button"
            onClick={() => setSimOpen((v) => !v)}
            className={[
              'px-2 py-1 rounded text-xs flex items-center gap-1',
              simOpen
                ? 'bg-cigana-purple text-white'
                : 'border border-cigana-border hover:border-cigana-purple',
            ].join(' ')}
          >
            {simOpen ? (
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
              editable={!simOpen}
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
    </div>
  );
}
