import { useCallback } from 'react';
import { Link, useParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { blueprintsApi, type BlueprintDetail } from '../api/blueprints';
import Canvas from '../builder/Canvas';
import Palette from '../builder/Palette';
import SaveIndicator from '../builder/SaveIndicator';
import { useFlowState } from '../builder/useFlowState';
import Inspector from '../inspector/Inspector';
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

  // Atualiza node selecionado.
  const handleUpdateSelected = useCallback(
    (patch: Partial<FlowNodeData>) => {
      if (fs.selectedNodeId) fs.updateNode(fs.selectedNodeId, patch);
    },
    [fs],
  );

  // Fecha inspetor: deseleciona via onNodesChange.
  const handleCloseInspector = useCallback(() => {
    if (!fs.selectedNodeId) return;
    fs.onNodesChange([
      { type: 'select', id: fs.selectedNodeId, selected: false },
    ]);
  }, [fs]);

  return (
    <div className="h-full flex flex-col">
      <div className="border-b border-cigana-border bg-cigana-surface px-4 py-2 flex items-center justify-between flex-shrink-0">
        <div className="flex items-baseline gap-3">
          <Link to="/" className="text-xs text-slate-400 hover:text-slate-200">
            ← Fluxos
          </Link>
          <h2 className="text-sm font-medium">{blueprint.title}</h2>
          <span className="text-xs text-slate-500">
            #{blueprint.id} · {blueprint.slug}
          </span>
        </div>
        <div className="flex items-center gap-3 text-xs text-slate-500">
          <span>
            {fs.nodes.length} nodes · {fs.edges.length} arestas
          </span>
          <SaveIndicator status={fs.status} error={fs.error} />
        </div>
      </div>
      <div className="flex-1 min-h-0 flex">
        <Palette />
        <div className="flex-1 min-w-0">
          <Canvas
            nodes={fs.nodes}
            edges={fs.edges}
            editable
            onNodesChange={fs.onNodesChange}
            onEdgesChange={fs.onEdgesChange}
            onConnect={fs.onConnect}
            onAddNode={fs.addNode}
          />
        </div>
        {fs.selectedNode && (
          <Inspector
            node={fs.selectedNode}
            onUpdate={handleUpdateSelected}
            onClose={handleCloseInspector}
          />
        )}
      </div>
    </div>
  );
}
