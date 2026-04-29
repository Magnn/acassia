import { useRef } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { Link, useNavigate } from 'react-router-dom';
import { History, Upload } from 'lucide-react';
import { blueprintsApi } from '../api/blueprints';
import { importBlueprintFromFile } from '../lib/exportImport';

export default function BlueprintsList() {
  const { data, isLoading, error } = useQuery({
    queryKey: ['blueprints'],
    queryFn: blueprintsApi.list,
  });
  const qc = useQueryClient();
  const navigate = useNavigate();
  const fileRef = useRef<HTMLInputElement | null>(null);

  const onPickFile = async (file: File) => {
    const newId = await importBlueprintFromFile(file);
    if (newId) {
      qc.invalidateQueries({ queryKey: ['blueprints'] });
      navigate(`/flows/${newId}`);
    }
  };

  return (
    <section className="max-w-3xl mx-auto px-6 py-8">
      <div className="flex items-baseline justify-between mb-6">
        <h1 className="text-xl font-semibold">Fluxos do tenant</h1>
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={() => fileRef.current?.click()}
            className="text-xs text-slate-300 hover:text-slate-100 flex items-center gap-1 px-2 py-1 rounded border border-cigana-border hover:border-cigana-purple"
            title="Importar fluxo de arquivo JSON"
          >
            <Upload className="w-3 h-3" />
            <span>Importar JSON</span>
          </button>
          <a
            href="/dashboard?legacy=1"
            className="text-xs text-slate-500 hover:text-slate-300 flex items-center gap-1"
            title="Builder antigo (dashboard.html)"
          >
            <History className="w-3 h-3" />
            <span>builder antigo</span>
          </a>
          <input
            ref={fileRef}
            type="file"
            accept="application/json,.json"
            className="hidden"
            onChange={(e) => {
              const f = e.target.files?.[0];
              if (f) onPickFile(f);
              e.target.value = '';
            }}
          />
        </div>
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
