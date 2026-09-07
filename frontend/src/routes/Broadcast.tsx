import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Send, Plus, Users, CheckCircle2, XCircle, Clock, Megaphone, CalendarClock } from 'lucide-react';
import { broadcastApi, type Campaign } from '../api/saas';
import { handleApiError } from '../lib/handleApiError';
import { toast } from '../lib/toast';

export default function Broadcast() {
  const qc = useQueryClient();
  const [showCreate, setShowCreate] = useState(false);

  const { data, isLoading } = useQuery({ queryKey: ['broadcast-campaigns'], queryFn: broadcastApi.campaigns });
  const items = data?.campaigns ?? [];

  return (
    <div className="p-10 max-w-5xl mx-auto space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-3 mb-2">
            <div className="w-10 h-10 rounded-2xl bg-accent-amethyst/10 flex items-center justify-center">
              <Megaphone className="w-5 h-5 text-accent-amethyst" />
            </div>
            <h1 className="text-3xl font-black tracking-tight">Broadcast</h1>
          </div>
          <p className="text-secondary text-sm font-medium">Envie mensagens em massa para seus contatos via WhatsApp — segmente por tags, signo, score.</p>
        </div>
        <button onClick={() => setShowCreate(true)} className="flex items-center gap-2 px-5 py-3 bg-accent-amethyst hover:bg-accent-amethyst/90 text-white rounded-2xl font-black uppercase tracking-widest text-xs transition-all">
          <Plus className="w-4 h-4" /> Nova Campanha
        </button>
      </div>

      {isLoading ? (
        <div className="space-y-3 animate-pulse">{[1,2,3].map(i => <div key={i} className="h-24 bg-bg-surface rounded-2xl" />)}</div>
      ) : items.length === 0 ? (
        <div className="bg-bg-surface border border-dashed border-border rounded-3xl p-12 text-center">
          <Megaphone className="w-12 h-12 mx-auto text-secondary/40 mb-4" />
          <h3 className="font-black text-lg mb-2">Nenhuma campanha</h3>
          <p className="text-secondary text-sm mb-4">Crie sua primeira campanha de broadcast para engajar seus contatos.</p>
          <button onClick={() => setShowCreate(true)} className="px-5 py-3 bg-accent-amethyst text-white rounded-2xl text-xs font-black uppercase tracking-widest">Criar Campanha</button>
        </div>
      ) : (
        <div className="space-y-3">
          {items.map(c => (
            <CampaignCard key={c.id} campaign={c} onRefresh={() => qc.invalidateQueries({ queryKey: ['broadcast-campaigns'] })} />
          ))}
        </div>
      )}

      {showCreate && <CreateCampaignModal onClose={() => setShowCreate(false)} onCreated={() => { setShowCreate(false); qc.invalidateQueries({ queryKey: ['broadcast-campaigns'] }); }} />}
    </div>
  );
}

function CampaignCard({ campaign: c, onRefresh }: { campaign: Campaign; onRefresh: () => void }) {
  const sendMut = useMutation({
    mutationFn: () => broadcastApi.send(c.id),
    onSuccess: (res) => { toast.success(`Campanha enviada! ${res.total_queued} mensagens na fila.`); onRefresh(); },
    onError: handleApiError('Erro ao enviar'),
  });

  const statusConfig: Record<string, { color: string; label: string; Icon: typeof Clock }> = {
    draft: { color: 'text-amber-400 bg-amber-500/10 border-amber-500/30', label: 'Rascunho', Icon: Clock },
    scheduled: { color: 'text-blue-400 bg-blue-500/10 border-blue-500/30', label: 'Agendado', Icon: CalendarClock },
    sending: { color: 'text-blue-400 bg-blue-500/10 border-blue-500/30', label: 'Enviando', Icon: Send },
    sent: { color: 'text-emerald-500 bg-emerald-500/10 border-emerald-500/30', label: 'Enviado', Icon: CheckCircle2 },
    completed: { color: 'text-emerald-500 bg-emerald-500/10 border-emerald-500/30', label: 'Concluído', Icon: CheckCircle2 },
    failed: { color: 'text-red-400 bg-red-500/10 border-red-500/30', label: 'Falhou', Icon: XCircle },
  };
  const cfg = statusConfig[c.status] || statusConfig.draft;

  return (
    <div className="bg-bg-surface border border-border hover:border-accent-amethyst/20 rounded-2xl p-5 transition-all">
      <div className="flex items-start justify-between mb-3">
        <div>
          <h3 className="font-black text-sm">{c.name}</h3>
          <p className="text-[11px] text-secondary mt-1 line-clamp-1">{c.message_template}</p>
        </div>
        <span className={`text-[9px] font-black uppercase tracking-widest px-2.5 py-1 rounded-lg border ${cfg.color}`}>{cfg.label}</span>
      </div>
      <div className="flex items-center gap-4 text-[11px] text-secondary mb-3">
        <span className="flex items-center gap-1"><Users className="w-3 h-3" />{c.total_recipients} destinatários</span>
        <span className="flex items-center gap-1"><CheckCircle2 className="w-3 h-3" />{c.total_delivered} entregues</span>
        {c.total_failed > 0 && <span className="flex items-center gap-1 text-red-400"><XCircle className="w-3 h-3" />{c.total_failed} falhas</span>}
        {c.scheduled_at ? (
          <span className="flex items-center gap-1 text-blue-400">
            <CalendarClock className="w-3 h-3" />
            {new Date(c.scheduled_at).toLocaleString('pt-BR', { dateStyle: 'short', timeStyle: 'short' })}
          </span>
        ) : (
          <span>{new Date(c.created_at).toLocaleDateString('pt-BR')}</span>
        )}
      </div>
      {c.status === 'draft' && (
        <div className="flex gap-2">
          <button onClick={() => sendMut.mutate()} disabled={sendMut.isPending}
            className="flex items-center gap-2 px-4 py-2 bg-accent-amethyst/10 text-accent-amethyst hover:bg-accent-amethyst/20 rounded-xl text-[10px] font-black uppercase tracking-widest transition-all">
            <Send className="w-3 h-3" /> {sendMut.isPending ? 'Enviando...' : 'Enviar Agora'}
          </button>
        </div>
      )}
      {(c.status === 'sent' || c.status === 'completed') && c.total_recipients > 0 && (
        <div className="w-full bg-bg-primary rounded-full h-2 mt-1">
          <div className="bg-emerald-500 h-2 rounded-full transition-all" style={{ width: `${Math.round((c.total_delivered / c.total_recipients) * 100)}%` }} />
        </div>
      )}
    </div>
  );
}

