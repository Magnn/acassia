import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Users, MessageCircle, Send, ArrowLeft, Bot } from 'lucide-react';
import { api } from '../../api/client';
import { toast } from '../../lib/toast';

const REACTIONS = [{ type: 'like', emoji: '❤️' }, { type: 'fire', emoji: '🔥' }, { type: 'pray', emoji: '🙏' }, { type: 'insight', emoji: '💡' }];

export default function PortalCommunity() {
  const qc = useQueryClient();
  const [activeGroup, setActiveGroup] = useState<any>(null);

  const { data } = useQuery({ queryKey: ['community-groups'], queryFn: () => api.get<any>('/saas/community/groups') });
  const groups = data?.groups ?? [];

  const joinMut = useMutation({
    mutationFn: (id: number) => api.post<any>(`/saas/community/groups/${id}/join`, {}),
    onSuccess: () => { toast.success('Entrou no grupo!'); qc.invalidateQueries({ queryKey: ['community-groups'] }); },
  });

  if (activeGroup) return <GroupView group={activeGroup} onBack={() => setActiveGroup(null)} />;

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <div className="text-center">
        <h1 className="text-3xl font-black tracking-tight mb-2">👥 Comunidade</h1>
        <p className="text-zinc-400 text-sm">Grupos por signo, prática e tema — com IA Oráculo 24/7.</p>
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        {groups.map((g: any) => (
          <div key={g.id} onClick={() => setActiveGroup(g)} className="bg-zinc-900 border border-zinc-800 hover:border-accent-amethyst/30 rounded-2xl p-5 cursor-pointer transition-all">
            <div className="flex items-center gap-3 mb-2">
              <span className="text-2xl">{g.icon || '🔮'}</span>
              <div>
                <h3 className="font-black text-sm">{g.name}</h3>
                <span className="text-[10px] text-zinc-500">{g.member_count} membros • {g.post_count} posts</span>
              </div>
            </div>
            {g.description && <p className="text-[11px] text-zinc-500 line-clamp-2">{g.description}</p>}
            {!g.is_member && (
              <button onClick={(e) => { e.stopPropagation(); joinMut.mutate(g.id); }}
                className="mt-3 text-[10px] bg-accent-amethyst/10 text-accent-amethyst px-3 py-1 rounded-lg font-black uppercase tracking-widest">Entrar</button>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

function GroupView({ group, onBack }: { group: any; onBack: () => void }) {
  const qc = useQueryClient();
  const [newPost, setNewPost] = useState('');

  const { data } = useQuery({ queryKey: ['community-posts', group.id], queryFn: () => api.get<any>(`/saas/community/groups/${group.id}/posts`) });
  const posts = data?.posts ?? [];

  const postMut = useMutation({
    mutationFn: () => api.post<any>(`/saas/community/groups/${group.id}/posts`, { content: newPost }),
    onSuccess: () => { setNewPost(''); qc.invalidateQueries({ queryKey: ['community-posts', group.id] }); },
  });

  const oracleMut = useMutation({
    mutationFn: (pid: number) => api.post<any>(`/saas/community/posts/${pid}/oracle`, {}),
    onSuccess: () => { toast.success('🔮 Oráculo respondeu!'); qc.invalidateQueries({ queryKey: ['community-posts', group.id] }); },
  });

  const reactMut = useMutation({
    mutationFn: ({ pid, type }: { pid: number; type: string }) => api.post<any>(`/saas/community/posts/${pid}/react`, { reaction_type: type }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['community-posts', group.id] }),
  });

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <div className="flex items-center gap-3">
        <button onClick={onBack} className="w-9 h-9 rounded-xl bg-zinc-800 flex items-center justify-center"><ArrowLeft className="w-4 h-4" /></button>
        <span className="text-2xl">{group.icon}</span>
        <div>
          <h2 className="font-black">{group.name}</h2>
          <span className="text-[10px] text-zinc-500">{group.member_count} membros</span>
        </div>
      </div>

      <div className="flex gap-2">
        <input value={newPost} onChange={e => setNewPost(e.target.value)} placeholder="Compartilhe..."
          className="flex-1 bg-zinc-800 border border-zinc-700 rounded-xl px-3 py-2 text-sm outline-none focus:border-accent-amethyst/50"
          onKeyDown={e => e.key === 'Enter' && newPost && postMut.mutate()} />
        <button onClick={() => postMut.mutate()} disabled={!newPost.trim()}
          className="px-4 py-2 bg-accent-amethyst disabled:opacity-30 text-white rounded-xl"><Send className="w-4 h-4" /></button>
      </div>

      <div className="space-y-3">
        {posts.map((p: any) => (
          <div key={p.id} className={`bg-zinc-900 border rounded-2xl p-4 ${p.is_oracle_response ? 'border-accent-amethyst/30 bg-accent-amethyst/5' : 'border-zinc-800'}`}>
            {p.is_oracle_response && <div className="text-[9px] text-accent-amethyst font-bold flex items-center gap-1 mb-1"><Bot className="w-3 h-3" /> Oráculo IA</div>}
            <p className="text-sm whitespace-pre-wrap">{p.content}</p>
            <div className="flex items-center justify-between mt-2">
              <div className="flex gap-1">{REACTIONS.map(r => (
                <button key={r.type} onClick={() => reactMut.mutate({ pid: p.id, type: r.type })} className="text-xs px-1.5 py-0.5 rounded hover:bg-zinc-800">{r.emoji}</button>
              ))}{p.reaction_count > 0 && <span className="text-[10px] text-zinc-500 ml-1">{p.reaction_count}</span>}</div>
              <div className="flex gap-2 items-center">
                <span className="text-[10px] text-zinc-600">{new Date(p.created_at).toLocaleDateString('pt-BR')}</span>
                {group.oracle_enabled && !p.is_oracle_response && (
                  <button onClick={() => oracleMut.mutate(p.id)} className="text-[10px] text-accent-amethyst font-bold">🔮 Oráculo</button>
                )}
              </div>
            </div>
            {p.replies?.length > 0 && (
              <div className="mt-2 ml-3 border-l border-zinc-800 pl-3 space-y-2">
                {p.replies.map((r: any) => (
                  <div key={r.id} className={`text-xs ${r.is_oracle_response ? 'text-accent-amethyst' : 'text-zinc-500'}`}>
                    {r.is_oracle_response && <span className="text-[8px] font-bold">🔮</span>}
                    <p className="whitespace-pre-wrap">{r.content}</p>
                  </div>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
