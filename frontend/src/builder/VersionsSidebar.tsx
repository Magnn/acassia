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
  const [versionToRestore, setVersionToRestore] = useState<{ id: number; version_number: number } | null>(null);

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
      toast.success('Versão restaurada com sucesso!');
      setVersionToRestore(null);
      qc.invalidateQueries({ queryKey: ['blueprint', blueprintId] });
      qc.invalidateQueries({ queryKey: ['blueprint-versions', blueprintId] });
      onRestored();
    },
    onError: (e) => toast.error(`Falha: ${(e as Error).message}`),
  });

  return (
    <aside className="w-80 flex-shrink-0 border-l border-sibila-mist bg-sibila-obsidian flex flex-col h-full animate-slide-in-right shadow-xl">
      <header className="flex items-center justify-between px-3 py-2 border-b border-sibila-mist flex-shrink-0">
        <div className="flex items-center gap-2 text-[11px] uppercase tracking-wide text-sibila-fog">
          <History className="w-3.5 h-3.5 text-sibila-amethyst" />
          <span>Versões</span>
        </div>
        <button
          onClick={onClose}
          className="text-sibila-fog hover:text-sibila-moonlight p-1 rounded hover:bg-sibila-onyx"
          title="Fechar"
        >
          <X className="w-4 h-4" />
        </button>
      </header>

      {/* Snapshot form */}
      <div className="px-3 py-3 border-b border-sibila-mist space-y-2 flex-shrink-0">
        <input
          type="text"
          value={note}
          onChange={(e) => setNote(e.target.value)}
          placeholder="Nota (opcional)"
          className="w-full text-sm rounded border border-sibila-mist bg-sibila-onyx px-2 py-1.5 text-sibila-moonlight placeholder:text-sibila-smoke focus:outline-none focus:border-sibila-amethyst"
        />
        <button
          type="button"
          disabled={snapshot.isPending}
          onClick={() => snapshot.mutate(note)}
          className="w-full text-xs px-2 py-1.5 rounded bg-sibila-amethyst text-white hover:brightness-110 disabled:opacity-50 flex items-center justify-center gap-1"
        >
          <Camera className="w-3.5 h-3.5" />
          {snapshot.isPending ? 'Criando…' : 'Snapshot agora'}
        </button>
      </div>

      <div className="flex-1 overflow-y-auto">
        {isLoading && (
          <p className="px-3 py-3 text-xs text-sibila-smoke">Carregando…</p>
        )}
        {!isLoading && versions.length === 0 && (
          <p className="px-3 py-3 text-xs text-sibila-smoke">
            Sem versões salvas. Crie um snapshot acima.
          </p>
        )}
        <ul className="divide-y divide-sibila-mist/50">
          {versions.map((v) => (
            <li key={v.id} className="px-3 py-2.5 flex items-start justify-between gap-2 hover:bg-sibila-onyx/40">
              <div className="flex-1 min-w-0">
                <div className="text-sm font-medium text-sibila-moonlight">
                  v{v.version_number}
                </div>
                <div className="text-[11px] text-sibila-smoke">
                  {v.created_at ? new Date(v.created_at).toLocaleString() : '—'}
                </div>
                {v.note && (
                  <div className="text-xs text-sibila-fog mt-1 break-words">
                    {v.note}
                  </div>
                )}
              </div>
              <button
                type="button"
                onClick={() => setVersionToRestore({ id: v.id, version_number: v.version_number })}
                disabled={restore.isPending}
                className="text-[11px] px-2 py-1 rounded border border-sibila-mist hover:border-sibila-amethyst text-sibila-fog hover:text-sibila-moonlight disabled:opacity-50 flex items-center gap-1 flex-shrink-0 transition-colors"
                title="Restaurar esta versão"
              >
                <RotateCcw className="w-3 h-3" />
                restaurar
              </button>
            </li>
          ))}
        </ul>
      </div>

      {/* Confirmation Modal (Zero native browser confirm) */}
      {versionToRestore && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-xs animate-fade-in">
          <div className="bg-zinc-900 border border-zinc-800 rounded-2xl w-full max-w-sm p-5 space-y-4 shadow-2xl">
            <h4 className="text-sm font-bold text-white flex items-center gap-2">
              <RotateCcw className="w-4 h-4 text-purple-400" />
              Restaurar Versão v{versionToRestore.version_number}?
            </h4>
            <p className="text-xs text-zinc-400 leading-relaxed">
              O fluxo atual será sobrescrito com o estado desta versão. Se desejar, crie um snapshot antes de continuar.
            </p>
            <div className="flex items-center justify-end gap-2 pt-2">
              <button
                type="button"
                onClick={() => setVersionToRestore(null)}
                className="px-3 py-1.5 rounded-lg border border-zinc-700 text-xs font-medium text-zinc-300 hover:bg-zinc-800 transition-colors"
              >
                Cancelar
              </button>
              <button
                type="button"
                disabled={restore.isPending}
                onClick={() => restore.mutate(versionToRestore.id)}
                className="px-3 py-1.5 rounded-lg bg-purple-600 hover:bg-purple-500 disabled:opacity-50 text-xs font-bold text-white transition-colors"
              >
                {restore.isPending ? 'Restaurando...' : 'Confirmar Restauração'}
              </button>
            </div>
          </div>
        </div>
      )}
    </aside>
  );
}
