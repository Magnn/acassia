import { useRef, useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { Mic, Send, Square, RotateCcw } from 'lucide-react';
import { voiceApi } from '../api/voice';
import { handleApiError } from '../lib/handleApiError';
import { toast } from '../lib/toast';

interface Props {
  leadId: number;
  onSent?: () => void;
}

export default function VoiceOnlyCompose({ leadId, onSent }: Props) {
  const [recording, setRecording] = useState(false);
  const [recordedSec, setRecordedSec] = useState(0);
  const [audioBlob, setAudioBlob] = useState<Blob | null>(null);
  const [audioUrl, setAudioUrl] = useState<string | null>(null);

  const mediaRecRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const intervalRef = useRef<number | null>(null);

  const sendMut = useMutation({
    mutationFn: async () => {
      if (!audioBlob) throw new Error('sem áudio');
      const fd = new FormData();
      const ext = audioBlob.type.includes('ogg')
        ? 'ogg'
        : audioBlob.type.includes('mp4')
        ? 'm4a'
        : 'webm';
      fd.append('audio', audioBlob, `rec.${ext}`);
      fd.append('lead_id', String(leadId));
      return voiceApi.sendRecordedToLead(fd);
    },
    onSuccess: () => {
      toast.success('Áudio enviado');
      reset();
      onSent?.();
    },
    onError: handleApiError('Erro ao enviar áudio'),
  });

  const reset = () => {
    if (audioUrl) URL.revokeObjectURL(audioUrl);
    setAudioBlob(null);
    setAudioUrl(null);
    setRecordedSec(0);
  };

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mr = new MediaRecorder(stream);
      chunksRef.current = [];
      mr.ondataavailable = (e) => chunksRef.current.push(e.data);
      mr.onstop = () => {
        const blob = new Blob(chunksRef.current, { type: 'audio/webm' });
        setAudioBlob(blob);
        const url = URL.createObjectURL(blob);
        setAudioUrl(url);
        stream.getTracks().forEach((t) => t.stop());
      };
      mediaRecRef.current = mr;
      mr.start();
      setRecording(true);
      setRecordedSec(0);
      intervalRef.current = window.setInterval(() => {
        setRecordedSec((s) => s + 1);
      }, 1000);
    } catch {
      toast.error('Permissão de microfone negada');
    }
  };

  const stopRecording = () => {
    mediaRecRef.current?.stop();
    setRecording(false);
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
  };

  return (
    <div className="bg-bg-surface/80 backdrop-blur-xl border-t border-border p-6 flex-shrink-0">
      <div className="max-w-3xl mx-auto space-y-3">
        {audioBlob ? (
          <>
            <audio src={audioUrl ?? undefined} controls className="w-full h-12" />
            <div className="flex gap-2">
              <button
                onClick={reset}
                disabled={sendMut.isPending}
                className="px-4 py-3 bg-bg-primary border border-border rounded-2xl text-xs font-bold flex items-center gap-2"
              >
                <RotateCcw className="w-3.5 h-3.5" />
                Regravar
              </button>
              <button
                onClick={() => sendMut.mutate()}
                disabled={sendMut.isPending}
                className="flex-1 px-4 py-3 bg-accent-amethyst hover:bg-accent-amethyst/90 disabled:opacity-30 text-white rounded-2xl text-xs font-black uppercase tracking-widest flex items-center justify-center gap-2"
              >
                <Send className="w-3.5 h-3.5" />
                {sendMut.isPending ? 'Enviando…' : 'Enviar áudio'}
              </button>
            </div>
          </>
        ) : recording ? (
          <button
            onClick={stopRecording}
            className="w-full py-5 bg-rose-500 hover:bg-rose-600 text-white rounded-2xl font-black uppercase tracking-widest text-sm shadow-2xl flex items-center justify-center gap-3 animate-pulse"
          >
            <Square className="w-5 h-5 fill-current" />
            ● Gravando — toque pra parar ({recordedSec}s)
          </button>
        ) : (
          <button
            onClick={startRecording}
            className="w-full py-5 bg-accent-amethyst hover:bg-accent-amethyst/90 text-white rounded-2xl font-black uppercase tracking-widest text-sm shadow-2xl flex items-center justify-center gap-3"
          >
            <Mic className="w-5 h-5" />
            Toque pra gravar
          </button>
        )}
        <div className="text-center text-[10px] uppercase tracking-widest text-secondary">
          Modo áudio • só voz, sem texto
        </div>
      </div>
    </div>
  );
}
