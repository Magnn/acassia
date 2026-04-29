import { Link, useParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { blueprintsApi } from '../api/blueprints';
import Canvas from '../builder/Canvas';
import type { AcassiaDocument } from '../lib/types';

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

  const doc = (data.body ?? {}) as AcassiaDocument;
  const nodeCount = doc.graph?.nodes?.length ?? 0;
  const edgeCount = doc.graph?.edges?.length ?? 0;

  return (
    <div className="h-full flex flex-col">
      <div className="border-b border-cigana-border bg-cigana-surface px-4 py-2 flex items-center justify-between">
        <div className="flex items-baseline gap-3">
          <Link to="/" className="text-xs text-slate-400 hover:text-slate-200">
            ← Fluxos
          </Link>
          <h2 className="text-sm font-medium">{data.title}</h2>
          <span className="text-xs text-slate-500">
            #{data.id} · {data.slug}
          </span>
        </div>
        <div className="text-xs text-slate-500">
          {nodeCount} nodes · {edgeCount} arestas · read-only (Fase 1)
        </div>
      </div>
      <div className="flex-1 min-h-0">
        <Canvas doc={doc} />
      </div>
    </div>
  );
}
