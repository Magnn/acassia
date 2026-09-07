import { useState, useRef, useEffect, useCallback } from 'react';
import type { Node } from '@xyflow/react';
import { SquarePen, Check, X } from 'lucide-react';
import type { FlowNodeData } from '../lib/adapt';
import { visualForType } from '../builder/nodeStyles';
import {
  AbSplitInspector,
  AnotacaoInspector,
  ApiInspector,
  CondicaoInspector,
  ConteudoInspector,
  DelayInspector,
  EndInspector,
  GptInspector,
  MotorRefInspector,
  TriggerInspector,
  AcaoInspector,
  IntegrationInspector,
  VoiceStudioInspector,
  AgenteIaInspector,
  MenuInspector,
  ExpedienteInspector,
  NotificarAtendenteInspector,
} from './inspectors';
import PerguntaInspector from './pergunta/PerguntaInspector';
import type { InspectorProps } from './helpers';
import UnsavedChangesModal from './UnsavedChangesModal';
import { toast } from '../lib/toast';

interface Props {
  node: Node<FlowNodeData>;
  onUpdate: (patch: Partial<FlowNodeData>) => void;
  onClose: () => void;
  onDirtyChange?: (dirty: boolean) => void;
  onRequestCloseRef?: React.MutableRefObject<(() => void) | null>;
}

