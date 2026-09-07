import { useState } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import {
  Wand2, Zap, Search, RefreshCw, Settings as SettingsIcon, X, Volume2,
} from 'lucide-react';
import { composeApi, type QuickReply, type Suggestion } from '../api/compose';
import { handleApiError } from '../lib/handleApiError';

interface Props {
  leadId: number;
  onInsert: (text: string) => void;
  onOpenManager: () => void;
  onOpenAudio?: () => void;
}

export default function ComposeToolbar({ leadId, onInsert, onOpenManager, onOpenAudio }: Props) {
  const [aiOpen, setAiOpen] = useState(false);
  const [tplOpen, setTplOpen] = useState(false);

  return (
    <div className="flex items-center gap-2 mb-2">
      <button
        type="button"
        onClick={() => { setAiOpen((v) => !v); setTplOpen(false); }}
        title="Sugestões IA"
        className={`p-2 rounded-lg border transition-all ${
          aiOpen ? 'bg-accent-amethyst text-white border-accent-amethyst' : 'bg-bg-primary border-border hover:border-accent-amethyst/30 text-secondary'
        }`}
      >
        <Wand2 className="w-3.5 h-3.5" />
      </button>
      <button
        type="button"
        onClick={() => { setTplOpen((v) => !v); setAiOpen(false); }}
        title="Templates rápidos (1-9)"
        className={`p-2 rounded-lg border transition-all ${
          tplOpen ? 'bg-accent-amethyst text-white border-accent-amethyst' : 'bg-bg-primary border-border hover:border-accent-amethyst/30 text-secondary'
        }`}
      >
        <Zap className="w-3.5 h-3.5" />
      </button>
      {onOpenAudio && (
        <button
          type="button"
          onClick={onOpenAudio}
          title="Enviar áudio na voz clonada"
          className="p-2 rounded-lg border bg-bg-primary border-border hover:border-accent-amethyst/30 text-secondary transition-all"
        >
          <Volume2 className="w-3.5 h-3.5" />
        </button>
      )}
      <span className="text-[10px] text-secondary ml-1">
        Atalhos: Ctrl+Enter envia · 1-9 templates
      </span>

      {aiOpen && (
        <SuggestionsPopover
          leadId={leadId}
          onPick={(text) => { onInsert(text); setAiOpen(false); }}
          onClose={() => setAiOpen(false)}
        />
      )}

      {tplOpen && (
        <TemplatesPopover
          leadId={leadId}
          onPick={(text) => { onInsert(text); setTplOpen(false); }}
          onClose={() => setTplOpen(false)}
          onManage={() => { onOpenManager(); setTplOpen(false); }}
        />
      )}
    </div>
  );
}

