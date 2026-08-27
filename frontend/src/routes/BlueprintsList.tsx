import { useMemo, useRef, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Link, useNavigate } from 'react-router-dom';
import {
  BarChart2,
  ChevronDown,
  ChevronLeft,
  Folder,
  FolderOpen,
  FolderPlus,
  Home,
  Link2,
  MessageCircle,
  MoreHorizontal,
  PauseCircle,
  Pencil,
  Play,
  Plus,
  Search,
  Trash2,
  Upload,
  Workflow,
  X,
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

const INTEGRATIONS = [
  { id: 'whatsapp', icon: 'https://upload.wikimedia.org/wikipedia/commons/6/6b/WhatsApp.svg', name: 'WhatsApp' },
  { id: 'kiwify', icon: null, text: 'Ki', name: 'Kiwify' },
  { id: 'hotmart', icon: null, text: '🔥', name: 'Hotmart' },
  { id: 'asaas', icon: null, text: 'Asaas', name: 'Asaas' },
  { id: 'stripe', icon: null, text: 'S', name: 'Stripe' },
];

export default function BlueprintsList() {
  const { data, isLoading, error } = useQuery({
    queryKey: ['blueprints'],
    queryFn: blueprintsApi.list,
  });
  const qc = useQueryClient();
  const navigate = useNavigate();

  const { mutate: createBlueprint, isPending: isCreating } = useMutation({
    mutationFn: blueprintsApi.create,
    onSuccess: (bp: BlueprintSummary) => {
      qc.invalidateQueries({ queryKey: ['blueprints'] });
      if (activeFolderId && activeFolderId !== 'principal') {
        const next = setFolderOf(folders, bp.id, activeFolderId);
        updateFolders(next);
      }
      navigate(`/flows/${bp.id}`);
    },
    onError: (err: Error) => {
      toast.error(err.message || 'Erro ao criar fluxo');
    },
  });
  const fileRef = useRef<HTMLInputElement | null>(null);

  const [folders, setFolders] = useState<FoldersState>(() => readFolders());
  const [activeFolderId, setActiveFolderId] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');

  const [modalType, setModalType] = useState<
    'createFlow' | 'createFolder' | 'renameFolder' | 'deleteFolder' | null
  >(null);
  const [modalInput, setModalInput] = useState('');
  const [targetFolderId, setTargetFolderId] = useState<string | null>(null);

  const [selectedIntegration, setSelectedIntegration] = useState('whatsapp');
  const [selectedEvent, setSelectedEvent] = useState('');

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
      if (activeFolderId && activeFolderId !== 'principal') {
        updateFolders(setFolderOf(folders, newId, activeFolderId));
      }
      navigate(`/flows/${newId}`);
    }
  };

  const handleModalSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const val = modalInput.trim();

    if (modalType === 'createFlow' && val) {
      createBlueprint({
        title: val,
        integration: selectedIntegration,
        event: selectedEvent,
      });
    } else if (modalType === 'createFolder' && val) {
      updateFolders(addFolder(folders, val));
      toast.success('Pasta criada.');
    } else if (modalType === 'renameFolder' && val && targetFolderId) {
      updateFolders(renameFolder(folders, targetFolderId, val));
    } else if (modalType === 'deleteFolder' && targetFolderId) {
      updateFolders(deleteFolder(folders, targetFolderId));
      if (activeFolderId === targetFolderId) {
        setActiveFolderId(null);
      }
      toast.success('Pasta removida.');
    }
    closeModal();
  };

  const closeModal = () => {
    setModalType(null);
    setModalInput('');
    setTargetFolderId(null);
    setSelectedIntegration('whatsapp');
    setSelectedEvent('');
  };

  const flowsInActiveFolder = activeFolderId ? (grouped.get(activeFolderId) ?? []) : [];
  const filteredFlows = flowsInActiveFolder.filter((bp) =>
    bp.title.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <section className="flex-1 overflow-y-auto bg-bg-primary text-primary flex flex-col">
      <div className="max-w-6xl w-full mx-auto px-6 py-10">
        
        <div className="flex flex-col md:flex-row md:items-center justify-between mb-8 gap-4">
          <div>
            <div className="flex items-center gap-3">
              <Workflow className="w-7 h-7 text-accent-amethyst" />
              <h1 className="text-2xl font-bold text-primary tracking-tight">Fluxos de conversa</h1>
            </div>
            <p className="text-sm text-secondary mt-1 ml-10">
              {data ? data.length : 0} fluxos cadastrados
            </p>
          </div>
          <div className="flex items-center gap-3 self-start md:self-auto ml-10 md:ml-0">
            <div className="bg-bg-surface border border-border rounded-xl px-3 py-2 flex items-center shadow-sm">
              <span className="text-sm text-secondary mr-2">Selecione uma int...</span>
              <ChevronDown className="w-4 h-4 text-secondary" />
            </div>

            <button
              type="button"
              onClick={() => {
                setModalType('createFlow');
                setModalInput('');
              }}
              disabled={isCreating}
              className="text-sm bg-[#10b981] text-white hover:bg-[#059669] flex items-center gap-2 px-5 py-2.5 rounded-xl shadow-md transition-all font-semibold disabled:opacity-50"
            >
              <Plus className="w-4 h-4" />
              <span>{isCreating ? 'Criando...' : 'Novo fluxo'}</span>
            </button>
            <button
              type="button"
              onClick={() => {
                setModalType('createFolder');
                setModalInput('');
              }}
              className="text-sm bg-bg-surface border border-border text-primary hover:bg-bg-primary flex items-center gap-2 px-5 py-2.5 rounded-xl shadow-sm transition-all font-semibold"
            >
              <FolderPlus className="w-4 h-4" />
              <span>Nova Pasta</span>
            </button>
            <button
              type="button"
              onClick={() => fileRef.current?.click()}
              className="text-sm bg-[#ec4899] text-white hover:bg-[#db2777] flex items-center gap-2 px-5 py-2.5 rounded-xl shadow-md transition-all font-semibold"
            >
              <Upload className="w-4 h-4" />
              <span>Importar Fluxo</span>
            </button>

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

        {isLoading && <p className="text-secondary ml-10">Carregando fluxos…</p>}
        {error && <p className="text-red-400 ml-10">Erro: {(error as Error).message}</p>}

        {!activeFolderId && data && (
          <div className="animate-in fade-in slide-in-from-bottom-2 duration-300">
            <div className="mb-6 flex items-center justify-between">
              <div className="flex items-center gap-2 text-primary font-semibold text-lg ml-2">
                <Home className="w-5 h-5 text-secondary" />
                Minhas pastas
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
              {folders.folders.map((folder) => {
                const count = (grouped.get(folder.id) ?? []).length;
                return (
                  <div
                    key={folder.id}
                    onClick={() => setActiveFolderId(folder.id)}
                    className="group relative cursor-pointer flex flex-col bg-bg-surface border border-border hover:border-accent-amethyst transition-all rounded-2xl p-6 shadow-sm hover:shadow-md"
                  >
                    <div className="flex items-start justify-between mb-8">
                      <Folder className="w-10 h-10 text-accent-amethyst fill-accent-amethyst/20" />
                      {!folder.system && (
                        <div className="opacity-0 group-hover:opacity-100 transition-opacity flex items-center gap-1 bg-bg-primary rounded-lg border border-border p-1">
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              setModalType('renameFolder');
                              setModalInput(folder.name);
                              setTargetFolderId(folder.id);
                            }}
                            className="text-secondary hover:text-primary p-1.5 rounded hover:bg-bg-surface"
                            title="Renomear"
                          >
                            <Pencil className="w-3.5 h-3.5" />
                          </button>
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              setModalType('deleteFolder');
                              setModalInput(folder.name);
                              setTargetFolderId(folder.id);
                            }}
                            className="text-secondary hover:text-red-400 p-1.5 rounded hover:bg-bg-surface"
                            title="Apagar"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      )}
                    </div>
                    <div>
                      <h3 className="text-lg font-bold text-primary mb-1">{folder.name}</h3>
                      <div className="flex items-center justify-between">
                        <span className="text-xs text-secondary">
                          {folder.name === 'Pasta Principal' ? 'Todos os fluxos sem pasta' : `${count} fluxo${count !== 1 ? 's' : ''}`}
                        </span>
                        <span className="text-[10px] font-bold text-primary">
                          {folder.system ? 'Pasta principal' : ''}
                        </span>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {activeFolderId && (
          <div className="animate-in fade-in slide-in-from-right-4 duration-300">
            <div className="flex items-center justify-between mb-8 border-b border-border pb-4">
              <div className="flex items-center gap-4">
                <button
                  onClick={() => setActiveFolderId(null)}
                  className="p-2.5 rounded-xl border border-border bg-bg-surface hover:bg-bg-primary transition-all text-secondary hover:text-primary shadow-sm"
                  title="Voltar para pastas"
                >
                  <ChevronLeft className="w-5 h-5" />
                </button>
                <div className="flex items-center gap-2">
                  <h2 className="text-lg font-semibold text-primary">
                    <Home className="w-4 h-4 inline-block mr-2 text-secondary mb-1" />
                    Minhas pastas / {folders.folders.find((f) => f.id === activeFolderId)?.name || 'Pasta'}
                  </h2>
                </div>
              </div>

              <div className="relative w-full max-w-lg">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                  <Search className="h-4 w-4 text-secondary" />
                </div>
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="block w-full pl-10 pr-3 py-2 border border-border rounded-xl leading-5 bg-bg-surface text-primary placeholder-secondary focus:outline-none focus:bg-bg-primary focus:ring-1 focus:ring-accent-amethyst focus:border-accent-amethyst sm:text-sm transition-colors shadow-sm"
                  placeholder="Pesquisar..."
                />
              </div>
            </div>

            {filteredFlows.length === 0 ? (
              <div className="bg-bg-surface border border-border border-dashed rounded-2xl p-12 text-center">
                <Workflow className="w-10 h-10 text-secondary/40 mx-auto mb-3" />
                <h3 className="text-primary font-medium mb-1">Nenhum fluxo encontrado</h3>
                <p className="text-sm text-secondary">
                  {searchQuery ? 'Tente outro termo de busca.' : 'Crie um novo fluxo nesta pasta para começar.'}
                </p>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {filteredFlows.map((bp) => (
                  <BlueprintCard
                    key={bp.id}
                    bp={bp}
                    folders={folders}
                    onMoveTo={(fid) => updateFolders(setFolderOf(folders, bp.id, fid))}
                  />
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      {modalType && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm px-4">
          <div className={`${modalType === 'createFlow' ? 'max-w-2xl' : 'max-w-md'} bg-bg-surface w-full rounded-2xl shadow-2xl border border-border relative animate-in fade-in zoom-in-95 duration-200 overflow-hidden`}>
            
            {modalType === 'createFlow' ? (
              <>
                <div className="bg-accent-amethyst px-6 py-4 flex items-center justify-between">
                  <div className="flex items-center gap-3 text-white">
                    <Workflow className="w-5 h-5" />
                    <h2 className="text-lg font-bold">Criar um novo fluxo</h2>
                  </div>
                  <button onClick={closeModal} className="text-white/80 hover:text-white transition-colors bg-white/20 hover:bg-white/30 rounded-full p-1">
                    <X className="w-5 h-5" />
                  </button>
                </div>

                <div className="p-8">
                  <form onSubmit={handleModalSubmit}>
                    <div className="mb-6">
                      <label className="block text-sm font-medium text-primary mb-1">
                        Título do fluxo <span className="text-red-500">*</span>
                      </label>
                      <input
                        type="text"
                        autoFocus
                        required
                        value={modalInput}
                        onChange={(e) => setModalInput(e.target.value)}
                        className="w-full bg-bg-primary border border-border rounded-xl px-4 py-3 text-primary text-sm focus:outline-none focus:border-accent-amethyst focus:ring-1 focus:ring-accent-amethyst transition-all shadow-sm"
                        placeholder="Crie um nome de fácil memorização"
                      />
                      <p className="text-[11px] text-secondary/60 mt-1">O nome deve conter no mínimo 4 caracteres</p>
                    </div>

                    <div className="grid grid-cols-5 gap-3 mb-8">
                      {INTEGRATIONS.map(int => (
                        <button
                          key={int.id}
                          type="button"
                          onClick={() => {
                            setSelectedIntegration(int.id);
                            setSelectedEvent('');
                          }}
                          className={`aspect-square rounded-xl border flex items-center justify-center transition-all bg-bg-primary ${
                            selectedIntegration === int.id 
                              ? 'border-accent-amethyst shadow-[0_0_0_1px_#8b5cf6]' 
                              : 'border-border hover:border-secondary grayscale hover:grayscale-0'
                          }`}
                          title={int.name}
                        >
                          {int.icon ? (
                            <img src={int.icon} alt={int.name} className="w-8 h-8 object-contain" />
                          ) : (
                            <span className="font-bold text-secondary text-lg">{int.text}</span>
                          )}
                        </button>
                      ))}
                    </div>

                    <div className="relative mb-6">
                      <div className="absolute inset-0 flex items-center" aria-hidden="true">
                        <div className="w-full border-t border-border"></div>
                      </div>
                      <div className="relative flex justify-center">
                        <span className="px-3 bg-bg-surface text-xs font-medium text-secondary">
                          Evento de gatilho <span className="text-primary font-bold">{INTEGRATIONS.find(i => i.id === selectedIntegration)?.name || 'WhatsApp'}</span>
                        </span>
                      </div>
                    </div>

                    <div className="mb-8">
                      <label className="block text-sm font-medium text-primary mb-1">
                        Evento <span className="text-red-500">*</span>
                      </label>
                      <select
                        required
                        value={selectedEvent}
                        onChange={(e) => setSelectedEvent(e.target.value)}
                        className="w-full bg-bg-primary border border-border rounded-xl px-4 py-3 text-primary text-sm focus:outline-none focus:border-accent-amethyst focus:ring-1 focus:ring-accent-amethyst transition-all shadow-sm appearance-none"
                      >
                        <option value="" disabled>Selecione um evento</option>
                        {selectedIntegration === 'whatsapp' ? (
                          <>
                            <option value="keyword">Mensagem de palavra-chave</option>
                            <option value="message_received">Qualquer mensagem recebida</option>
                            <option value="inicio_conversa">Início de conversa</option>
                          </>
                        ) : (
                          <>
                            <option value="purchase">Compra aprovada</option>
                            <option value="abandon">Carrinho abandonado</option>
                          </>
                        )}
                      </select>
                    </div>

                    <button
                      type="submit"
                      disabled={isCreating}
                      className="w-full bg-[#d8b4fe] hover:bg-[#c084fc] text-purple-900 font-bold py-3.5 rounded-xl shadow-md transition-all flex justify-center"
                    >
                      {isCreating ? 'Salvando...' : 'Salvar Fluxo'}
                    </button>
                    <p className="text-xs text-secondary text-center mt-3 leading-relaxed">
                      Você pode utilizar palavras ou frases como palavra-chave. O fluxo será acionado quando o cliente enviar uma mensagem exatamente igual à palavra-chave. Uma dica é copiar o texto pronto que está configurado na sua campanha de mensagem.
                    </p>
                  </form>
                </div>
              </>
            ) : (
              <div className="p-6">
                <button
                  onClick={closeModal}
                  className="absolute right-4 top-4 text-secondary hover:text-primary transition-colors"
                >
                  <X className="w-5 h-5" />
                </button>
                <h2 className="text-lg font-bold text-primary mb-1">
                  {modalType === 'createFolder' && 'Nova pasta'}
                  {modalType === 'renameFolder' && 'Renomear pasta'}
                  {modalType === 'deleteFolder' && 'Apagar pasta'}
                </h2>
                <p className="text-sm text-secondary mb-4">
                  {modalType === 'deleteFolder'
                    ? `Tem certeza que deseja apagar a pasta "${modalInput}"? Os fluxos voltarão para a Pasta Principal.`
                    : 'Insira o nome desejado abaixo.'}
                </p>
                <form onSubmit={handleModalSubmit}>
                  {modalType !== 'deleteFolder' && (
                    <input
                      type="text"
                      autoFocus
                      required
                      value={modalInput}
                      onChange={(e) => setModalInput(e.target.value)}
                      className="w-full bg-bg-primary border border-border rounded-xl px-4 py-3 text-primary text-sm focus:outline-none focus:border-accent-amethyst focus:ring-1 focus:ring-accent-amethyst transition-all mb-6 shadow-sm"
                      placeholder="Nome da pasta"
                    />
                  )}
                  <div className="flex justify-end gap-3 mt-4">
                    <button
                      type="button"
                      onClick={closeModal}
                      className="px-5 py-2.5 rounded-xl text-sm font-bold text-secondary hover:bg-bg-primary hover:text-primary transition-all border border-transparent hover:border-border"
                    >
                      Cancelar
                    </button>
                    <button
                      type="submit"
                      className={`px-5 py-2.5 rounded-xl text-sm font-bold text-white shadow-md transition-all ${
                        modalType === 'deleteFolder'
                          ? 'bg-red-500 hover:bg-red-600'
                          : 'bg-accent-amethyst hover:bg-accent-amethyst/90'
                      }`}
                    >
                      {modalType === 'deleteFolder' ? 'Apagar' : 'Confirmar'}
                    </button>
                  </div>
                </form>
              </div>
            )}
          </div>
        </div>
      )}
    </section>
  );
}

function BlueprintCard({
  bp,
  folders,
  onMoveTo,
}: {
  bp: BlueprintSummary;
  folders: FoldersState;
  onMoveTo: (folderId: string) => void;
}) {
  const [menuOpen, setMenuOpen] = useState(false);
  const isPaused = bp.slug?.includes('esmeralda');

  return (
    <div className="relative flex flex-col bg-bg-surface border border-border rounded-2xl shadow-sm hover:shadow-md transition-all bg-white">
      <div className="p-4 flex items-start justify-between">
        <div className="flex items-start gap-3">
          <div className="bg-[#25D366]/10 p-2 rounded-full">
            <MessageCircle className="w-5 h-5 text-[#25D366] fill-[#25D366]" />
          </div>
          <div>
            <Link to={`/flows/${bp.id}`} className="font-bold text-primary hover:text-accent-amethyst transition-colors block text-base leading-none mb-1.5">
              {bp.title}
            </Link>
            <div className="flex items-center text-xs text-[#3b82f6] font-medium">
              <span>Enviou palavra chave</span>
              <Link2 className="w-3.5 h-3.5 ml-1" />
            </div>
          </div>
        </div>
        <div className="text-right">
          <div className="text-xs font-bold text-primary">Automação Id:</div>
          <div className="text-xs text-secondary">#{bp.id + 75600}</div>
        </div>
      </div>
      
      <div className="h-px w-full bg-border" />

      <div className="p-3 px-4 flex items-center justify-between bg-bg-primary/50 rounded-b-2xl">
        <div className="text-xs text-secondary font-medium">
          Última execução: {isPaused ? <span className="font-bold text-primary">há 17 dias</span> : '---'}
        </div>
        
        <div className="flex items-center gap-1.5 relative">
          <button className="p-1.5 rounded-full hover:bg-bg-primary transition-colors text-accent-amethyst">
            {isPaused ? <PauseCircle className="w-5 h-5 text-red-500" /> : <Play className="w-4 h-4 fill-accent-amethyst" />}
          </button>
          <button className="p-1.5 rounded hover:bg-bg-primary transition-colors text-[#10b981]">
            <BarChart2 className="w-4 h-4" />
          </button>
          
          <button
            onClick={(e) => {
              e.preventDefault();
              setMenuOpen((v) => !v);
            }}
            className="p-1.5 rounded hover:bg-bg-primary transition-colors text-secondary border border-transparent hover:border-border"
          >
            <MoreHorizontal className="w-4 h-4" />
          </button>

          {menuOpen && (
            <>
              <div
                className="fixed inset-0 z-10"
                onClick={(e) => {
                  e.stopPropagation();
                  setMenuOpen(false);
                }}
              />
              <ul className="absolute right-0 bottom-full mb-1 z-20 w-48 bg-bg-surface border border-border rounded-xl shadow-xl py-1 overflow-hidden">
                <li className="px-4 py-2 text-[10px] uppercase font-bold tracking-widest text-secondary/60 bg-bg-primary border-b border-border">
                  Mover para pasta
                </li>
                {folders.folders.map((f) => (
                  <li key={f.id}>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        onMoveTo(f.id);
                        setMenuOpen(false);
                      }}
                      className="w-full text-left px-4 py-2.5 text-sm font-medium text-secondary hover:text-primary hover:bg-bg-primary transition-colors"
                    >
                      {f.name}
                    </button>
                  </li>
                ))}
              </ul>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
