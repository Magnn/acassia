// Pastas para organizar blueprints — só localStorage, sem backend.
// Compatível com a chave do dashboard.html original (meumisterio_flux_folders_v1).

const KEY = 'meumisterio_flux_folders_v1';

export interface Folder {
  id: string;
  name: string;
  system?: boolean;
}

export interface FoldersState {
  folders: Folder[];
  /** map blueprintId (number stringified) -> folderId */
  flowFolder: Record<string, string>;
}

const PRINCIPAL: Folder = { id: 'principal', name: 'Pasta Principal', system: true };

export function readFolders(): FoldersState {
  try {
    const raw = localStorage.getItem(KEY);
    if (!raw) return { folders: [PRINCIPAL], flowFolder: {} };
    const j = JSON.parse(raw);
    if (!j || !Array.isArray(j.folders)) throw new Error('bad');
    if (!j.flowFolder || typeof j.flowFolder !== 'object') j.flowFolder = {};
    if (!j.folders.some((f: Folder) => f?.id === 'principal')) {
      j.folders.unshift(PRINCIPAL);
    }
    return j as FoldersState;
  } catch {
    return { folders: [PRINCIPAL], flowFolder: {} };
  }
}

export function writeFolders(st: FoldersState) {
  try {
    localStorage.setItem(KEY, JSON.stringify(st));
  } catch {}
}

export function folderOf(state: FoldersState, blueprintId: number): string {
  return state.flowFolder[String(blueprintId)] || 'principal';
}

export function setFolderOf(
  state: FoldersState,
  blueprintId: number,
  folderId: string,
): FoldersState {
  return {
    ...state,
    flowFolder: { ...state.flowFolder, [String(blueprintId)]: folderId },
  };
}

export function addFolder(state: FoldersState, name: string): FoldersState {
  const trimmed = name.trim();
  if (!trimmed) return state;
  const id = `f-${Date.now().toString(36)}`;
  return {
    ...state,
    folders: [...state.folders, { id, name: trimmed }],
  };
}

export function renameFolder(
  state: FoldersState,
  folderId: string,
  name: string,
): FoldersState {
  const trimmed = name.trim();
  if (!trimmed) return state;
  return {
    ...state,
    folders: state.folders.map((f) =>
      f.id === folderId && !f.system ? { ...f, name: trimmed } : f,
    ),
  };
}

export function deleteFolder(state: FoldersState, folderId: string): FoldersState {
  if (folderId === 'principal') return state;
  // Move tudo dessa pasta para "principal".
  const newMap: Record<string, string> = {};
  for (const [bp, fid] of Object.entries(state.flowFolder)) {
    newMap[bp] = fid === folderId ? 'principal' : fid;
  }
  return {
    folders: state.folders.filter((f) => f.id !== folderId),
    flowFolder: newMap,
  };
}
