import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { X, Plus, Trash2, Save } from 'lucide-react';
import { composeApi, type QuickReply } from '../api/compose';
import { handleApiError } from '../lib/handleApiError';
import { toast } from '../lib/toast';

const CATEGORIES = ['saudacao', 'oferta', 'fechamento', 'recuperacao', 'outro'] as const;

export default function QuickReplyManager({ onClose }: { onClose: () => void }) {
  const qc = useQueryClient();
  const [editing, setEditing] = useState<QuickReply | null>(null);
  const [draft, setDraft] = useState({
    title: '', body: '', category: 'outro' as string, shortcut_number: null as number | null,
  });

  const { data, isLoading } = useQuery({
    queryKey: ['quick-replies'],
    queryFn: composeApi.list,
  });

  const createMut = useMutation({
    mutationFn: () => composeApi.create({
      title: draft.title.trim(),
      body: draft.body.trim(),
      category: draft.category,
      shortcut_number: draft.shortcut_number,
    }),
    onSuccess: () => {
      toast.success('Template criado');
      setDraft({ title: '', body: '', category: 'outro', shortcut_number: null });
      qc.invalidateQueries({ queryKey: ['quick-replies'] });
    },
    onError: handleApiError('Erro ao criar'),
  });

  const updateMut = useMutation({
    mutationFn: () => {
      if (!editing) throw new Error('no_editing');
      return composeApi.update(editing.id, {
        title: draft.title.trim(),
        body: draft.body.trim(),
        category: draft.category,
        shortcut_number: draft.shortcut_number,
      });
    },
    onSuccess: () => {
      toast.success('Template salvo');
      setEditing(null);
      setDraft({ title: '', body: '', category: 'outro', shortcut_number: null });
      qc.invalidateQueries({ queryKey: ['quick-replies'] });
    },
    onError: handleApiError('Erro ao salvar'),
  });

  const deleteMut = useMutation({
    mutationFn: (id: number) => composeApi.remove(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['quick-replies'] });
    },
    onError: handleApiError('Erro ao remover'),
  });

  const startEdit = (q: QuickReply) => {
    setEditing(q);
    setDraft({
      title: q.title,
      body: q.body,
      category: q.category || 'outro',
      shortcut_number: q.shortcut_number,
    });
  };

  const cancelEdit = () => {
    setEditing(null);
    setDraft({ title: '', body: '', category: 'outro', shortcut_number: null });
  };

  const items = data?.quick_replies ?? [];

  return (
    <div className="fixed inset-0 z-50 bg-black/70 flex items-center justify-center p-6">
      <div className="bg-bg-surface border border-border rounded-3xl max-w-3xl w-full max-h-[85vh] overflow-hidden flex flex-col">
        <div className="p-5 border-b border-border flex items-start justify-between">
          <div>
            <h2 className="text-xl font-black tracking-tight">Templates rápidos</h2>
            <p className="text-xs text-secondary mt-1">
              Use <code className="bg-bg-primary px-1 rounded text-[10px]">{'{{nome}}'}</code>,{' '}
              <code className="bg-bg-primary px-1 rounded text-[10px]">{'{{primeiro_nome}}'}</code>,{' '}
              <code className="bg-bg-primary px-1 rounded text-[10px]">{'{{signo}}'}</code>{' '}
              para personalizar.
            </p>
          </div>
          <button onClick={onClose} className="text-secondary hover:text-primary">
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-0 flex-1 overflow-hidden">
          <div className="border-r border-border overflow-y-auto p-4 space-y-2">
            <h3 className="text-[10px] font-black uppercase tracking-widest text-secondary mb-2">
              Existentes ({items.length})
            </h3>
            {isLoading ? (
              <div className="text-center text-secondary text-xs py-6">Carregando…</div>
            ) : items.length === 0 ? (
              <div className="text-center text-secondary text-xs py-6">
                Nenhum template ainda. Crie o primeiro à direita.
              </div>
            ) : (
              items.map((q) => (
                <div
                  key={q.id}
                  className={`px-3 py-2 rounded-xl border cursor-pointer transition-all ${
                    editing?.id === q.id
                      ? 'bg-accent-amethyst/10 border-accent-amethyst'
                      : 'bg-bg-primary border-border hover:border-accent-amethyst/30'
                  }`}
                  onClick={() => startEdit(q)}
                >
                  <div className="flex items-center justify-between mb-1">
                    <div className="font-black text-xs">{q.title}</div>
                    <div className="flex items-center gap-1">
                      {q.shortcut_number && (
                        <span className="text-[10px] font-mono bg-bg-surface border border-border px-1 rounded">
                          {q.shortcut_number}
                        </span>
                      )}
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          if (confirm(`Remover "${q.title}"?`)) deleteMut.mutate(q.id);
                        }}
                        className="text-secondary hover:text-rose-400 p-0.5"
                      >
                        <Trash2 className="w-3 h-3" />
                      </button>
                    </div>
                  </div>
                  <div className="text-[11px] text-secondary line-clamp-2 leading-relaxed">
                    {q.body}
                  </div>
                </div>
              ))
            )}
          </div>

          <div className="p-5 overflow-y-auto space-y-3">
            <h3 className="text-[10px] font-black uppercase tracking-widest text-secondary mb-2">
              {editing ? 'Editar template' : 'Novo template'}
            </h3>

            <Field label="Título">
              <input
                type="text"
                value={draft.title}
                onChange={(e) => setDraft({ ...draft, title: e.target.value })}
                maxLength={120}
                className="w-full bg-bg-primary border border-border rounded-xl px-3 py-2 text-xs"
                placeholder="Ex.: Saudação inicial"
              />
            </Field>

            <Field label="Mensagem">
              <textarea
                value={draft.body}
                onChange={(e) => setDraft({ ...draft, body: e.target.value })}
                rows={6}
                className="w-full bg-bg-primary border border-border rounded-xl px-3 py-2 text-xs resize-none"
                placeholder="Olá, {{primeiro_nome}}! Tudo bem?"
              />
              <div className="text-[10px] text-secondary mt-1">{draft.body.length} caracteres</div>
            </Field>

            <div className="grid grid-cols-2 gap-3">
              <Field label="Categoria">
                <select
                  value={draft.category}
                  onChange={(e) => setDraft({ ...draft, category: e.target.value })}
                  className="w-full bg-bg-primary border border-border rounded-xl px-3 py-2 text-xs"
                >
                  {CATEGORIES.map((c) => (
                    <option key={c} value={c}>{c}</option>
                  ))}
                </select>
              </Field>
              <Field label="Atalho (1-9)">
                <select
                  value={draft.shortcut_number ?? ''}
                  onChange={(e) =>
                    setDraft({ ...draft, shortcut_number: e.target.value ? Number(e.target.value) : null })
                  }
                  className="w-full bg-bg-primary border border-border rounded-xl px-3 py-2 text-xs"
                >
                  <option value="">Sem atalho</option>
                  {[1,2,3,4,5,6,7,8,9].map((n) => <option key={n} value={n}>{n}</option>)}
                </select>
              </Field>
            </div>

            <div className="flex gap-2 pt-3">
              {editing && (
                <button
                  onClick={cancelEdit}
                  className="flex-1 px-3 py-2 bg-bg-primary border border-border rounded-xl text-[11px] font-bold"
                >
                  Cancelar
                </button>
              )}
              <button
                onClick={() => editing ? updateMut.mutate() : createMut.mutate()}
                disabled={
                  draft.title.trim().length < 3 ||
                  draft.body.trim().length < 1 ||
                  createMut.isPending || updateMut.isPending
                }
                className="flex-1 px-3 py-2 bg-accent-amethyst hover:bg-accent-amethyst/90 disabled:opacity-30 text-white rounded-xl text-[11px] font-black uppercase tracking-widest flex items-center justify-center gap-1.5"
              >
                {editing ? <Save className="w-3 h-3" /> : <Plus className="w-3 h-3" />}
                {editing ? (updateMut.isPending ? 'Salvando…' : 'Salvar') : (createMut.isPending ? 'Criando…' : 'Criar')}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <label className="text-[9px] font-black uppercase tracking-widest text-secondary block mb-1">
        {label}
      </label>
      {children}
    </div>
  );
}