export default function Inspector({ node, onUpdate, onClose, onDirtyChange, onRequestCloseRef }: Props) {
  const v = visualForType(node.data.meumisterioType);

  // ── Rename inline state ──
  const [editing, setEditing] = useState(false);
  const [editValue, setEditValue] = useState(node.data.label || v.label);
  const inputRef = useRef<HTMLInputElement>(null);

  // ── Dirty tracking ──
  // Snapshot of node data when inspector opens (or after save)
  const snapshotRef = useRef<string>(JSON.stringify(node.data));
  const [isDirty, setIsDirty] = useState(false);
  const [showModal, setShowModal] = useState(false);

  // Capture snapshot when node changes (opening a different node)
  useEffect(() => {
    snapshotRef.current = JSON.stringify(node.data);
    setIsDirty(false);
    setShowModal(false);
    setEditValue(node.data.label || v.label);
    setEditing(false);
  }, [node.id]);

  // Check dirty on every render by comparing current data to snapshot
  useEffect(() => {
    const current = JSON.stringify(node.data);
    setIsDirty(current !== snapshotRef.current);
  }, [node.data]);

  // Sync dirty state with parent (Builder)
  useEffect(() => {
    onDirtyChange?.(isDirty);
  }, [isDirty, onDirtyChange]);

  // ── Close attempt: check dirty ──
  const requestClose = useCallback(() => {
    if (isDirty) {
      setShowModal(true);
    } else {
      onClose();
    }
  }, [isDirty, onClose]);

  // Expose requestClose to parent so canvas clicks can trigger the modal
  useEffect(() => {
    if (onRequestCloseRef) {
      onRequestCloseRef.current = requestClose;
    }
    return () => {
      if (onRequestCloseRef) onRequestCloseRef.current = null;
    };
  }, [requestClose, onRequestCloseRef]);

  // Ensure dirty state is reset ONLY on unmount
  useEffect(() => {
    return () => {
      onDirtyChange?.(false);
    };
  }, [onDirtyChange]);

  // Auto-focus input when editing starts
  useEffect(() => {
    if (editing && inputRef.current) {
      inputRef.current.focus();
      inputRef.current.select();
    }
  }, [editing]);

  const confirmRename = () => {
    const trimmed = editValue.trim();
    if (trimmed && trimmed !== (node.data.label || v.label)) {
      onUpdate({ label: trimmed });
    }
    setEditing(false);
  };

  // ── Validation: check for empty/incomplete content ──
  const validateBeforeSave = useCallback((): string | null => {
    const cfg = node.data.config;
    const type = node.data.meumisterioType;

    if (type === 'conteudo') {
      const contents = cfg.contents;
      if (Array.isArray(contents)) {
        for (let i = 0; i < contents.length; i++) {
          const card = contents[i] as any;
          if (card.type === 'text' && (!card.value || !card.value.trim())) {
            return `O card de Texto ${i + 1} está vazio. Preencha ou remova-o.`;
          }
          if (['image', 'audio', 'video', 'document'].includes(card.type)) {
            if (!card.value?.url || !card.value.url.trim()) {
              const labels: Record<string, string> = { image: 'Imagem', audio: 'Áudio', video: 'Vídeo', document: 'Documento' };
              return `O card de ${labels[card.type] || card.type} ${i + 1} não tem arquivo. Faça upload ou remova-o.`;
            }
          }
        }
      }
    }

    if (type === 'pergunta') {
      const q = cfg.question || cfg.body || cfg.question_text;
      if (!q || !(q as string).trim()) {
        return 'O texto da pergunta está vazio.';
      }
      // save_to_flow_field é opcional (igual ao legado)
      const qr = Array.isArray(cfg.quick_replies) ? (cfg.quick_replies as string[]) : [];
      const emptyQr = qr.findIndex((r) => !r.trim());
      if (emptyQr >= 0) {
        return `A opção de resposta rápida ${emptyQr + 1} está vazia. Preencha ou remova-a.`;
      }
    }

    if (type === 'gpt') {
      if (!cfg.system_prompt || !(cfg.system_prompt as string).trim()) {
        return 'O system prompt está vazio.';
      }
    }

    if (type === 'api') {
      if (!cfg.url || !(cfg.url as string).trim()) {
        return 'A URL da API está vazia.';
      }
    }

    return null; // valid
  }, [node.data]);

  // ── Save: validate then update snapshot ──
  const handleSave = useCallback(() => {
    const error = validateBeforeSave();
    if (error) {
      toast.error(error);
      return false;
    }
    snapshotRef.current = JSON.stringify(node.data);
    setIsDirty(false);
    toast.success('Configuração salva com sucesso!');
    return true;
  }, [node.data, validateBeforeSave]);

  const handleSaveAndClose = useCallback(() => {
    const saved = handleSave();
    if (saved) {
      setShowModal(false);
      onClose();
    } else {
      setShowModal(false); // close modal but stay in inspector
    }
  }, [handleSave, onClose]);

  // ── Discard: restore snapshot + close ──
  const handleDiscard = useCallback(() => {
    try {
      const original = JSON.parse(snapshotRef.current) as FlowNodeData;
      onUpdate(original);
    } catch { /* ignore */ }
    setShowModal(false);
    setIsDirty(false);
    onClose();
  }, [onUpdate, onClose]);

  // ── Stay: dismiss modal ──
  const handleStay = useCallback(() => {
    setShowModal(false);
  }, []);

  const inspectorProps: InspectorProps = { node, onUpdate };

  return (
    <>
      <aside className="w-[360px] flex-shrink-0 border-l border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-950 flex flex-col h-full animate-slide-in-right shadow-2xl z-30 font-sans">
        {/* Header — title (editable) + rename icon + close icon */}
        <header className="flex items-center justify-between px-5 py-3.5 border-b border-zinc-200 dark:border-zinc-800 flex-shrink-0 bg-white dark:bg-zinc-950 min-h-[52px]">
          {editing ? (
            <input
              ref={inputRef}
              type="text"
              value={editValue}
              onChange={(e) => setEditValue(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') confirmRename();
                if (e.key === 'Escape') { setEditValue(node.data.label || v.label); setEditing(false); }
              }}
              onBlur={confirmRename}
              className="flex-1 text-sm font-semibold text-zinc-900 dark:text-zinc-100 tracking-tight border border-indigo-500 rounded-xl px-2.5 py-1.5 outline-none focus:ring-2 focus:ring-indigo-500/30 mr-2 bg-zinc-50 dark:bg-zinc-900"
            />
          ) : (
            <div className="flex flex-col min-w-0 pr-2">
              <span className="text-sm font-semibold text-zinc-900 dark:text-zinc-100 tracking-tight truncate">
                {node.data.label || v.label}
              </span>
              <span className="text-[10px] text-zinc-400 font-medium uppercase tracking-wider">
                Configurar Parâmetros
              </span>
            </div>
          )}

          <div className="flex items-center gap-1 shrink-0">
            <button
              type="button"
              className="w-7 h-7 rounded-lg text-zinc-400 hover:text-indigo-600 dark:hover:text-indigo-400 hover:bg-zinc-100 dark:hover:bg-zinc-800 flex items-center justify-center transition-colors"
              title={editing ? "Confirmar" : "Renomear"}
              onClick={() => {
                if (editing) {
                  confirmRename();
                } else {
                  setEditing(true);
                }
              }}
            >
              {editing ? <Check className="w-4 h-4 text-emerald-600" /> : <SquarePen className="w-4 h-4" />}
            </button>

            <button
              type="button"
              className="w-7 h-7 rounded-lg text-zinc-400 hover:text-zinc-700 dark:hover:text-zinc-200 hover:bg-zinc-100 dark:hover:bg-zinc-800 flex items-center justify-center transition-colors"
              title="Fechar painel"
              onClick={requestClose}
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </header>

        {/* Dirty indicator */}
        {isDirty && (
          <div className="px-5 py-1.5 bg-amber-50 dark:bg-amber-950/40 border-b border-amber-200/60 dark:border-amber-900/40 flex items-center gap-2">
            <div className="w-2 h-2 rounded-full bg-amber-500 animate-pulse" />
            <span className="text-[11px] text-amber-700 dark:text-amber-400 font-medium">Alterações não salvas</span>
          </div>
        )}

        {/* Body — type-specific inspector */}
        <div className="flex-1 overflow-y-auto px-5 py-4 space-y-4 custom-scrollbar text-zinc-800 dark:text-zinc-200">
          {renderTypeBody(inspectorProps)}
        </div>

        {/* Footer — Salvar button */}
        <footer className="px-5 py-3.5 border-t border-zinc-100 dark:border-zinc-800/80 bg-zinc-50/50 dark:bg-zinc-950 flex-shrink-0">
          <button
            type="button"
            onClick={handleSave}
            disabled={!isDirty}
            className={[
              "w-full py-2.5 rounded-xl text-xs font-semibold flex items-center justify-center gap-2 transition-all shadow-xs",
              isDirty
                ? "bg-emerald-600 hover:bg-emerald-700 text-white shadow-emerald-500/20 active:scale-[0.99]"
                : "bg-zinc-100 dark:bg-zinc-800 text-zinc-400 dark:text-zinc-500 cursor-default"
            ].join(' ')}
          >
            {isDirty ? '✓ Salvar Alterações' : 'Configurações Salvas'}
          </button>
        </footer>
      </aside>

      {/* Unsaved changes modal */}
      {showModal && (
        <UnsavedChangesModal
          onSave={handleSaveAndClose}
          onDiscard={handleDiscard}
          onStay={handleStay}
        />
      )}
    </>
  );
}

