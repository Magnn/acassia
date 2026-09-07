import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Users, Plus, MessageCircle, Heart, Flame, Sparkles, Send, ArrowLeft, Bot, Trash2 } from 'lucide-react';
import { api } from '../api/client';
import { handleApiError } from '../lib/handleApiError';
import { toast } from '../lib/toast';

interface Group { id: number; name: string; slug: string; description: string | null; category: string; icon: string; is_public: boolean; oracle_enabled: boolean; member_count: number; post_count: number; is_member: boolean; created_at: string }
interface Post { id: number; group_id: number; content: string; post_type: string; media_url: string | null; reply_to_id: number | null; reply_count: number; is_oracle_response: boolean; reaction_count: number; is_pinned: boolean; author_user_id: number | null; created_at: string; replies?: Post[] }

const communityApi = {
  groups: () => api.get<{ groups: Group[] }>('/saas/community/groups'),
  createGroup: (b: { name: string; description?: string; category: string; icon: string; oracle_enabled: boolean }) =>
    api.post<{ ok: boolean; id: number }>('/saas/community/groups', b),
  join: (id: number) => api.post<{ ok: boolean }>(`/saas/community/groups/${id}/join`, {}),
  leave: (id: number) => api.post<{ ok: boolean }>(`/saas/community/groups/${id}/leave`, {}),
  posts: (gid: number, page?: number) => api.get<{ posts: Post[]; total: number }>(`/saas/community/groups/${gid}/posts?page=${page || 1}`),
  createPost: (gid: number, b: { content: string; post_type?: string }) => api.post<{ ok: boolean; id: number; post: Post }>(`/saas/community/groups/${gid}/posts`, b),
  reply: (pid: number, b: { content: string }) => api.post<{ ok: boolean; reply: Post }>(`/saas/community/posts/${pid}/reply`, b),
  react: (pid: number, type: string) => api.post<{ ok: boolean; action: string }>(`/saas/community/posts/${pid}/react`, { reaction_type: type }),
  oracle: (pid: number) => api.post<{ ok: boolean; oracle_post: Post }>(`/saas/community/posts/${pid}/oracle`, {}),
  del: (pid: number) => api.del<{ ok: boolean }>(`/saas/community/posts/${pid}`),
  stats: () => api.get<{ total_groups: number; total_posts: number; total_members: number; my_groups: number }>('/saas/community/stats'),
};

const REACTIONS = [
  { type: 'like', emoji: '❤️' }, { type: 'fire', emoji: '🔥' },
  { type: 'pray', emoji: '🙏' }, { type: 'insight', emoji: '💡' },
];

const CATEGORIES = [
  { id: 'signo', emoji: '♈', label: 'Signo' },
  { id: 'pratica', emoji: '🧘', label: 'Prática' },
  { id: 'tema', emoji: '📖', label: 'Tema' },
  { id: 'livre', emoji: '💬', label: 'Livre' },
];

