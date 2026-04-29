import { useMemo, useRef, useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { Link, useNavigate } from 'react-router-dom';
import {
  ChevronDown,
  ChevronRight,
  FolderPlus,
  History,
  MoreHorizontal,
  Pencil,
  Trash2,
  Upload,
} from 'lucide-react';
import { blueprintsApi, type BlueprintSummary } from '../api/blueprints';
import { importBlueprintFromFile } from '../lib/exportImport';
import {
  addFolder,
  deleteFolder,
  folderOf,
  readFolders,
  renameFolder,
  setFolderOf,
  writeFolders,
  type FoldersState,
} from '../lib/blueprintFolders';
import { toast } from '../lib/toast';

export default function BlueprintsList() {
  const { data, isLoading, error } = useQuery({
    queryKey: ['blueprints'],
    queryFn: blueprintsApi.list,
  });
  const qc = useQueryClient();
  const navigate = useNavigate();
  const fileRef = useRef<HTMLInputElement | null>(null);

  const [folders, setFolders] = useState<FoldersState>(() => readFolders());
  const [collapsed, setCollapsed] = useState<Record<string, boolean>>({});

  const updateFolders = (next: FoldersState) => {
    setFolders(next);
    writeFolders(next);
  };

  const grouped = useMemo(() => {
    const map = new Map<string, BlueprintSummary[]>();
    for (const f of folders.folders) map.set(f.id, []);
    for (const bp of data ?? []) {
      const fid = folderOf(folders, bp.id);
      const arr = map.get(fid) ?? map.get('principal')!;
      arr.push(bp);
    }
    return map;
  }, [data, folders]);

  const onPickFile = async (file: File) => {
    const newId = await importBlueprintFromFile(file);
    if (newId) {
      qc.invalidateQueries({ queryKey: ['blueprints'] });
      navigate(`/flows/${newId}`);
    }
  };

  const handleAddFolder = () => {
    const name = window.prompt('Nome da pasta:');
    if (name && name.trim()) {
      updateFolders(addFolder(folders, name));
      toast.success('Pasta criada.');
    }
  };

  return (
    <section className="max-w-3xl mx-auto px-6 py-8">
      <div className="flex items-baseline justify-between mb-6">
        <h1 className="text-xl font-semibold">Fluxos do tenant</h1>
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={handleAddFolder}
            className="text-xs text-slate-300 hover:text-slate-100 flex items-center gap-1 px-2 py-1 rounded border border-cigana-border hover:border-cigana-purple"
            title="Criar nova pasta"
          >
            <FolderPlus className="w-3 h-3" />
            <span>Nova pasta</span>
          </button>
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
      {error && <p className="text-red-400">Erro: {(error as Error).message}</p>}
      {data && data.length === 0 && (
        <p className="text-slate-400">Nenhum fluxo cadastrado neste tenant.</p>
      )}

      {data && data.length > 0 && (
        <div className="space-y-4">
          {folders.folders.map((folder) => {
            const items = grouped.get(folder.id) ?? [];
            const isCollapsed = collapsed[folder.id];
            return (
              <div key={folder.id}>
                <div className="flex items-center justify-between mb-2 group">
                  <button
                    type="button"
                    onClick={() =>
                      setCollapsed((s) => ({ ...s, [folder.id]: !s[folder.id] }))
                    }
                    className="flex items-center gap-1.5 text-sm text-slate-300 hover:text-slate-100"
                  >
                    {isCollapsed ? (
                      <ChevronRight className="w-3.5 h-3.5" />
                    ) : (
                      <ChevronDown className="w-3.5 h-3.5" />
                    )}
                    <span className="font-medium">{folder.name}</span>
                    <span className="text-xs text-slate-500">({items.length})</span>
                  </button>
                  {!folder.system && (
                    <div className="opacity-0 group-hover:opacity-100 transition-opacity flex items-center gap-1">
                      <button
                        onClick={() => {
                          const name = window.prompt('Renomear pasta:', folder.name);
                          if (name && name.trim()) {
                            updateFolders(renameFolder(folders, folder.id, name));
                          }
                        }}
                        className="text-slate-500 hover:text-slate-200 p-1 rounded hover:bg-cigana-surface"
                        title="Renomear"
                      >
                        <Pencil className="w-3 h-3" />
                      </button>
                      <button
                        onClick={() => {
                          if (
                            confirm(
                              `Apagar "${folder.name}"? Os fluxos voltam pra Pasta Principal.`,
                            )
                          ) {
                            updateFolders(deleteFolder(folders, folder.id));
                            toast.success('Pasta removida.');
                          }
                        }}
                        className="text-slate-500 hover:text-red-400 p-1 rounded hover:bg-cigana-surface"
                        title="Apagar"
                      >
                        <Trash2 className="w-3 h-3" />
                      </button>
                    </div>
                  )}
                </div>

                {!isCollapsed && (
                  <ul className="space-y-2">
                    {items.length === 0 ? (
                      <li className="text-xs text-slate-500 italic px-1">
                        Pasta vazia.
                      </li>
                    ) : (
                      items.map((bp) => (
                        <BlueprintRow
                          key={bp.id}
                          bp={bp}
                          folders={folders}
                          onMoveTo={(fid) =>
                            updateFolders(setFolderOf(folders, bp.id, fid))
                          }
                        />
                      ))
                    )}
                  </ul>
                )}
              </div>
            );
          })}
        </div>
      )}
    </section>
  );
}

function BlueprintRow({
  bp,
  folders,
  onMoveTo,
}: {
  bp: BlueprintSummary;
  folders: FoldersState;
  onMoveTo: (folderId: string) => void;
}) {
  const [menuOpen, setMenuOpen] = useState(false);
  return (
    <li className="relative">
      <div className="flex items-center gap-2">
        <Link
          to={`/flows/${bp.id}`}
          className="flex-1 rounded border border-cigana-border bg-cigana-surface px-4 py-3 flex items-baseline justify-between hover:border-cigana-purple transition-colors"
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
        <button
          onClick={() => setMenuOpen((v) => !v)}
          className="p-2 rounded text-slate-400 hover:text-slate-100 hover:bg-cigana-surface"
          title="Mover para pasta"
        >
          <MoreHorizontal className="w-4 h-4" />
        </button>
      </div>
      {menuOpen && (
        <>
          <div
            className="fixed inset-0 z-10"
            onClick={() => setMenuOpen(false)}
          />
          <ul className="absolute right-0 mt-1 z-20 min-w-[180px] bg-cigana-surface border border-cigana-border rounded shadow-lg py-1">
            <li className="px-3 py-1 text-[10px] uppercase tracking-wide text-slate-500">
              Mover para
            </li>
            {folders.folders.map((f) => (
              <li key={f.id}>
                <button
                  onClick={() => {
                    onMoveTo(f.id);
                    setMenuOpen(false);
                  }}
                  className="w-full text-left px-3 py-1.5 text-sm text-slate-200 hover:bg-cigana-bg/60"
                >
                  {f.name}
                </button>
              </li>
            ))}
          </ul>
        </>
      )}
    </li>
  );
}
