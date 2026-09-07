import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Volume2, Sparkles, Send } from 'lucide-react';
import { audioLibraryApi } from '../api/audioLibrary';
import { handleApiError } from '../lib/handleApiError';
import { toast } from '../lib/toast';

interface Props {
  leadId: number;
}

export default function AudioSuggestPanel({ leadId }: Props) {
  const qc = useQueryClient();
  const { data, isLoading } = useQuery({
    queryKey: ['audio-suggest', leadId],
    queryFn: () => audioLibraryApi.suggest(leadId),
    staleTime: 60_000,
  });

  const sendMut = useMutation({
    mutationFn: (audioId: number) => audioLibraryApi.send(audioId, leadId),
    onSuccess: () => {
      toast.success('Áudio enviado pro lead');
      qc.invalidateQueries({ queryKey: ['leads-conversation', leadId] });
      qc.invalidateQueries({ queryKey: ['audio-suggest', leadId] });
    },
    onError: handleApiError('Erro ao enviar áudio'),
  });

  if (isLoading) return null;
  const suggestions = data?.suggestions ?? [];
  if (suggestions.length === 0) return null;

  return (
    <div className="bg-bg-surface border border-border rounded-2xl p-4 mb-3">
      <div className="flex items-center gap-2 mb-2">
        <Sparkles className="w-3.5 h-3.5 text-accent-amethyst" />
        <span className="text-[10px] font-black uppercase tracking-widest text-secondary">
          Áudios sugeridos
        </span>
        {data?.matched_category && (
          <span className="text-[9px] uppercase tracking-widest font-black text-accent-amethyst">
            · {data.matched_category}
          </span>
        )}
      </div>
      <div className="space-y-2">
        {suggestions.map((s) => (
          <div
            key={s.id}
            className="bg-bg-primary border border-border rounded-xl p-2.5 flex items-center justify-between gap-2"
          >
            <div className="flex items-center gap-2 min-w-0">
              <Volume2 className="w-3.5 h-3.5 text-accent-amethyst flex-shrink-0" />
              <div className="min-w-0">
                <div className="text-xs font-bold truncate">{s.title}</div>
                <div className="text-[10px] text-secondary">
                  {s.category || 'outro'} · {s.usage_count} uso{s.usage_count !== 1 ? 's' : ''}
                </div>
              </div>
            </div>
            <div className="flex items-center gap-1.5 flex-shrink-0">
              <audio src={s.audio_url} controls className="h-7 w-32" />
              <button
                onClick={() => sendMut.mutate(s.id)}
                disabled={sendMut.isPending}
                className="px-2.5 py-1.5 bg-accent-amethyst hover:bg-accent-amethyst/90 disabled:opacity-30 text-white rounded-lg text-[10px] font-black uppercase tracking-widest flex items-center gap-1"
              >
                <Send className="w-3 h-3" />
                Enviar
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
