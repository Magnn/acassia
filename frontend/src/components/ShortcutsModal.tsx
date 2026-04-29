import { useEffect } from 'react';
import { Keyboard, X } from 'lucide-react';

interface Props {
  open: boolean;
  onClose: () => void;
}

interface Shortcut {
  keys: string[];
  description: string;
}

const SHORTCUTS: { section: string; items: Shortcut[] }[] = [
  {
    section: 'Edição',
    items: [
      { keys: ['Ctrl', 'Z'], description: 'Desfazer' },
      { keys: ['Ctrl', 'Shift', 'Z'], description: 'Refazer' },
      { keys: ['Ctrl', 'Y'], description: 'Refazer (alternativo)' },
      { keys: ['Delete'], description: 'Apagar nó/aresta selecionada' },
      { keys: ['Backspace'], description: 'Apagar nó/aresta selecionada' },
      { keys: ['Esc'], description: 'Fechar inspetor / modal / deselecionar' },
    ],
  },
  {
    section: 'Canvas',
    items: [
      { keys: ['Mouse'], description: 'Arrastar fundo para mover (pan)' },
      { keys: ['Scroll'], description: 'Zoom in/out' },
      { keys: ['Click'], description: 'Selecionar nó ou aresta' },
      { keys: ['Drag'], description: 'Mover nó (modo edição)' },
    ],
  },
  {
    section: 'Construção',
    items: [
      { keys: ['Drag'], description: 'Arrastar item da paleta para o canvas' },
      { keys: ['Drag handle'], description: 'Conectar dois nós (alça → alça)' },
    ],
  },
  {
    section: 'Ajuda',
    items: [
      { keys: ['?'], description: 'Mostrar/ocultar este painel' },
    ],
  },
];

export default function ShortcutsModal({ open, onClose }: Props) {
  useEffect(() => {
    if (!open) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-[100] bg-black/60 backdrop-blur-sm flex items-center justify-center p-4 animate-[fadeIn_0.15s_ease-out]"
      onClick={onClose}
    >
      <div
        className="bg-cigana-surface border border-cigana-border rounded-xl shadow-2xl max-w-lg w-full max-h-[80vh] overflow-hidden flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        <header className="flex items-center justify-between px-5 py-3 border-b border-cigana-border flex-shrink-0">
          <div className="flex items-center gap-2">
            <Keyboard className="w-4 h-4 text-cigana-purple" />
            <h3 className="font-semibold text-sm text-slate-100">
              Atalhos de teclado
            </h3>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-slate-100 p-1 rounded hover:bg-cigana-bg"
            title="Fechar (Esc)"
          >
            <X className="w-4 h-4" />
          </button>
        </header>

        <div className="overflow-y-auto px-5 py-4 space-y-5">
          {SHORTCUTS.map((s) => (
            <section key={s.section}>
              <h4 className="text-[11px] uppercase tracking-wide text-slate-400 mb-2">
                {s.section}
              </h4>
              <ul className="space-y-1.5">
                {s.items.map((it, i) => (
                  <li
                    key={i}
                    className="flex items-center justify-between text-sm"
                  >
                    <span className="text-slate-300">{it.description}</span>
                    <span className="flex items-center gap-1 flex-shrink-0">
                      {it.keys.map((k, j) => (
                        <kbd
                          key={j}
                          className="px-1.5 py-0.5 text-[11px] font-mono rounded border border-cigana-border bg-cigana-bg text-slate-200"
                        >
                          {k}
                        </kbd>
                      ))}
                    </span>
                  </li>
                ))}
              </ul>
            </section>
          ))}
        </div>

        <footer className="px-5 py-2.5 border-t border-cigana-border text-[11px] text-slate-500 flex-shrink-0">
          Pressione <kbd className="px-1 py-0.5 font-mono rounded bg-cigana-bg border border-cigana-border">Esc</kbd> ou clique fora para fechar.
        </footer>
      </div>
    </div>
  );
}
