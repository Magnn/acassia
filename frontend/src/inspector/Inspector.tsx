import { useState, useRef, useEffect, useCallback } from 'react';
import type { Node } from '@xyflow/react';
import { SquarePen, Check } from 'lucide-react';
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
      <aside className="w-[340px] flex-shrink-0 border-l border-slate-200 bg-white flex flex-col h-full animate-slide-in-right shadow-xl">
        {/* Header — title (editable) + rename icon */}
        <header className="flex items-center justify-between px-4 py-3 border-b border-slate-200 flex-shrink-0 bg-white min-h-[48px]">
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
              className="flex-1 text-[15px] font-semibold text-slate-900 tracking-tight border border-[#7c3aed] rounded-md px-2 py-1 outline-none focus:ring-2 focus:ring-[#7c3aed]/30 mr-2"
            />
          ) : (
            <span className="text-[15px] font-semibold text-slate-900 tracking-tight">
              {node.data.label || v.label}
            </span>
          )}
          <button
            type="button"
            className="w-7 h-7 rounded-md text-slate-400 hover:text-[#7c3aed] hover:bg-slate-100 flex items-center justify-center transition-colors"
            title={editing ? "Confirmar" : "Renomear"}
            onClick={() => {
              if (editing) {
                confirmRename();
              } else {
                setEditing(true);
              }
            }}
          >
            {editing ? <Check className="w-4 h-4 text-[#059669]" /> : <SquarePen className="w-4 h-4" />}
          </button>
        </header>

        {/* Dirty indicator */}
        {isDirty && (
          <div className="px-4 py-1.5 bg-amber-50 border-b border-amber-200 flex items-center gap-2">
            <div className="w-2 h-2 rounded-full bg-amber-400 animate-pulse" />
            <span className="text-[11px] text-amber-700 font-medium">Alterações não salvas</span>
          </div>
        )}

        {/* Body — type-specific inspector */}
        <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4 custom-scrollbar">
          {renderTypeBody(inspectorProps)}
        </div>

        {/* Footer — Salvar button */}
        <footer className="px-4 py-3 border-t border-slate-100 flex-shrink-0"
          style={{ background: 'linear-gradient(180deg, #fff 0%, #f8fafc 100%)', boxShadow: '0 -4px 12px rgba(15,23,42,0.04)' }}
        >
          <button
            type="button"
            onClick={handleSave}
            disabled={!isDirty}
            className={[
              "w-full py-3 rounded-xl text-[13px] font-semibold flex items-center justify-center gap-2 transition-all active:scale-[0.99]",
              isDirty
                ? "text-white hover:brightness-105"
                : "text-white/70 cursor-default"
            ].join(' ')}
            style={{
              background: isDirty
                ? 'linear-gradient(180deg, #059669 0%, #047857 100%)'
                : 'linear-gradient(180deg, #94a3b8 0%, #64748b 100%)',
              boxShadow: isDirty
                ? '0 2px 8px rgba(5,150,105,0.35)'
                : 'none',
            }}
          >
            {isDirty ? '✓ Salvar Dados' : 'Salvo'}
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
