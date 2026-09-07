import { AlertCircle } from 'lucide-react';

interface Props {
  onDiscard: () => void;
  onSave: () => void;
  onStay: () => void;
}

export default function UnsavedChangesModal({ onDiscard, onSave, onStay }: Props) {
  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/30 backdrop-blur-sm animate-fade-in"
        onClick={onStay}
      />

      {/* Modal */}
      <div className="relative bg-white rounded-2xl shadow-2xl w-[380px] p-6 flex flex-col items-center gap-4 animate-scale-in z-10">
        {/* Warning icon */}
        <div className="w-14 h-14 rounded-full border-[3px] border-orange-400 flex items-center justify-center">
          <span className="text-orange-400 text-2xl font-bold">!</span>
        </div>

        {/* Title */}
        <h3 className="text-[18px] font-bold text-slate-900 text-center">
          Alterações não salvas
        </h3>

        {/* Description */}
        <p className="text-[13px] text-slate-500 text-center leading-relaxed max-w-[280px]">
          Existem mudanças pendentes neste bloco. O que deseja fazer?
        </p>

        {/* Actions */}
        <div className="flex flex-col gap-2.5 w-full mt-1">
          {/* Save */}
          <button
            onClick={onSave}
            className="w-full py-3 rounded-xl text-white text-[13px] font-semibold flex items-center justify-center gap-2 transition-all hover:brightness-105 active:scale-[0.99]"
            style={{ background: 'linear-gradient(180deg, #059669 0%, #047857 100%)', boxShadow: '0 2px 8px rgba(5,150,105,0.35)' }}
          >
            Salvar e fechar
          </button>

          {/* Discard */}
          <button
            onClick={onDiscard}
            className="w-full py-3 rounded-xl text-white text-[13px] font-semibold flex items-center justify-center gap-2 transition-all hover:brightness-105 active:scale-[0.99]"
            style={{ background: 'linear-gradient(180deg, #ef4444 0%, #dc2626 100%)', boxShadow: '0 2px 8px rgba(239,68,68,0.35)' }}
          >
            Descartar alterações
          </button>

          {/* Stay */}
          <button
            onClick={onStay}
            className="w-full py-3 rounded-xl text-[13px] font-semibold flex items-center justify-center gap-2 transition-all hover:brightness-105 active:scale-[0.99] border-2 border-[#7c3aed] text-[#7c3aed]"
          >
            Permanecer na página
          </button>
        </div>
      </div>
    </div>
  );
}
