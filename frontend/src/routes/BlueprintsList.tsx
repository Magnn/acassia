import { useQuery } from '@tanstack/react-query';
import { blueprintsApi } from '../api/blueprints';

export default function BlueprintsList() {
  const { data, isLoading, error } = useQuery({
    queryKey: ['blueprints'],
    queryFn: blueprintsApi.list,
  });

  return (
    <section className="max-w-3xl mx-auto px-6 py-8">
      <div className="flex items-baseline justify-between mb-6">
        <h1 className="text-xl font-semibold">Fluxos do tenant</h1>
        <span className="text-xs text-slate-500">
          GET /api/flows/blueprints
        </span>
      </div>

      {isLoading && <p className="text-slate-400">Carregando…</p>}

      {error && (
        <p className="text-red-400">Erro: {(error as Error).message}</p>
      )}

      {data && data.length === 0 && (
        <p className="text-slate-400">Nenhum fluxo cadastrado neste tenant.</p>
      )}

      {data && data.length > 0 && (
        <ul className="space-y-2">
          {data.map((bp) => (
            <li
              key={bp.id}
              className="rounded border border-cigana-border bg-cigana-surface px-4 py-3 flex items-baseline justify-between"
            >
              <div>
                <div className="font-medium">{bp.title}</div>
                <div className="text-xs text-slate-500">
                  #{bp.id} · {bp.slug}
                </div>
              </div>
              <div className="text-xs text-slate-500">
                {bp.updated_at ? new Date(bp.updated_at).toLocaleString() : '—'}
              </div>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
