import { useState, useRef } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  Library, Mic, Upload, Trash2, Play, Pause, Tag,
  Plus, X, Search, Heart, Shield, Coins, Sparkles, Briefcase, Home, Activity,
  AlertCircle, Edit3, Save,
} from 'lucide-react';
import { audioLibraryApi, type AudioLibraryItem } from '../api/audioLibrary';
import { handleApiError } from '../lib/handleApiError';
import { toast } from '../lib/toast';

const CATEGORY_META: Record<string, { label: string; Icon: typeof Heart; color: string }> = {
  saudacao: { label: 'Saudação', Icon: Sparkles, color: 'text-amber-300' },
  protecao: { label: 'Proteção', Icon: Shield, color: 'text-blue-300' },
  prosperidade: { label: 'Prosperidade', Icon: Coins, color: 'text-emerald-300' },
  amor: { label: 'Amor', Icon: Heart, color: 'text-rose-300' },
  fechamento: { label: 'Fechamento', Icon: Activity, color: 'text-purple-300' },
  carreira: { label: 'Carreira', Icon: Briefcase, color: 'text-indigo-300' },
  familia: { label: 'Família', Icon: Home, color: 'text-amber-200' },
  saude: { label: 'Saúde', Icon: Activity, color: 'text-emerald-300' },
  outro: { label: 'Outro', Icon: Tag, color: 'text-secondary' },
};

const CATEGORY_KEYS = Object.keys(CATEGORY_META);

export default function AudioLibrary() {
  const qc = useQueryClient();
  const [category, setCategory] = useState<string | null>(null);
  const [search, setSearch] = useState('');
  const [showUpload, setShowUpload] = useState(false);
  const [editing, setEditing] = useState<AudioLibraryItem | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ['audio-library', category, search],
    queryFn: () => audioLibraryApi.list({
      category: category || undefined,
      search: search || undefined,
    }),
  });

  const { data: categoriesData } = useQuery({
    queryKey: ['audio-library-categories'],
    queryFn: audioLibraryApi.categories,
  });

  const deleteMut = useMutation({
    mutationFn: (id: number) => audioLibraryApi.remove(id),
    onSuccess: () => {
      toast.success('Áudio removido');
      qc.invalidateQueries({ queryKey: ['audio-library'] });
    },
    onError: handleApiError('Erro ao remover'),
  });

  const items = data?.items ?? [];
  const cats = categoriesData?.categories ?? [];

  return (
    <div className="p-10 max-w-6xl mx-auto space-y-8">
      <header className="flex items-start justify-between flex-wrap gap-4">
        <div>
          <div className="flex items-center gap-3 mb-2">
            <div className="w-10 h-10 rounded-2xl bg-accent-amethyst/10 flex items-center justify-center">
              <Library className="w-5 h-5 text-accent-amethyst" />
            </div>
            <h1 className="text-3xl font-black tracking-tight">Biblioteca de Áudios</h1>
          </div>
          <p className="text-secondary text-sm font-medium">
            Pré-grave áudios de "saudação manhã", "oração de proteção", "fechamento de venda"
            — reuse em conversas e fluxos.
          </p>
        </div>
        <button
          onClick={() => setShowUpload(true)}
          className="px-5 py-3 bg-accent-amethyst hover:bg-accent-amethyst/90 text-white rounded-2xl font-black uppercase tracking-widest text-xs flex items-center gap-2"
        >
          <Plus className="w-4 h-4" />
          Novo áudio
        </button>
      </header>

      {/* Filters */}
      <section className="bg-bg-surface border border-border rounded-3xl p-5 space-y-3">
        <div className="flex items-center gap-2 bg-bg-primary border border-border rounded-xl px-3 py-2 max-w-md">
          <Search className="w-3.5 h-3.5 text-secondary" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Buscar por título…"
            className="flex-1 bg-transparent text-sm outline-none"
          />
        </div>

        <div className="flex flex-wrap gap-2">
          <button
            onClick={() => setCategory(null)}
            className={`px-3 py-1.5 rounded-lg text-[11px] font-bold transition-all ${
              !category
                ? 'bg-accent-amethyst text-white'
                : 'bg-bg-primary text-secondary hover:text-primary'
            }`}
          >
            Todas
          </button>
          {CATEGORY_KEYS.map((c) => {
            const meta = CATEGORY_META[c];
            const Icon = meta.Icon;
            const cnt = cats.find((x) => x.category === c)?.count;
            return (
              <button
                key={c}
                onClick={() => setCategory(c === category ? null : c)}
                className={`px-3 py-1.5 rounded-lg text-[11px] font-bold transition-all flex items-center gap-1.5 ${
                  category === c
                    ? 'bg-accent-amethyst text-white'
                    : 'bg-bg-primary text-secondary hover:text-primary'
                }`}
              >
                <Icon className="w-3 h-3" />
                {meta.label}
                {cnt ? <span className="opacity-60">({cnt})</span> : null}
              </button>
            );
          })}
        </div>
      </section>

      {/* Grid */}
      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3 animate-pulse">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="h-48 bg-bg-surface rounded-2xl" />
          ))}
        </div>
      ) : items.length === 0 ? (
        <EmptyState onUpload={() => setShowUpload(true)} />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {items.map((item) => (
            <AudioCard
              key={item.id}
              item={item}
              onEdit={() => setEditing(item)}
              onDelete={() => {
                if (confirm(`Remover "${item.title}"?`)) deleteMut.mutate(item.id);
              }}
            />
          ))}
        </div>
      )}

      {showUpload && (
        <UploadModal
          onClose={() => setShowUpload(false)}
          onUploaded={() => {
            setShowUpload(false);
            qc.invalidateQueries({ queryKey: ['audio-library'] });
            qc.invalidateQueries({ queryKey: ['audio-library-categories'] });
          }}
        />
      )}

      {editing && (
        <EditModal
          item={editing}
          onClose={() => setEditing(null)}
          onSaved={() => {
            setEditing(null);
            qc.invalidateQueries({ queryKey: ['audio-library'] });
          }}
        />
      )}
    </div>
  );
}

