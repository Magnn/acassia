import { useState } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import {
  X, Wand2, Send, Volume2, AlertCircle, CheckCircle2,
} from 'lucide-react';
import { voiceApi, type VoiceClone } from '../api/voice';
import { handleApiError } from '../lib/handleApiError';
import { toast } from '../lib/toast';

interface Props {
  leadId: number;
  leadName: string;
  onClose: () => void;
  onSent?: () => void;
}

export default function AudioComposeModal({
  leadId, leadName, onClose, onSent,
}: Props) {
  const [text, setText] = useState('');
  const [selectedVoice, setSelectedVoice] = useState<number | undefined>(undefined);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);

  const { data: clonesData, isLoading: loadingClones } = useQuery({
    queryKey: ['voice-clones'],
    queryFn: voiceApi.list,
  });

  const clones = (clonesData?.clones ?? []).filter((c) => c.status === 'active');
  const defaultClone = clones.find((c) => c.is_default);
  const effectiveClone = selectedVoice
    ? clones.find((c) => c.id === selectedVoice)
    : defaultClone;

  const sendMut = useMutation({
    mutationFn: () => voiceApi.sendToLead({
      lead_id: leadId,
      text: text.trim(),
      voice_clone_id: selectedVoice,
    }),
    onSuccess: (res) => {
      toast.success(`Áudio enviado (${res.chars_count} chars)`);
      setPreviewUrl(res.audio_url);
      onSent?.();
    },
    onError: handleApiError('Erro ao enviar áudio'),
  });

  const valid = text.trim().length >= 3 && text.length <= 5000 && effectiveClone !== undefined;

  return (
    <div className="fixed inset-0 z-50 bg-black/70 flex items-center justify-center p-6">
      <div className="bg-bg-surface border border-border rounded-3xl max-w-lg w-full overflow-hidden">
        <div className="p-5 border-b border-border flex items-start justify-between">
          <div>
            <h2 className="text-xl font-black tracking-tight flex items-center gap-2">
              <Volume2 className="w-5 h-5 text-accent-amethyst" />
              Áudio na sua voz
            </h2>
            <p className="text-xs text-secondary mt-1">
              Para {leadName}. Texto vira áudio na voz clonada e vai direto pro WhatsApp.
            </p>
          </div>
          <button onClick={onClose} className="text-secondary hover:text-primary">
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="p-5 space-y-4">
          {loadingClones ? (
            <div className="text-secondary text-sm">Carregando vozes…</div>
          ) : clones.length === 0 ? (
            <div className="bg-amber-500/5 border border-amber-500/30 rounded-2xl p-4 flex items-start gap-2">
              <AlertCircle className="w-4 h-4 text-amber-400 flex-shrink-0 mt-0.5" />
              <div className="text-xs text-amber-200">
                Nenhuma voz clonada ativa. Vá em <strong>/voice</strong> e grave 1min de áudio
                para clonar sua voz.
              </div>
            </div>
          ) : !defaultClone && !selectedVoice ? (
            <div className="bg-amber-500/5 border border-amber-500/30 rounded-2xl p-4 flex items-start gap-2">
              <AlertCircle className="w-4 h-4 text-amber-400 flex-shrink-0 mt-0.5" />
              <div className="text-xs text-amber-200">
                Sem voz padrão definida. Selecione abaixo ou marque uma como padrão em <strong>/voice</strong>.
              </div>
            </div>
          ) : null}

          {clones.length > 0 && (
            <div>
              <label className="text-[10px] font-black uppercase tracking-widest text-secondary block mb-1.5">
                Voz
              </label>
              <select
                value={selectedVoice ?? defaultClone?.id ?? ''}
                onChange={(e) => setSelectedVoice(Number(e.target.value) || undefined)}
                className="w-full bg-bg-primary border border-border rounded-xl px-3 py-2.5 text-sm"
              >
                {clones.map((c: VoiceClone) => (
                  <option key={c.id} value={c.id}>
                    {c.name}{c.is_default ? ' (padrão)' : ''}
                  </option>
                ))}
              </select>
            </div>
          )}

          <div>
            <label className="text-[10px] font-black uppercase tracking-widest text-secondary block mb-1.5">
              O que falar?
            </label>
            <textarea
              value={text}
              onChange={(e) => setText(e.target.value)}
              rows={5}
              maxLength={5000}
              placeholder="Olá, querida. Sinto que algo aqui pediu pra eu te falar diretamente…"
              className="w-full bg-bg-primary border border-border rounded-xl px-4 py-3 text-sm resize-none"
              autoFocus
            />
            <div className="flex justify-between items-center mt-1">
              <span className="text-[10px] text-secondary">{text.length}/5000</span>
              {text.length > 4500 && (
                <span className="text-[10px] text-amber-400">Próximo do limite</span>
              )}
            </div>
          </div>

          {previewUrl && (
            <div className="bg-emerald-500/5 border border-emerald-500/30 rounded-2xl p-4 space-y-2">
              <div className="flex items-center gap-2 text-[11px] text-emerald-400 font-bold">
                <CheckCircle2 className="w-3.5 h-3.5" />
                Enviado para o WhatsApp
              </div>
              <audio src={previewUrl} controls className="w-full h-10" />
            </div>
          )}
        </div>

        <div className="p-4 border-t border-border flex gap-2">
          <button
            onClick={onClose}
            className="flex-1 px-3 py-2.5 bg-bg-primary border border-border rounded-xl text-xs font-bold"
          >
            Fechar
          </button>
          <button
            onClick={() => sendMut.mutate()}
            disabled={!valid || sendMut.isPending}
            className="flex-1 px-3 py-2.5 bg-accent-amethyst hover:bg-accent-amethyst/90 disabled:opacity-30 text-white rounded-xl text-xs font-black uppercase tracking-widest flex items-center justify-center gap-2"
          >
            {sendMut.isPending ? (
              <>
                <Wand2 className="w-3.5 h-3.5 animate-pulse" />
                Gerando…
              </>
            ) : (
              <>
                <Send className="w-3.5 h-3.5" />
                Gerar e enviar
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
