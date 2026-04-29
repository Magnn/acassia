import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Camera, History, RotateCcw, X } from 'lucide-react';
import { blueprintsApi } from '../api/blueprints';
import { toast } from '../lib/toast';

interface Props {
  blueprintId: number;
  onClose: () => void;
  onRestored: () => void;
}

export default function VersionsSidebar({ blueprintId, onClose, onRestored }: Props) {
  const qc = useQueryClient();
  const [note, setNote] = useState('');

  const { data: versions = [], isLoading } = useQuery({
    queryKey: ['blueprint-versions', blueprintId],
    queryFn: () => blueprintsApi.listVersions(blueprintId),
  });

  const snapshot = useMutation({
    mutationFn: (n: string) => blueprintsApi.createVersion(blueprintId, n),
    onSuccess: () => {
      toast.success('Versão criada.');
      setNote('');
      qc.invalidateQueries({ queryKey: ['blueprint-versions', blueprintId] });
    },
    onError: (e) => toast.error(`Falha: ${(e as Error).message}`),
  });

  const restore = useMutation({
    mutationFn: (vid: number) => blueprintsApi.restoreVersion(blueprintId, vid),
    onSuccess: () => {
      toast.success('Versão restaurada.');
      qc.invalidateQueries({ queryKey: ['blueprint', blueprintId] });
      qc.invalidateQueries({ queryKey: ['blueprint-versions', blueprintId] });
      onRestored();
    },
    onError: (e) => toast.error(`Falha: ${(e as Error).message}`),
  });

  return (
    <aside className="w-80 flex-shrink-0 border-l border-cigana-border bg-cigana-surface flex flex-col h-full animate-slide-in-right shadow-xl">
      <header className="flex items-center justify-between px-3 py-2 border-b border-cigana-border flex-shrink-0">
        <div className="flex items-center gap-2 text-[11px] uppercase tracking-wide text-slate-400">
          <History className="w-3.5 h-3.5 text-cigana-purple" />
          <span>Versões</span>
        </div>
        <button
          onClick={onClose}
          className="text-slate-400 hover:text-slate-100 p-1 rounded hover:bg-cigana-bg"
          title="Fechar"
        >
          <X className="w-4 h-4" />
        </button>
      </header>

      {/* Snapshot form */}
      <div className="px-3 py-3 border-b border-cigana-border space-y-2 flex-shrink-0">
        <input
          type="text"
          value={note}
          onChange={(e) => setNote(e.target.value)}
          placeholder="Nota (opcional)"
          className="w-full text-sm rounded border border-cigana-border bg-cigana-bg px-2 py-1.5 text-slate-100 placeholder:text-slate-500 focus:outline-none focus:border-cigana-purple"
        />
        <button
          type="button"
          disabled={snapshot.isPending}
          onClick={() => snapshot.mutate(note)}
          className="w-full text-xs px-2 py-1.5 rounded bg-cigana-purple text-white hover:brightness-110 disabled:opacity-50 flex items-center justify-center gap-1"
        >
          <Camera className="w-3.5 h-3.5" />
          {snapshot.isPending ? 'Criando…' : 'Snapshot agora'}
        </button>
      </div>

      <div className="flex-1 overflow-y-auto">
        {isLoading && (
          <p className="px-3 py-3 text-xs text-slate-500">Carregando…</p>
        )}
        {!isLoading && versions.length === 0 && (
          <p className="px-3 py-3 text-xs text-slate-500">
            Sem versões salvas. Crie um snapshot acima.
          </p>
        )}
        <ul className="divide-y divide-cigana-border/50">
          {versions.map((v) => (
            <li key={v.id} className="px-3 py-2.5 flex items-start justify-between gap-2 hover:bg-cigana-bg/40">
              <div className="flex-1 min-w-0">
                <div className="text-sm font-medium text-slate-200">
                  v{v.version_number}
                </div>
                <div className="text-[11px] text-slate-500">
                  {v.created_at ? new Date(v.created_at).toLocaleString() : '—'}
                </div>
                {v.note && (
                  <div className="text-xs text-slate-400 mt-1 break-words">
                    {v.note}
                  </div>
                )}
              </div>
              <button
                type="button"
                onClick={() => {
                  if (confirm(`Restaurar v${v.version_number}? O estado atual será sobrescrito (você pode criar um snapshot antes).`))
                    restore.mutate(v.id);
                }}
                disabled={restore.isPending}
                className="text-[11px] px-2 py-1 rounded border border-cigana-border hover:border-cigana-purple text-slate-300 hover:text-slate-100 disabled:opacity-50 flex items-center gap-1 flex-shrink-0"
                title="Restaurar esta versão"
              >
                <RotateCcw className="w-3 h-3" />
                restaurar
              </button>
            </li>
          ))}
        </ul>
      </div>
    </aside>
  );
}