function EmptyState({ onUpload }: { onUpload: () => void }) {
  return (
    <div className="bg-bg-surface border border-dashed border-border rounded-3xl p-12 text-center">
      <Library className="w-12 h-12 mx-auto text-accent-amethyst/40 mb-4" />
      <h3 className="font-black text-lg mb-2">Sua biblioteca está vazia</h3>
      <p className="text-secondary text-sm mb-4 max-w-md mx-auto">
        Suba ou grave áudios pré-prontos pra reusar em qualquer conversa.
        Ex.: "Saudação manhã", "Oração de proteção", "Fechamento amoroso".
      </p>
      <button
        onClick={onUpload}
        className="px-6 py-3 bg-accent-amethyst hover:bg-accent-amethyst/90 text-white rounded-2xl text-xs font-black uppercase tracking-widest"
      >
        Subir primeiro áudio
      </button>
    </div>
  );
}

function AudioCard({
  item, onEdit, onDelete,
}: {
  item: AudioLibraryItem;
  onEdit: () => void;
  onDelete: () => void;
}) {
  const meta = CATEGORY_META[item.category || 'outro'] || CATEGORY_META.outro;
  const Icon = meta.Icon;
  const audioRef = useRef<HTMLAudioElement>(null);
  const [playing, setPlaying] = useState(false);

  return (
    <div className="bg-bg-surface border border-border rounded-2xl p-4 space-y-3">
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-2 min-w-0">
          <Icon className={`w-4 h-4 flex-shrink-0 ${meta.color}`} />
          <h3 className="font-black text-sm truncate">{item.title}</h3>
        </div>
        <span className="text-[9px] uppercase tracking-widest text-secondary font-black flex-shrink-0">
          {meta.label}
        </span>
      </div>

      {item.tags.length > 0 && (
        <div className="flex flex-wrap gap-1">
          {item.tags.slice(0, 5).map((t) => (
            <span key={t} className="text-[9px] bg-bg-primary border border-border px-1.5 py-0.5 rounded font-bold text-secondary">
              #{t}
            </span>
          ))}
        </div>
      )}

      <audio
        ref={audioRef}
        src={item.audio_url}
        onPlay={() => setPlaying(true)}
        onPause={() => setPlaying(false)}
        onEnded={() => setPlaying(false)}
        className="hidden"
      />

      <div className="flex items-center justify-between text-[10px] text-secondary">
        <span>{item.usage_count} uso{item.usage_count !== 1 ? 's' : ''}</span>
        {item.duration_s && <span>{Math.round(item.duration_s)}s</span>}
      </div>

      <div className="flex gap-2">
        <button
          onClick={() => {
            if (audioRef.current) {
              if (playing) audioRef.current.pause();
              else audioRef.current.play();
            }
          }}
          className="flex-1 px-3 py-2 bg-accent-amethyst hover:bg-accent-amethyst/90 text-white rounded-xl text-xs font-bold flex items-center justify-center gap-1.5"
        >
          {playing ? <Pause className="w-3.5 h-3.5" /> : <Play className="w-3.5 h-3.5" />}
          {playing ? 'Pausar' : 'Tocar'}
        </button>
        <button
          onClick={onEdit}
          className="px-3 py-2 bg-bg-primary border border-border hover:border-accent-amethyst/30 rounded-xl text-xs"
          title="Editar"
        >
          <Edit3 className="w-3.5 h-3.5" />
        </button>
        <button
          onClick={onDelete}
          className="px-3 py-2 bg-bg-primary border border-border hover:border-rose-500/30 rounded-xl text-xs hover:text-rose-400"
          title="Remover"
        >
          <Trash2 className="w-3.5 h-3.5" />
        </button>
      </div>
    </div>
  );
}

