import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { History } from 'lucide-react';
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
        <a
          href="/dashboard?legacy=1"
          className="text-xs text-slate-500 hover:text-slate-300 flex items-center gap-1"
          title="Builder antigo (dashboard.html)"
        >
          <History className="w-3 h-3" />
          <span>builder antigo</span>
        </a>
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
            <li key={bp.id}>
              <Link
                to={`/flows/${bp.id}`}
                className="block rounded border border-cigana-border bg-cigana-surface px-4 py-3 flex items-baseline justify-between hover:border-cigana-purple transition-colors"
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
              </Link>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