function SuggestionsPopover({
  leadId, onPick, onClose,
}: {
  leadId: number;
  onPick: (t: string) => void;
  onClose: () => void;
}) {
  const { data, refetch, isFetching } = useQuery({
    queryKey: ['ai-suggestions', leadId],
    queryFn: () => composeApi.suggestions(leadId, false),
    staleTime: 0,
  });
  const refreshMut = useMutation({
    mutationFn: () => composeApi.suggestions(leadId, true),
    onSuccess: () => refetch(),
    onError: handleApiError('Erro ao gerar sugestões'),
  });
  const items = data?.suggestions ?? [];
  const cached = data?.cached;

  const toneColor: Record<string, string> = {
    cta: 'border-amber-400/40',
    pergunta: 'border-sky-400/40',
    empatico: 'border-rose-400/40',
    conexao: 'border-accent-amethyst/40',
  };

  return (
    <div className="absolute bottom-full left-0 mb-2 w-full max-w-[640px] bg-bg-surface border border-border rounded-2xl shadow-2xl p-4 z-30">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-[10px] font-black uppercase tracking-widest text-secondary flex items-center gap-1.5">
          <Wand2 className="w-3 h-3" />
          Sugestões IA
          {cached && <span className="text-[9px] opacity-60 normal-case">(cache)</span>}
        </h3>
        <div className="flex items-center gap-2">
          <button
            onClick={() => refreshMut.mutate()}
            disabled={refreshMut.isPending || isFetching}
            className="text-[10px] text-secondary hover:text-primary flex items-center gap-1 font-bold"
          >
            <RefreshCw className={`w-3 h-3 ${(refreshMut.isPending || isFetching) ? 'animate-spin' : ''}`} />
            Refresh
          </button>
          <button onClick={onClose} className="text-secondary hover:text-primary">
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {isFetching && items.length === 0 ? (
        <div className="text-center text-secondary text-xs py-6">Gerando sugestões…</div>
      ) : items.length === 0 ? (
        <div className="text-center text-secondary text-xs py-6">Sem sugestões.</div>
      ) : (
        <div className="space-y-2">
          {items.map((s: Suggestion, i) => (
            <button
              key={i}
              onClick={() => onPick(s.text)}
              className={`w-full text-left px-4 py-3 bg-bg-primary border ${toneColor[s.tone] || 'border-border'} rounded-xl hover:bg-bg-surface transition-all`}
            >
              <div className="text-[9px] font-black uppercase tracking-widest text-secondary mb-1">
                {s.tone}
              </div>
              <div className="text-xs text-primary leading-relaxed">{s.text}</div>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

function TemplatesPopover({
  leadId, onPick, onClose, onManage,
}: {
  leadId: number;
  onPick: (t: string) => void;
  onClose: () => void;
  onManage: () => void;
}) {
  const [search, setSearch] = useState('');
  const { data, isLoading } = useQuery({
    queryKey: ['quick-replies'],
    queryFn: composeApi.list,
  });
  const renderMut = useMutation({
    mutationFn: (id: number) => composeApi.render(id, leadId),
    onSuccess: (res) => onPick(res.text),
    onError: handleApiError('Erro ao usar template'),
  });

  const items = (data?.quick_replies ?? []).filter((q: QuickReply) => {
    if (!search) return true;
    const s = search.toLowerCase();
    return q.title.toLowerCase().includes(s) || q.body.toLowerCase().includes(s);
  });

  return (
    <div className="absolute bottom-full left-0 mb-2 w-full max-w-[640px] bg-bg-surface border border-border rounded-2xl shadow-2xl p-4 z-30">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-[10px] font-black uppercase tracking-widest text-secondary flex items-center gap-1.5">
          <Zap className="w-3 h-3" />
          Templates rápidos
        </h3>
        <div className="flex items-center gap-2">
          <button
            onClick={onManage}
            className="text-[10px] text-secondary hover:text-primary flex items-center gap-1 font-bold"
          >
            <SettingsIcon className="w-3 h-3" />
            Gerenciar
          </button>
          <button onClick={onClose} className="text-secondary hover:text-primary">
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      <div className="flex items-center gap-2 bg-bg-primary border border-border rounded-xl px-3 py-2 mb-3">
        <Search className="w-3.5 h-3.5 text-secondary" />
        <input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Buscar…"
          className="flex-1 bg-transparent text-xs outline-none"
          autoFocus
        />
      </div>

      <div className="space-y-1.5 max-h-64 overflow-y-auto">
        {isLoading ? (
          <div className="text-center text-secondary text-xs py-6">Carregando…</div>
        ) : items.length === 0 ? (
          <div className="text-center text-secondary text-xs py-6 space-y-2">
            <div>Sem templates.</div>
            <button
              onClick={onManage}
              className="text-accent-amethyst font-bold hover:underline"
            >
              Criar agora
            </button>
          </div>
        ) : (
          items.map((q: QuickReply) => (
            <button
              key={q.id}
              onClick={() => renderMut.mutate(q.id)}
              className="w-full text-left px-3 py-2 bg-bg-primary border border-border hover:border-accent-amethyst/30 rounded-xl transition-all"
            >
              <div className="flex items-center justify-between mb-0.5">
                <div className="font-black text-xs">{q.title}</div>
                <div className="flex items-center gap-1">
                  {q.category && (
                    <span className="text-[9px] uppercase tracking-widest text-secondary">{q.category}</span>
                  )}
                  {q.shortcut_number && (
                    <span className="text-[10px] font-mono bg-bg-surface border border-border px-1.5 rounded">
                      {q.shortcut_number}
                    </span>
                  )}
                </div>
              </div>
              <div className="text-[11px] text-secondary line-clamp-2 leading-relaxed">
                {q.body}
              </div>
            </button>
          ))
        )}
      </div>
    </div>
  );
}