function UploadModal({
  onClose, onUploaded,
}: {
  onClose: () => void;
  onUploaded: () => void;
}) {
  const [title, setTitle] = useState('');
  const [category, setCategory] = useState('outro');
  const [tags, setTags] = useState('');
  const [audioBlob, setAudioBlob] = useState<Blob | null>(null);
  const [audioPreviewUrl, setAudioPreviewUrl] = useState<string | null>(null);
  const [recording, setRecording] = useState(false);
  const [recordedSec, setRecordedSec] = useState(0);
  const mediaRecRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const intervalRef = useRef<number | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const uploadMut = useMutation({
    mutationFn: async () => {
      if (!audioBlob) throw new Error('Sem áudio');
      const fd = new FormData();
      const ext = audioBlob.type.includes('webm') ? 'webm'
        : audioBlob.type.includes('ogg') ? 'ogg'
        : audioBlob.type.includes('mp4') ? 'm4a'
        : 'mp3';
      fd.append('audio', audioBlob, `library.${ext}`);
      fd.append('title', title.trim());
      fd.append('category', category);
      fd.append('tags', tags);
      return audioLibraryApi.upload(fd);
    },
    onSuccess: () => {
      toast.success('Áudio adicionado à biblioteca');
      onUploaded();
    },
    onError: (e: unknown) => {
      const body = (e as { body?: { error?: string; message?: string } }).body;
      toast.error(body?.message || body?.error || 'Erro no upload');
    },
  });

  const handleFile = (file: File) => {
    setAudioBlob(file);
    const url = URL.createObjectURL(file);
    setAudioPreviewUrl(url);
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
        setAudioPreviewUrl(url);
        stream.getTracks().forEach((t) => t.stop());
      };
      mediaRecRef.current = mr;
      mr.start();
      setRecording(true);
      setRecordedSec(0);
      intervalRef.current = window.setInterval(() => {
        setRecordedSec((s) => s + 1);
      }, 1000);
    } catch (e) {
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

  const valid = title.trim().length >= 3 && audioBlob !== null;

  return (
    <div className="fixed inset-0 z-50 bg-black/70 flex items-center justify-center p-6">
      <div className="bg-bg-surface border border-border rounded-3xl max-w-lg w-full overflow-hidden flex flex-col max-h-[85vh]">
        <div className="p-5 border-b border-border flex items-start justify-between">
          <h2 className="text-xl font-black tracking-tight">Adicionar áudio</h2>
          <button onClick={onClose} className="text-secondary hover:text-primary">
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="p-5 overflow-y-auto space-y-4">
          <div>
            <label className="text-[10px] font-black uppercase tracking-widest text-secondary block mb-1.5">
              Título
            </label>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder='Ex.: "Oração de proteção"'
              maxLength={200}
              className="w-full bg-bg-primary border border-border rounded-xl px-4 py-2.5 text-sm"
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-[10px] font-black uppercase tracking-widest text-secondary block mb-1.5">
                Categoria
              </label>
              <select
                value={category}
                onChange={(e) => setCategory(e.target.value)}
                className="w-full bg-bg-primary border border-border rounded-xl px-4 py-2.5 text-sm"
              >
                {CATEGORY_KEYS.map((k) => (
                  <option key={k} value={k}>{CATEGORY_META[k].label}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="text-[10px] font-black uppercase tracking-widest text-secondary block mb-1.5">
                Tags (vírgula)
              </label>
              <input
                type="text"
                value={tags}
                onChange={(e) => setTags(e.target.value)}
                placeholder="manha, vela branca"
                className="w-full bg-bg-primary border border-border rounded-xl px-4 py-2.5 text-sm"
              />
            </div>
          </div>

          <div className="border-t border-border pt-4 space-y-3">
            <div className="text-[10px] font-black uppercase tracking-widest text-secondary">
              Áudio
            </div>

            <div className="flex gap-2">
              <button
                onClick={() => fileInputRef.current?.click()}
                className="flex-1 px-4 py-2.5 bg-bg-primary border border-border hover:border-accent-amethyst/30 rounded-xl text-xs font-bold flex items-center justify-center gap-2"
              >
                <Upload className="w-3.5 h-3.5" />
                Subir arquivo
              </button>
              {!recording ? (
                <button
                  onClick={startRecording}
                  className="flex-1 px-4 py-2.5 bg-bg-primary border border-border hover:border-rose-500/30 rounded-xl text-xs font-bold flex items-center justify-center gap-2"
                >
                  <Mic className="w-3.5 h-3.5" />
                  Gravar
                </button>
              ) : (
                <button
                  onClick={stopRecording}
                  className="flex-1 px-4 py-2.5 bg-rose-500 text-white rounded-xl text-xs font-black animate-pulse flex items-center justify-center gap-2"
                >
                  ● Parar ({recordedSec}s)
                </button>
              )}
            </div>

            <input
              ref={fileInputRef}
              type="file"
              accept="audio/*"
              hidden
              onChange={(e) => {
                const f = e.target.files?.[0];
                if (f) handleFile(f);
              }}
            />

            {audioPreviewUrl && (
              <audio src={audioPreviewUrl} controls className="w-full h-10" />
            )}
            {audioBlob && (
              <div className="text-[10px] text-secondary">
                {(audioBlob.size / 1024).toFixed(1)} KB
              </div>
            )}
            {!audioBlob && (
              <div className="text-[11px] text-secondary flex items-start gap-1">
                <AlertCircle className="w-3 h-3 mt-0.5 flex-shrink-0" />
                Suba um arquivo ou grave inline. Formatos aceitos: mp3, ogg, m4a, webm, wav (até 25MB).
              </div>
            )}
          </div>
        </div>

        <div className="p-4 border-t border-border flex gap-2">
          <button
            onClick={onClose}
            className="flex-1 px-3 py-2.5 bg-bg-primary border border-border rounded-xl text-xs font-bold"
          >
            Cancelar
          </button>
          <button
            onClick={() => uploadMut.mutate()}
            disabled={!valid || uploadMut.isPending}
            className="flex-1 px-3 py-2.5 bg-accent-amethyst hover:bg-accent-amethyst/90 disabled:opacity-30 text-white rounded-xl text-xs font-black uppercase tracking-widest flex items-center justify-center gap-2"
          >
            <Upload className="w-3.5 h-3.5" />
            {uploadMut.isPending ? 'Enviando…' : 'Salvar'}
          </button>
        </div>
      </div>
    </div>
  );
}

function EditModal({
  item, onClose, onSaved,
}: {
  item: AudioLibraryItem;
  onClose: () => void;
  onSaved: () => void;
}) {
  const [title, setTitle] = useState(item.title);
  const [category, setCategory] = useState(item.category || 'outro');
  const [tags, setTags] = useState((item.tags || []).join(', '));

  const updateMut = useMutation({
    mutationFn: () => audioLibraryApi.update(item.id, {
      title: title.trim(),
      category,
      tags: tags.split(',').map((t) => t.trim()).filter(Boolean),
    }),
    onSuccess: () => {
      toast.success('Áudio atualizado');
      onSaved();
    },
    onError: handleApiError('Erro ao atualizar'),
  });

  return (
    <div className="fixed inset-0 z-50 bg-black/70 flex items-center justify-center p-6">
      <div className="bg-bg-surface border border-border rounded-3xl max-w-md w-full overflow-hidden">
        <div className="p-5 border-b border-border flex items-start justify-between">
          <h2 className="text-xl font-black tracking-tight">Editar áudio</h2>
          <button onClick={onClose} className="text-secondary hover:text-primary">
            <X className="w-5 h-5" />
          </button>
        </div>
        <div className="p-5 space-y-3">
          <div>
            <label className="text-[10px] font-black uppercase tracking-widest text-secondary block mb-1">Título</label>
            <input
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              maxLength={200}
              className="w-full bg-bg-primary border border-border rounded-xl px-3 py-2 text-sm"
            />
          </div>
          <div>
            <label className="text-[10px] font-black uppercase tracking-widest text-secondary block mb-1">Categoria</label>
            <select
              value={category}
              onChange={(e) => setCategory(e.target.value)}
              className="w-full bg-bg-primary border border-border rounded-xl px-3 py-2 text-sm"
            >
              {CATEGORY_KEYS.map((k) => (
                <option key={k} value={k}>{CATEGORY_META[k].label}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="text-[10px] font-black uppercase tracking-widest text-secondary block mb-1">Tags (vírgula)</label>
            <input
              value={tags}
              onChange={(e) => setTags(e.target.value)}
              className="w-full bg-bg-primary border border-border rounded-xl px-3 py-2 text-sm"
            />
          </div>
        </div>
        <div className="p-4 border-t border-border flex gap-2">
          <button
            onClick={onClose}
            className="flex-1 px-3 py-2 bg-bg-primary border border-border rounded-xl text-xs font-bold"
          >
            Cancelar
          </button>
          <button
            onClick={() => updateMut.mutate()}
            disabled={updateMut.isPending}
            className="flex-1 px-3 py-2 bg-accent-amethyst hover:bg-accent-amethyst/90 disabled:opacity-30 text-white rounded-xl text-xs font-black uppercase tracking-widest flex items-center justify-center gap-1.5"
          >
            <Save className="w-3 h-3" />
            {updateMut.isPending ? 'Salvando…' : 'Salvar'}
          </button>
        </div>
      </div>
    </div>
  );
}