export default function Community() {
  const qc = useQueryClient();
  const [activeGroup, setActiveGroup] = useState<Group | null>(null);
  const [showCreate, setShowCreate] = useState(false);

  const { data, isLoading } = useQuery({ queryKey: ['community-groups'], queryFn: communityApi.groups });
  const { data: statsData } = useQuery({ queryKey: ['community-stats'], queryFn: communityApi.stats });
  const groups = data?.groups ?? [];

  const joinMut = useMutation({
    mutationFn: (id: number) => communityApi.join(id),
    onSuccess: () => { toast.success('Entrou no grupo!'); qc.invalidateQueries({ queryKey: ['community-groups'] }); },
    onError: handleApiError('Erro'),
  });

  const leaveMut = useMutation({
    mutationFn: (id: number) => communityApi.leave(id),
    onSuccess: () => { toast.success('Saiu do grupo'); qc.invalidateQueries({ queryKey: ['community-groups'] }); },
    onError: handleApiError('Erro'),
  });

  if (activeGroup) {
    return <GroupFeed group={activeGroup} onBack={() => { setActiveGroup(null); qc.invalidateQueries({ queryKey: ['community-groups'] }); }} />;
  }

  return (
    <div className="p-10 max-w-5xl mx-auto space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-3 mb-2">
            <div className="w-10 h-10 rounded-2xl bg-accent-amethyst/10 flex items-center justify-center">
              <Users className="w-5 h-5 text-accent-amethyst" />
            </div>
            <h1 className="text-3xl font-black tracking-tight">Comunidade</h1>
          </div>
          <p className="text-secondary text-sm font-medium">Grupos temáticos e canais de engajamento com suporte de Assistente IA.</p>
        </div>
        <button onClick={() => setShowCreate(true)} className="flex items-center gap-2 px-5 py-3 bg-accent-amethyst hover:bg-accent-amethyst/90 text-white rounded-2xl font-black uppercase tracking-widest text-xs transition-all">
          <Plus className="w-4 h-4" /> Criar Grupo
        </button>
      </div>

      {/* Stats */}
      {statsData && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[
            { label: 'Grupos', value: statsData.total_groups, icon: Users, color: 'text-accent-amethyst' },
            { label: 'Posts', value: statsData.total_posts, icon: MessageCircle, color: 'text-blue-400' },
            { label: 'Membros', value: statsData.total_members, icon: Heart, color: 'text-pink-400' },
            { label: 'Meus Grupos', value: statsData.my_groups, icon: Sparkles, color: 'text-amber-400' },
          ].map(s => (
            <div key={s.label} className="bg-bg-surface border border-border rounded-2xl p-5">
              <div className="flex items-center gap-2 mb-2">
                <s.icon className={`w-4 h-4 ${s.color}`} />
                <span className="text-[10px] font-black uppercase tracking-widest text-secondary">{s.label}</span>
              </div>
              <div className="text-2xl font-black tracking-tight">{s.value}</div>
            </div>
          ))}
        </div>
      )}

      {/* Groups */}
      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 animate-pulse">{[1,2,3,4].map(i => <div key={i} className="h-32 bg-bg-surface rounded-2xl" />)}</div>
      ) : groups.length === 0 ? (
        <div className="bg-bg-surface border border-dashed border-border rounded-3xl p-12 text-center">
          <Users className="w-12 h-12 mx-auto text-secondary/40 mb-4" />
          <h3 className="font-black text-lg mb-2">Nenhum grupo ainda</h3>
          <p className="text-secondary text-sm mb-4">Crie o primeiro grupo da comunidade — por signo, prática ou tema.</p>
          <button onClick={() => setShowCreate(true)} className="px-5 py-3 bg-accent-amethyst text-white rounded-2xl text-xs font-black uppercase tracking-widest">Criar Grupo</button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {groups.map(g => (
            <div key={g.id} className="bg-bg-surface border border-border hover:border-accent-amethyst/30 rounded-2xl p-6 transition-all cursor-pointer" onClick={() => setActiveGroup(g)}>
              <div className="flex items-start justify-between mb-3">
                <div className="flex items-center gap-3">
                  <span className="text-3xl">{g.icon || '🔮'}</span>
                  <div>
                    <h3 className="font-black text-sm">{g.name}</h3>
                    <span className="text-[10px] text-secondary">{CATEGORIES.find(c => c.id === g.category)?.label || g.category}</span>
                  </div>
                </div>
                {g.oracle_enabled && <span className="text-[9px] bg-accent-amethyst/10 text-accent-amethyst px-2 py-0.5 rounded-md font-bold">🔮 Oracle</span>}
              </div>
              {g.description && <p className="text-[11px] text-secondary mb-3 line-clamp-2">{g.description}</p>}
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3 text-[11px] text-secondary">
                  <span className="flex items-center gap-1"><Users className="w-3 h-3" />{g.member_count}</span>
                  <span className="flex items-center gap-1"><MessageCircle className="w-3 h-3" />{g.post_count}</span>
                </div>
                {g.is_member ? (
                  <button onClick={(e) => { e.stopPropagation(); leaveMut.mutate(g.id); }}
                    className="text-[9px] text-secondary font-bold hover:text-red-400">Sair</button>
                ) : (
                  <button onClick={(e) => { e.stopPropagation(); joinMut.mutate(g.id); }}
                    className="text-[9px] bg-accent-amethyst/10 text-accent-amethyst px-3 py-1 rounded-lg font-black uppercase tracking-widest hover:bg-accent-amethyst/20">Entrar</button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {showCreate && <CreateGroupModal onClose={() => setShowCreate(false)} onCreated={() => { setShowCreate(false); qc.invalidateQueries({ queryKey: ['community-groups'] }); }} />}
    </div>
  );
}

function GroupFeed({ group, onBack }: { group: Group; onBack: () => void }) {
  const qc = useQueryClient();
  const [newPost, setNewPost] = useState('');
  const [replyTo, setReplyTo] = useState<number | null>(null);
  const [replyText, setReplyText] = useState('');

  const { data, isLoading } = useQuery({ queryKey: ['community-posts', group.id], queryFn: () => communityApi.posts(group.id) });
  const posts = data?.posts ?? [];

  const postMut = useMutation({
    mutationFn: () => communityApi.createPost(group.id, { content: newPost }),
    onSuccess: () => { setNewPost(''); toast.success('Publicado!'); qc.invalidateQueries({ queryKey: ['community-posts', group.id] }); },
    onError: handleApiError('Erro'),
  });

  const replyMut = useMutation({
    mutationFn: () => communityApi.reply(replyTo!, { content: replyText }),
    onSuccess: () => { setReplyTo(null); setReplyText(''); toast.success('Respondido!'); qc.invalidateQueries({ queryKey: ['community-posts', group.id] }); },
    onError: handleApiError('Erro'),
  });

  const oracleMut = useMutation({
    mutationFn: (pid: number) => communityApi.oracle(pid),
    onSuccess: () => { toast.success('🔮 Oráculo respondeu!'); qc.invalidateQueries({ queryKey: ['community-posts', group.id] }); },
    onError: handleApiError('Erro ao consultar oráculo'),
  });

  const reactMut = useMutation({
    mutationFn: ({ pid, type }: { pid: number; type: string }) => communityApi.react(pid, type),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['community-posts', group.id] }),
  });

  const delMut = useMutation({
    mutationFn: (pid: number) => communityApi.del(pid),
    onSuccess: () => { toast.success('Removido'); qc.invalidateQueries({ queryKey: ['community-posts', group.id] }); },
  });

  return (
    <div className="p-10 max-w-3xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <button onClick={onBack} className="w-10 h-10 rounded-2xl bg-bg-surface border border-border flex items-center justify-center hover:border-accent-amethyst/30 transition-all">
          <ArrowLeft className="w-5 h-5" />
        </button>
        <div className="flex items-center gap-3">
          <span className="text-3xl">{group.icon || '🔮'}</span>
          <div>
            <h1 className="text-2xl font-black tracking-tight">{group.name}</h1>
            <span className="text-[11px] text-secondary">{group.member_count} membros • {group.post_count} posts</span>
          </div>
        </div>
      </div>

      {/* New Post */}
      <div className="bg-bg-surface border border-border rounded-2xl p-5">
        <textarea value={newPost} onChange={e => setNewPost(e.target.value)} rows={3}
          placeholder="Compartilhe um pensamento, faça uma pergunta..."
          className="inp resize-none mb-3" />
        <div className="flex justify-between items-center">
          {group.oracle_enabled && (
            <span className="text-[10px] text-accent-amethyst font-bold">🔮 Use "?" para perguntar ao Oráculo IA</span>
          )}
          <button onClick={() => postMut.mutate()} disabled={!newPost.trim() || postMut.isPending}
            className="flex items-center gap-2 px-5 py-2.5 bg-accent-amethyst hover:bg-accent-amethyst/90 disabled:opacity-30 text-white rounded-xl text-xs font-black uppercase tracking-widest transition-all">
            <Send className="w-3.5 h-3.5" /> {postMut.isPending ? 'Enviando...' : 'Publicar'}
          </button>
        </div>
      </div>

      {/* Posts */}
      {isLoading ? (
        <div className="space-y-3 animate-pulse">{[1,2,3].map(i => <div key={i} className="h-24 bg-bg-surface rounded-2xl" />)}</div>
      ) : posts.length === 0 ? (
        <div className="bg-bg-surface border border-dashed border-border rounded-3xl p-12 text-center">
          <MessageCircle className="w-12 h-12 mx-auto text-secondary/40 mb-4" />
          <h3 className="font-black text-lg mb-2">Nenhum post</h3>
          <p className="text-secondary text-sm">Seja o primeiro a compartilhar!</p>
        </div>
      ) : (
        <div className="space-y-4">
          {posts.map(p => (
            <div key={p.id} className={`bg-bg-surface border rounded-2xl p-5 transition-all ${p.is_pinned ? 'border-amber-500/30' : p.is_oracle_response ? 'border-accent-amethyst/30 bg-accent-amethyst/5' : 'border-border'}`}>
              {p.is_pinned && <span className="text-[9px] font-black uppercase tracking-widest text-amber-400 mb-2 block">📌 Fixado</span>}
              {p.is_oracle_response && (
                <div className="flex items-center gap-1.5 text-[10px] text-accent-amethyst font-black uppercase tracking-widest mb-2">
                  <Bot className="w-3.5 h-3.5" /> Oráculo IA
                </div>
              )}
              <p className="text-sm whitespace-pre-wrap">{p.content}</p>
              <div className="flex items-center justify-between mt-3">
                <div className="flex items-center gap-1">
                  {REACTIONS.map(r => (
                    <button key={r.type} onClick={() => reactMut.mutate({ pid: p.id, type: r.type })}
                      className="px-2 py-1 rounded-lg hover:bg-bg-primary text-xs transition-all">
                      {r.emoji}
                    </button>
                  ))}
                  {p.reaction_count > 0 && <span className="text-[10px] text-secondary ml-1">{p.reaction_count}</span>}
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-[10px] text-secondary">{new Date(p.created_at).toLocaleDateString('pt-BR')}</span>
                  <button onClick={() => { setReplyTo(p.id); setReplyText(''); }}
                    className="text-[10px] text-accent-amethyst font-bold hover:underline flex items-center gap-1">
                    <MessageCircle className="w-3 h-3" /> {p.reply_count || ''}
                  </button>
                  {group.oracle_enabled && !p.is_oracle_response && (
                    <button onClick={() => oracleMut.mutate(p.id)} disabled={oracleMut.isPending}
                      className="text-[10px] text-accent-amethyst font-bold hover:underline">
                      🔮 Oráculo
                    </button>
                  )}
                  <button onClick={() => delMut.mutate(p.id)} className="text-secondary hover:text-red-400"><Trash2 className="w-3 h-3" /></button>
                </div>
              </div>

              {/* Replies */}
              {p.replies && p.replies.length > 0 && (
                <div className="mt-3 ml-4 border-l-2 border-border pl-4 space-y-3">
                  {p.replies.map(r => (
                    <div key={r.id} className={`text-[12px] ${r.is_oracle_response ? 'text-accent-amethyst' : 'text-secondary'}`}>
                      {r.is_oracle_response && <span className="text-[9px] font-bold">🔮 Oráculo</span>}
                      <p className="whitespace-pre-wrap">{r.content}</p>
                      <span className="text-[9px] text-secondary">{new Date(r.created_at).toLocaleDateString('pt-BR')}</span>
                    </div>
                  ))}
                </div>
              )}

              {/* Reply input */}
              {replyTo === p.id && (
                <div className="mt-3 ml-4 border-l-2 border-accent-amethyst/30 pl-4 flex gap-2">
                  <input value={replyText} onChange={e => setReplyText(e.target.value)} placeholder="Responder..."
                    className="inp flex-1 text-sm" onKeyDown={e => e.key === 'Enter' && replyText && replyMut.mutate()} />
                  <button onClick={() => replyMut.mutate()} disabled={!replyText || replyMut.isPending}
                    className="px-3 py-2 bg-accent-amethyst disabled:opacity-30 text-white rounded-xl text-xs font-bold">
                    <Send className="w-3.5 h-3.5" />
                  </button>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function CreateGroupModal({ onClose, onCreated }: { onClose: () => void; onCreated: () => void }) {
  const [form, setForm] = useState({ name: '', description: '', category: 'livre', icon: '🔮', oracle_enabled: true });
  const set = (k: string, v: unknown) => setForm(f => ({ ...f, [k]: v }));
  const ICONS = ['🔮', '♈', '♉', '♊', '♋', '♌', '♍', '♎', '♏', '♐', '♑', '♒', '♓', '🧘', '🌙', '⭐', '🌿', '🔥', '💎', '🦋'];

  const createMut = useMutation({
    mutationFn: () => communityApi.createGroup(form),
    onSuccess: () => { toast.success('Grupo criado!'); onCreated(); },
    onError: handleApiError('Erro'),
  });

  return (
    <div className="fixed inset-0 z-50 bg-black/70 flex items-center justify-center p-6">
      <div className="bg-bg-surface border border-border rounded-3xl p-8 max-w-md w-full space-y-5">
        <h2 className="text-xl font-black tracking-tight">Criar Grupo</h2>
        <F label="Ícone">
          <div className="flex flex-wrap gap-1.5">{ICONS.map(i => (
            <button key={i} onClick={() => set('icon', i)} className={`w-9 h-9 rounded-lg text-lg flex items-center justify-center transition-all ${form.icon === i ? 'bg-accent-amethyst text-white ring-2 ring-accent-amethyst/50' : 'bg-bg-primary hover:bg-bg-primary/80'}`}>{i}</button>
          ))}</div>
        </F>
        <F label="Nome"><input value={form.name} onChange={e => set('name', e.target.value)} placeholder="Círculo de Áries" className="inp" /></F>
        <F label="Descrição"><textarea value={form.description} onChange={e => set('description', e.target.value)} rows={2} className="inp resize-none" /></F>
        <F label="Categoria">
          <div className="flex gap-2">{CATEGORIES.map(c => (
            <button key={c.id} onClick={() => set('category', c.id)} className={`flex-1 px-3 py-2 rounded-xl text-xs font-bold ${form.category === c.id ? 'bg-accent-amethyst text-white' : 'bg-bg-primary text-secondary'}`}>
              {c.emoji} {c.label}
            </button>
          ))}</div>
        </F>
        <label className="flex items-center gap-3 cursor-pointer">
          <input type="checkbox" checked={form.oracle_enabled} onChange={e => set('oracle_enabled', e.target.checked)} className="accent-accent-amethyst w-4 h-4" />
          <span className="text-sm font-bold">🔮 Ativar IA Oráculo neste grupo</span>
        </label>
        <div className="flex gap-3">
          <button onClick={onClose} className="flex-1 px-5 py-3 bg-bg-primary border border-border rounded-2xl text-sm font-bold">Cancelar</button>
          <button onClick={() => createMut.mutate()} disabled={!form.name || createMut.isPending}
            className="flex-1 px-5 py-3 bg-accent-amethyst hover:bg-accent-amethyst/90 disabled:opacity-30 text-white rounded-2xl text-sm font-black uppercase tracking-widest">
            {createMut.isPending ? 'Criando...' : 'Criar Grupo'}
          </button>
        </div>
      </div>
    </div>
  );
}

function F({ label, children }: { label: string; children: React.ReactNode }) {
  return <div><label className="text-[10px] uppercase font-black tracking-widest text-secondary mb-1.5 block">{label}</label>{children}</div>;
}