function renderTypeBody(p: InspectorProps) {
  switch (p.node.data.meumisterioType) {
    case 'trigger':
      return <TriggerInspector {...p} />;
    case 'conteudo':
      return <ConteudoInspector {...p} />;
    case 'pergunta':
      return <PerguntaInspector {...p} />;
    case 'acao':
      return <AcaoInspector {...p} />;
    case 'delay':
      return <DelayInspector {...p} />;
    case 'expediente':
      return <ExpedienteInspector {...p} />;
    case 'notificar_atendente':
      return <NotificarAtendenteInspector {...p} />;
    case 'menu':
      return <MenuInspector {...p} />;
    case 'condicao':
      return <CondicaoInspector {...p} />;
    case 'gpt':
      return <GptInspector {...p} />;
    case 'api':
      return <ApiInspector {...p} />;
    case 'integration':
      return <IntegrationInspector {...p} />;
    case 'voice_studio':
      return <VoiceStudioInspector {...p} />;
    case 'agente_ia':
      return <AgenteIaInspector {...p} />;
    case 'ab_split':
      return <AbSplitInspector {...p} />;
    case 'motor_ref':
      return <MotorRefInspector {...p} />;
    case 'anotacao':
      return <AnotacaoInspector {...p} />;
    case 'end':
      return <EndInspector />;
    default:
      return (
        <p className="text-[11px] text-secondary">
          Tipo "{p.node.data.meumisterioType}" sem inspetor dedicado ainda.
        </p>
      );
  }
}