function CreateCampaignModal({ onClose, onCreated }: { onClose: () => void; onCreated: () => void }) {
  const [name, setName] = useState('');
  const [message, setMessage] = useState('');
  const [filterTag, setFilterTag] = useState('');
  const [scheduledAt, setScheduledAt] = useState('');

  const createMut = useMutation({
    mutationFn: () => broadcastApi.create({
      name,
      message_template: message,
      segment_filters: filterTag ? { tags: [filterTag] } : {},
      ...(scheduledAt ? { scheduled_at: new Date(scheduledAt).toISOString(), status: 'scheduled' } : {}),
    }),
    onSuccess: () => { toast.success(scheduledAt ? 'Campanha agendada!' : 'Campanha criada!'); onCreated(); },
    onError: handleApiError('Erro ao criar campanha'),
  });

  return (
    <div className="fixed inset-0 z-50 bg-black/70 flex items-center justify-center p-6">
      <div className="bg-bg-surface border border-border rounded-3xl p-8 max-w-md w-full space-y-5">
        <h2 className="text-xl font-black tracking-tight">Nova Campanha</h2>
        <F label="Nome da campanha"><input value={name} onChange={e => setName(e.target.value)} placeholder="Promoção de Junho" className="inp" /></F>
        <F label="Mensagem">
          <textarea value={message} onChange={e => setMessage(e.target.value)} rows={4} placeholder="Olá {nome}! Tenho uma novidade especial..." className="inp resize-none" />
          <div className="text-[10px] text-secondary mt-1">Use {'{nome}'} para personalizar com o nome do lead.</div>
        </F>
        <F label="Filtro por tag (opcional)"><input value={filterTag} onChange={e => setFilterTag(e.target.value)} placeholder="vip, tarot, retiro..." className="inp" /></F>
        <F label="Agendar para (opcional)">
          <input
            type="datetime-local"
            value={scheduledAt}
            onChange={e => setScheduledAt(e.target.value)}
            className="inp"
          />
          <div className="text-[10px] text-secondary mt-1">Deixe em branco para enviar manualmente.</div>
        </F>
        <div className="flex gap-3">
          <button onClick={onClose} className="flex-1 px-5 py-3 bg-bg-primary border border-border rounded-2xl text-sm font-bold">Cancelar</button>
          <button onClick={() => createMut.mutate()} disabled={!name || !message || createMut.isPending} className="flex-1 px-5 py-3 bg-accent-amethyst hover:bg-accent-amethyst/90 disabled:opacity-30 text-white rounded-2xl text-sm font-black uppercase tracking-widest">
            {createMut.isPending ? 'Criando...' : scheduledAt ? 'Agendar' : 'Criar'}
          </button>
        </div>
      </div>
    </div>
  );
}

function F({ label, children }: { label: string; children: React.ReactNode }) {
  return <div><label className="text-[10px] uppercase font-black tracking-widest text-secondary mb-1.5 block">{label}</label>{children}</div>;
}
