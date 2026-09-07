import { useEffect, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  User, MapPin, Calendar, Sparkles, MessageSquare,
  TrendingUp, TrendingDown, Activity, Star, CreditCard,
  Wand2, Phone, Edit3, Save, X, Plus, Trash2, RefreshCw,
  StickyNote, Check, Copy, Tag, SlidersHorizontal,
} from 'lucide-react';
import { useLeadContext } from '../hooks/useLeadContext';
import { leadContextApi, type LeadNote } from '../api/leadContext';
import { handleApiError } from '../lib/handleApiError';
import { toast } from '../lib/toast';
import ScoreBadge from './ScoreBadge';
import AudioSuggestPanel from './AudioSuggestPanel';
import LeadSummaryCard from './LeadSummaryCard';

interface Props {
  leadId: number | null;
}

export default function LeadContextPanel({ leadId }: Props) {
  const { data, isLoading } = useLeadContext(leadId);

  if (!leadId) {
    return (
      <div className="p-6 text-center text-secondary text-sm">
        Selecione um lead pra ver o contexto
      </div>
    );
  }

  if (isLoading || !data) {
    return (
      <div className="p-6 space-y-4 animate-pulse">
        <div className="h-32 bg-bg-surface rounded-2xl" />
        <div className="h-24 bg-bg-surface rounded-2xl" />
        <div className="h-24 bg-bg-surface rounded-2xl" />
      </div>
    );
  }

  const { lead, score, journey, sentiment, commercial, tarot_readings_count, spiritual } = data;

  return (
    <div className="p-4 space-y-3 overflow-y-auto h-full">
      <EditableLeadCard leadId={leadId} lead={lead} />

      {/* Score */}
      <Card title="Score" icon={Activity}>
        <div className="flex items-center justify-between">
          <ScoreBadge band={score.band} value={score.value} size="md" showValue />
          <div className="text-2xl font-black tracking-tight">{score.value}</div>
        </div>
        {score.components && Object.keys(score.components).length > 0 && (
          <div className="space-y-1.5 mt-3 pt-3 border-t border-border">
            {Object.entries(score.components).map(([k, v]) => (
              <div key={k} className="flex items-center gap-2">
                <span className="text-[10px] text-secondary capitalize w-20">{k}</span>
                <div className="flex-1 h-1 bg-bg-primary rounded-full overflow-hidden">
                  <div
                    className="h-full bg-accent-amethyst"
                    style={{ width: `${v}%` }}
                  />
                </div>
                <span className="text-[10px] font-mono w-8 text-right">{v}</span>
              </div>
            ))}
          </div>
        )}
      </Card>

      {/* Jornada */}
      <Card title="Jornada" icon={Sparkles}>
        {journey.node_atual && (
          <KV k="Nó atual" v={journey.node_atual} />
        )}
        <KV k="Profundidade" v={`${journey.depth} nós`} />
        {journey.time_in_node_s !== null && (
          <KV k="No nó há" v={fmtDuration(journey.time_in_node_s)} />
        )}
        {journey.last_msg_at && (
          <KV k="Última msg" v={fmtRelative(journey.last_msg_at)} />
        )}
        <div className="flex flex-wrap gap-1.5 mt-2 pt-2 border-t border-border">
          {journey.convertido && (
            <span className="px-2 py-0.5 bg-emerald-500/10 text-emerald-500 text-[9px] font-black uppercase tracking-widest rounded border border-emerald-500/30">
              ✓ Convertido
            </span>
          )}
          {journey.bot_pausado && (
            <span className="px-2 py-0.5 bg-amber-500/10 text-amber-500 text-[9px] font-black uppercase tracking-widest rounded border border-amber-500/30">
              ⏸ Bot pausado
            </span>
          )}
          {journey.opt_out && (
            <span className="px-2 py-0.5 bg-red-500/10 text-red-500 text-[9px] font-black uppercase tracking-widest rounded border border-red-500/30">
              ✗ Opt-out
            </span>
          )}
        </div>
      </Card>

      {/* Sentimento */}
      <Card title="Sentimento" icon={MessageSquare}>
        <div className="flex items-center justify-between mb-2">
          <span className="text-[10px] text-secondary">Últimas 10 msgs:</span>
          <SentimentTrend trend={sentiment.trend} />
        </div>
        <div className="flex gap-1">
          {sentiment.recent.length === 0 ? (
            <span className="text-[11px] text-secondary">Sem dados</span>
          ) : (
            sentiment.recent.map((s, i) => (
              <div
                key={i}
                className={`w-2.5 h-2.5 rounded-full ${
                  s === 'pos' ? 'bg-emerald-500' :
                  s === 'neg' ? 'bg-red-500' :
                  'bg-zinc-600'
                }`}
                title={s}
              />
            ))
          )}
        </div>
        <div className="flex justify-between text-[10px] mt-2">
          <span className="text-emerald-500">+{sentiment.positive_count}</span>
          <span className="text-red-500">−{sentiment.negative_count}</span>
        </div>
      </Card>

      {/* Comercial */}
      <Card title="Comercial" icon={CreditCard}>
        <KV k="Pagamentos" v={String(commercial.payments_count)} />
        {commercial.payments.length > 0 && (
          <div className="mt-2 pt-2 border-t border-border space-y-1">
            {commercial.payments.slice(0, 3).map((p) => (
              <div key={p.id} className="flex items-center justify-between text-[10px]">
                <span className="font-mono text-secondary">{p.provider}</span>
                <span className="text-primary">
                  {p.processed_at && new Date(p.processed_at).toLocaleDateString('pt-BR')}
                </span>
              </div>
            ))}
          </div>
        )}
      </Card>

      <LeadSummaryCard leadId={leadId} />
      <AudioSuggestPanel leadId={leadId} />
      <NextActionCard leadId={leadId} />
      <NotesCard leadId={leadId} />
    </div>
  );
}

function Card({
  title, icon: Icon, children,
}: {
  title: string;
  icon: typeof User;
  children: React.ReactNode;
}) {
  return (
    <div className="bg-bg-surface border border-border rounded-2xl p-4">
      <div className="flex items-center gap-2 mb-2.5 pb-2 border-b border-border">
        <Icon className="w-3.5 h-3.5 text-accent-amethyst" />
        <span className="text-[10px] font-black uppercase tracking-widest text-secondary">{title}</span>
      </div>
      <div className="space-y-1.5">{children}</div>
    </div>
  );
}

function KV({
  k, v, icon: Icon,
}: {
  k: string;
  v: string;
  icon?: typeof User;
}) {
  return (
    <div className="flex items-center justify-between gap-2 text-[11px]">
      <span className="text-secondary flex items-center gap-1.5">
        {Icon && <Icon className="w-2.5 h-2.5" />}
        {k}
      </span>
      <span className="text-primary font-bold truncate max-w-[55%]" title={v}>{v}</span>
    </div>
  );
}

function SentimentTrend({ trend }: { trend: 'positive' | 'negative' | 'neutral' }) {
  if (trend === 'positive') {
    return (
      <span className="text-emerald-500 flex items-center gap-1 text-[10px] font-bold">
        <TrendingUp className="w-3 h-3" /> POSITIVO
      </span>
    );
  }
  if (trend === 'negative') {
    return (
      <span className="text-red-500 flex items-center gap-1 text-[10px] font-bold">
        <TrendingDown className="w-3 h-3" /> NEGATIVO
      </span>
    );
  }
  return <span className="text-secondary text-[10px] font-bold">Neutro</span>;
}

function fmtDuration(seconds: number): string {
  if (seconds < 60) return `${seconds}s`;
  if (seconds < 3600) return `${Math.round(seconds / 60)}min`;
  if (seconds < 86400) return `${Math.round(seconds / 3600)}h`;
  return `${Math.round(seconds / 86400)}d`;
}

function fmtRelative(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const min = Math.floor(diff / 60000);
  if (min < 1) return 'agora';
  if (min < 60) return `${min}min atrás`;
  const h = Math.floor(min / 60);
  if (h < 24) return `${h}h atrás`;
  return `${Math.floor(h / 24)}d atrás`;
}


// ─── Editable Lead card (3.18) ─────────────────────────────────────


function EditableLeadCard({
  leadId, lead,
}: {
  leadId: number;
  lead: {
    nome: string | null;
    telefone: string;
    email: string | null;
    signo: string | null;
    idade: number | null;
    cidade: string | null;
    tags: string[];
    custom_fields: Record<string, unknown>;
    criado_em: string | null;
  };
}) {
  const qc = useQueryClient();
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState({
    nome: lead.nome || '',
    signo: lead.signo || '',
    idade: lead.idade != null ? String(lead.idade) : '',
    cidade: lead.cidade || '',
    email: lead.email || '',
    tags: (lead.tags || []).join(', '),
  });

  useEffect(() => {
    if (!editing) {
      setDraft({
        nome: lead.nome || '',
        signo: lead.signo || '',
        idade: lead.idade != null ? String(lead.idade) : '',
        cidade: lead.cidade || '',
        email: lead.email || '',
        tags: (lead.tags || []).join(', '),
      });
    }
  }, [lead, editing]);

  const saveMut = useMutation({
    mutationFn: () => leadContextApi.patchProfile(leadId, {
      nome: draft.nome.trim() || null,
      signo: draft.signo.trim() || null,
      idade: draft.idade ? Number(draft.idade) : null,
      cidade: draft.cidade.trim() || null,
      email: draft.email.trim() || null,
      tags: draft.tags.split(',').map((t) => t.trim()).filter(Boolean),
    }),
    onSuccess: () => {
      toast.success('Perfil atualizado');
      qc.invalidateQueries({ queryKey: ['lead-context', leadId] });
      qc.invalidateQueries({ queryKey: ['leads-list'] });
      setEditing(false);
    },
    onError: handleApiError('Erro ao salvar'),
  });

  return (
    <div className="bg-bg-surface border border-border rounded-2xl p-4">
      <div className="flex items-center justify-between mb-2.5 pb-2 border-b border-border">
        <div className="flex items-center gap-2">
          <User className="w-3.5 h-3.5 text-accent-amethyst" />
          <span className="text-[10px] font-black uppercase tracking-widest text-secondary">Lead</span>
        </div>
        {!editing ? (
          <button
            onClick={() => setEditing(true)}
            className="text-[10px] text-secondary hover:text-accent-amethyst flex items-center gap-1 font-bold"
          >
            <Edit3 className="w-3 h-3" />
            Editar
          </button>
        ) : (
          <div className="flex gap-1">
            <button
              onClick={() => setEditing(false)}
              className="text-[10px] text-secondary hover:text-primary flex items-center gap-0.5 font-bold"
            >
              <X className="w-3 h-3" /> cancelar
            </button>
            <button
              onClick={() => saveMut.mutate()}
              disabled={saveMut.isPending}
              className="text-[10px] text-accent-amethyst hover:underline flex items-center gap-0.5 font-bold"
            >
              <Save className="w-3 h-3" /> {saveMut.isPending ? 'salvando…' : 'salvar'}
            </button>
          </div>
        )}
      </div>

      {!editing ? (
        <div className="space-y-1.5">
          <KV k="Nome" v={lead.nome || '—'} />
          <KV k="Telefone" v={lead.telefone} icon={Phone} />
          {lead.email && <KV k="Email" v={lead.email} />}
          {lead.signo && <KV k="Signo" v={lead.signo} icon={Star} />}
          {lead.idade != null && <KV k="Idade" v={`${lead.idade} anos`} icon={Calendar} />}
          {lead.cidade && <KV k="Cidade" v={lead.cidade} icon={MapPin} />}
          {lead.criado_em && (
            <KV k="Cliente desde" v={new Date(lead.criado_em).toLocaleDateString('pt-BR')} />
          )}
          <LeadTagsManager leadId={leadId} tags={lead.tags || []} />
          <LeadCustomFieldsManager leadId={leadId} customFields={lead.custom_fields || {}} />
        </div>
      ) : (
        <div className="space-y-2">
          <FieldEdit label="Nome" value={draft.nome} onChange={(v) => setDraft({ ...draft, nome: v })} />
          <FieldEdit label="Email" value={draft.email} onChange={(v) => setDraft({ ...draft, email: v })} />
          <FieldEdit label="Signo" value={draft.signo} onChange={(v) => setDraft({ ...draft, signo: v })} />
          <div className="grid grid-cols-2 gap-2">
            <FieldEdit label="Idade" value={draft.idade} onChange={(v) => setDraft({ ...draft, idade: v.replace(/[^0-9]/g, '') })} />
            <FieldEdit label="Cidade" value={draft.cidade} onChange={(v) => setDraft({ ...draft, cidade: v })} />
          </div>
          <FieldEdit
            label="Tags (separadas por vírgula)"
            value={draft.tags}
            onChange={(v) => setDraft({ ...draft, tags: v })}
          />
        </div>
      )}
    </div>
  );
}

function LeadTagsManager({
  leadId, tags,
}: {
  leadId: number;
  tags: string[];
}) {
  const qc = useQueryClient();
  const [adding, setAdding] = useState(false);
  const [newTag, setNewTag] = useState('');

  const { data: tenantTagsData } = useQuery({
    queryKey: ['tenant-tags'],
    queryFn: leadContextApi.listTenantTags,
    staleTime: 60_000,
  });
  const allTenantTags = tenantTagsData?.tags || [];
  const suggestions = allTenantTags.filter((t) => !tags.includes(t) && t.toLowerCase().includes(newTag.toLowerCase()));

  const addMut = useMutation({
    mutationFn: (tag: string) => leadContextApi.addTag(leadId, tag),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['lead-context', leadId] });
      qc.invalidateQueries({ queryKey: ['leads-list'] });
      qc.invalidateQueries({ queryKey: ['tenant-tags'] });
      setNewTag('');
    },
    onError: handleApiError('Erro ao adicionar tag'),
  });

  const removeMut = useMutation({
    mutationFn: (tag: string) => leadContextApi.removeTag(leadId, tag),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['lead-context', leadId] });
      qc.invalidateQueries({ queryKey: ['leads-list'] });
    },
    onError: handleApiError('Erro ao remover tag'),
  });

  const handleAdd = (tagToAdd: string) => {
    const clean = tagToAdd.trim().toLowerCase();
    if (!clean || tags.includes(clean)) return;
    addMut.mutate(clean);
  };

  return (
    <div className="pt-2.5 mt-2.5 border-t border-border">
      <div className="flex items-center justify-between mb-1.5">
        <div className="flex items-center gap-1.5">
          <Tag className="w-3 h-3 text-accent-amethyst" />
          <span className="text-[9px] font-black uppercase tracking-widest text-secondary">Tags</span>
        </div>
        <button
          onClick={() => setAdding(!adding)}
          className="text-[9px] font-bold text-accent-amethyst hover:underline flex items-center gap-0.5"
        >
          <Plus className="w-2.5 h-2.5" /> {adding ? 'fechar' : 'adicionar'}
        </button>
      </div>

      <div className="flex flex-wrap gap-1 items-center">
        {tags.length === 0 && !adding && (
          <span className="text-[10px] text-secondary italic">Nenhuma tag</span>
        )}
        {tags.map((t, i) => (
          <span
            key={`${t}-${i}`}
            className={`text-[10px] pl-2 pr-1 py-0.5 rounded-md font-bold flex items-center gap-1 group ${
              t === 'opted_out'
                ? 'bg-red-500/10 text-red-400 border border-red-500/30'
                : 'bg-bg-primary text-primary border border-border'
            }`}
          >
            {t}
            <button
              onClick={() => removeMut.mutate(t)}
              disabled={removeMut.isPending}
              title={`Remover tag ${t}`}
              className="text-secondary hover:text-red-400 p-0.5 rounded transition-colors"
            >
              <X className="w-2.5 h-2.5" />
            </button>
          </span>
        ))}
      </div>

      {adding && (
        <div className="mt-2 space-y-1.5">
          <div className="flex gap-1">
            <input
              type="text"
              value={newTag}
              onChange={(e) => setNewTag(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') {
                  e.preventDefault();
                  handleAdd(newTag);
                }
              }}
              placeholder="Digite uma tag (ex: vip, hot)..."
              className="flex-1 bg-bg-primary border border-border rounded-lg px-2 py-1 text-[11px] focus:outline-none focus:border-accent-amethyst"
              autoFocus
            />
            <button
              onClick={() => handleAdd(newTag)}
              disabled={!newTag.trim() || addMut.isPending}
              className="px-2.5 py-1 bg-accent-amethyst text-white text-[10px] font-bold rounded-lg disabled:opacity-40"
            >
              Add
            </button>
          </div>

          {suggestions.length > 0 && (
            <div className="flex flex-wrap gap-1 mt-1 max-h-20 overflow-y-auto">
              <span className="text-[9px] text-secondary w-full">Sugestões:</span>
              {suggestions.slice(0, 6).map((s) => (
                <button
                  key={s}
                  onClick={() => handleAdd(s)}
                  className="text-[9px] px-1.5 py-0.5 bg-accent-amethyst/10 text-accent-amethyst hover:bg-accent-amethyst/20 rounded border border-accent-amethyst/20 font-medium"
                >
                  +{s}
                </button>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function LeadCustomFieldsManager({
  leadId, customFields,
}: {
  leadId: number;
  customFields: Record<string, unknown>;
}) {
  const qc = useQueryClient();
  const [adding, setAdding] = useState(false);
  const [key, setKey] = useState('');
  const [val, setVal] = useState('');

  const entries = Object.entries(customFields || {});

  const saveMut = useMutation({
    mutationFn: (updatedFields: Record<string, unknown>) =>
      leadContextApi.patchProfile(leadId, {
        custom_fields: updatedFields as Record<string, string | number | boolean>,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['lead-context', leadId] });
      setKey('');
      setVal('');
      setAdding(false);
      toast.success('Campos personalizados atualizados');
    },
    onError: handleApiError('Erro ao salvar campo'),
  });

  const handleAdd = () => {
    const cleanKey = key.trim();
    const cleanVal = val.trim();
    if (!cleanKey) return;
    const updated = { ...customFields, [cleanKey]: cleanVal };
    saveMut.mutate(updated);
  };

  const handleRemove = (targetKey: string) => {
    const updated = { ...customFields };
    delete updated[targetKey];
    saveMut.mutate(updated);
  };

  return (
    <div className="pt-2.5 mt-2.5 border-t border-border">
      <div className="flex items-center justify-between mb-1.5">
        <div className="flex items-center gap-1.5">
          <SlidersHorizontal className="w-3 h-3 text-accent-amethyst" />
          <span className="text-[9px] font-black uppercase tracking-widest text-secondary">Campos Personalizados</span>
        </div>
        <button
          onClick={() => setAdding(!adding)}
          className="text-[9px] font-bold text-accent-amethyst hover:underline flex items-center gap-0.5"
        >
          <Plus className="w-2.5 h-2.5" /> {adding ? 'fechar' : 'adicionar'}
        </button>
      </div>

      <div className="space-y-1">
        {entries.length === 0 && !adding && (
          <span className="text-[10px] text-secondary italic">Nenhum campo personalizado</span>
        )}
        {entries.map(([k, v]) => (
          <div key={k} className="flex items-center justify-between gap-1 text-[10px] bg-bg-primary/50 px-2 py-1 rounded-lg border border-border/60">
            <span className="font-mono text-secondary truncate max-w-[45%]" title={k}>{k}:</span>
            <div className="flex items-center gap-1.5 truncate">
              <span className="font-medium text-primary truncate max-w-[120px]" title={String(v)}>{String(v)}</span>
              <button
                onClick={() => handleRemove(k)}
                disabled={saveMut.isPending}
                title={`Remover ${k}`}
                className="text-secondary hover:text-red-400 transition-colors p-0.5"
              >
                <X className="w-2.5 h-2.5" />
              </button>
            </div>
          </div>
        ))}
      </div>

      {adding && (
        <div className="mt-2 p-2 bg-bg-primary rounded-xl border border-border space-y-1.5">
          <input
            type="text"
            value={key}
            onChange={(e) => setKey(e.target.value)}
            placeholder="Nome do campo (ex: nicho, vip)"
            className="w-full bg-bg-surface border border-border rounded-lg px-2 py-1 text-[11px] font-mono focus:outline-none focus:border-accent-amethyst"
            autoFocus
          />
          <input
            type="text"
            value={val}
            onChange={(e) => setVal(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') {
                e.preventDefault();
                handleAdd();
              }
            }}
            placeholder="Valor (ex: psicologia, sim)"
            className="w-full bg-bg-surface border border-border rounded-lg px-2 py-1 text-[11px] focus:outline-none focus:border-accent-amethyst"
          />
          <button
            onClick={handleAdd}
            disabled={!key.trim() || saveMut.isPending}
            className="w-full py-1 bg-accent-amethyst text-white text-[10px] font-bold rounded-lg disabled:opacity-40"
          >
            {saveMut.isPending ? 'Salvando...' : 'Salvar Campo'}
          </button>
        </div>
      )}
    </div>
  );
}

function FieldEdit({
  label, value, onChange,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
}) {
  return (
    <div>
      <label className="text-[9px] font-black uppercase tracking-widest text-secondary block mb-0.5">
        {label}
      </label>
      <input
        type="text"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="w-full bg-bg-primary border border-border rounded-lg px-2.5 py-1.5 text-[11px]"
      />
    </div>
  );
}


// ─── Spiritual intent classifier (4.19) ───────────────────────────


const SPIRITUAL_EMOJI: Record<string, string> = {
  amor: '❤️', dinheiro: '💰', saude: '🌿', carreira: '💼',
  familia: '🏠', espiritual: '🙏', decisao: '🔀', luto: '🕊️',
};

function SpiritualIntentCard({
  leadId, spiritual,
}: {
  leadId: number;
  spiritual?: {
    category: string | null;
    intent: {
      categories?: string[];
      categories_distribution?: Record<string, number>;
      urgency?: 'low' | 'med' | 'high';
      emotion?: string | null;
      msgs_analyzed?: number;
    } | null;
    computed_at: string | null;
  };
}) {
  const qc = useQueryClient();
  const recomputeMut = useMutation({
    mutationFn: () => fetch(`/saas/inbox/${leadId}/spiritual-intent/recompute`, {
      method: 'POST',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ last_n: 10 }),
    }).then(async (r) => {
      const data = await r.json();
      if (!r.ok) throw new Error(data?.message || data?.error || 'recompute_failed');
      return data;
    }),
    onSuccess: () => {
      toast.success('Intent espiritual recomputado');
      qc.invalidateQueries({ queryKey: ['lead-context', leadId] });
      qc.invalidateQueries({ queryKey: ['leads-list'] });
    },
    onError: (e) => toast.error((e as Error).message),
  });

  const intent = spiritual?.intent;
  const urgencyColor = {
    high: 'text-rose-400',
    med: 'text-amber-400',
    low: 'text-emerald-400',
  } as const;

  return (
    <div className="bg-bg-surface border border-border rounded-2xl p-4">
      <div className="flex items-center justify-between mb-2.5 pb-2 border-b border-border">
        <div className="flex items-center gap-2">
          <Sparkles className="w-3.5 h-3.5 text-accent-amethyst" />
          <span className="text-[10px] font-black uppercase tracking-widest text-secondary">
            Tema espiritual
          </span>
        </div>
        <button
          onClick={() => recomputeMut.mutate()}
          disabled={recomputeMut.isPending}
          className="text-[10px] text-accent-amethyst hover:underline flex items-center gap-1 font-bold"
        >
          <RefreshCw className={`w-3 h-3 ${recomputeMut.isPending ? 'animate-spin' : ''}`} />
          {spiritual?.category ? 'Atualizar' : 'Classificar'}
        </button>
      </div>

      {!spiritual?.category ? (
        <p className="text-[11px] text-secondary text-center py-2">
          Ainda não classificado.
        </p>
      ) : (
        <div className="space-y-2">
          <div className="flex items-center gap-2">
            <span className="text-2xl">{SPIRITUAL_EMOJI[spiritual.category] || '✦'}</span>
            <div className="flex-1">
              <div className="text-sm font-black capitalize">{spiritual.category}</div>
              {intent?.urgency && (
                <div className={`text-[10px] uppercase font-black tracking-widest ${urgencyColor[intent.urgency]}`}>
                  Urgência {intent.urgency}
                </div>
              )}
            </div>
          </div>
          {intent?.emotion && (
            <KV k="Emoção" v={intent.emotion} />
          )}
          {intent?.categories_distribution && Object.keys(intent.categories_distribution).length > 1 && (
            <div className="pt-2 border-t border-border">
              <div className="text-[9px] font-black uppercase tracking-widest text-secondary mb-1.5">
                Outras menções
              </div>
              <div className="flex flex-wrap gap-1">
                {Object.entries(intent.categories_distribution).map(([cat, n]) => (
                  <span key={cat} className="text-[10px] bg-bg-primary border border-border px-1.5 rounded">
                    {SPIRITUAL_EMOJI[cat] || '·'} {cat}: {n}
                  </span>
                ))}
              </div>
            </div>
          )}
          {intent?.msgs_analyzed != null && (
            <div className="text-[10px] text-secondary mt-1">
              {intent.msgs_analyzed} mensagem{intent.msgs_analyzed === 1 ? '' : 's'} analisada{intent.msgs_analyzed === 1 ? '' : 's'}
            </div>
          )}
        </div>
      )}
    </div>
  );
}


// ─── Next-action AI suggestion (3.21) ──────────────────────────────


function NextActionCard({ leadId }: { leadId: number }) {
  const qc = useQueryClient();
  const [copied, setCopied] = useState(false);

  const { data, isLoading, isFetching } = useQuery({
    queryKey: ['next-action', leadId],
    queryFn: () => leadContextApi.nextAction(leadId, false),
    staleTime: 0,
    enabled: false, // bota gerar manualmente
  });

  const triggerMut = useMutation({
    mutationFn: (force: boolean) => leadContextApi.nextAction(leadId, force),
    onSuccess: (res) => {
      qc.setQueryData(['next-action', leadId], res);
    },
    onError: handleApiError('Erro ao sugerir ação'),
  });

  const sug = data?.suggestion || triggerMut.data?.suggestion;
  const cached = data?.cached || triggerMut.data?.cached;
  const loading = isLoading || isFetching || triggerMut.isPending;

  const copyMessage = () => {
    if (!sug?.message) return;
    navigator.clipboard.writeText(sug.message);
    setCopied(true);
    setTimeout(() => setCopied(false), 1800);
  };

  return (
    <div className="bg-bg-surface border border-border rounded-2xl p-4">
      <div className="flex items-center justify-between mb-2.5 pb-2 border-b border-border">
        <div className="flex items-center gap-2">
          <Wand2 className="w-3.5 h-3.5 text-accent-amethyst" />
          <span className="text-[10px] font-black uppercase tracking-widest text-secondary">
            IA sugere próxima ação
          </span>
        </div>
        <button
          onClick={() => triggerMut.mutate(!!sug)}
          disabled={loading}
          className="text-[10px] text-accent-amethyst hover:underline flex items-center gap-1 font-bold"
        >
          <RefreshCw className={`w-3 h-3 ${loading ? 'animate-spin' : ''}`} />
          {sug ? (cached ? 'Atualizar' : 'Regen') : 'Gerar'}
        </button>
      </div>

      {!sug && !loading ? (
        <p className="text-[11px] text-secondary text-center py-3">
          Clique "Gerar" para a IA analisar a conversa e sugerir o próximo passo.
        </p>
      ) : loading ? (
        <p className="text-[11px] text-secondary text-center py-3">Pensando…</p>
      ) : sug ? (
        <div className="space-y-2">
          <div>
            <div className="text-[9px] font-black uppercase tracking-widest text-secondary">Estado</div>
            <div className="text-[11px] text-primary mt-0.5">{sug.summary}</div>
          </div>
          <div>
            <div className="text-[9px] font-black uppercase tracking-widest text-secondary">Ação sugerida</div>
            <div className="text-[11px] text-primary mt-0.5">{sug.action}</div>
          </div>
          {sug.message && (
            <div>
              <div className="text-[9px] font-black uppercase tracking-widest text-secondary mb-0.5">Mensagem pronta</div>
              <div className="bg-bg-primary border border-border rounded-lg p-2.5 text-[11px] leading-relaxed">
                {sug.message}
              </div>
              <button
                onClick={copyMessage}
                className="mt-1.5 text-[10px] text-accent-amethyst hover:underline flex items-center gap-1 font-bold"
              >
                {copied ? <Check className="w-3 h-3" /> : <Copy className="w-3 h-3" />}
                {copied ? 'Copiado' : 'Copiar mensagem'}
              </button>
            </div>
          )}
        </div>
      ) : null}
    </div>
  );
}


// ─── Notes (3.23) ──────────────────────────────────────────────────


function NotesCard({ leadId }: { leadId: number }) {
  const qc = useQueryClient();
  const [draft, setDraft] = useState('');

  const { data, isLoading } = useQuery({
    queryKey: ['lead-notes', leadId],
    queryFn: () => leadContextApi.listNotes(leadId),
  });

  const createMut = useMutation({
    mutationFn: () => leadContextApi.createNote(leadId, draft.trim()),
    onSuccess: () => {
      setDraft('');
      qc.invalidateQueries({ queryKey: ['lead-notes', leadId] });
    },
    onError: handleApiError('Erro ao criar nota'),
  });

  const deleteMut = useMutation({
    mutationFn: (id: number) => leadContextApi.deleteNote(leadId, id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['lead-notes', leadId] }),
    onError: handleApiError('Erro ao remover'),
  });

  const items = data?.notes ?? [];

  return (
    <div className="bg-bg-surface border border-border rounded-2xl p-4">
      <div className="flex items-center gap-2 mb-2.5 pb-2 border-b border-border">
        <StickyNote className="w-3.5 h-3.5 text-accent-amethyst" />
        <span className="text-[10px] font-black uppercase tracking-widest text-secondary">
          Notas internas
        </span>
        <span className="text-[10px] text-secondary ml-auto">{items.length}</span>
      </div>

      <div className="space-y-2">
        <textarea
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          rows={2}
          maxLength={8000}
          placeholder="Anote algo sobre este lead…"
          className="w-full bg-bg-primary border border-border rounded-lg px-2.5 py-1.5 text-[11px] resize-none"
        />
        <button
          onClick={() => createMut.mutate()}
          disabled={!draft.trim() || createMut.isPending}
          className="w-full px-3 py-1.5 bg-accent-amethyst hover:bg-accent-amethyst/90 disabled:opacity-30 text-white rounded-lg text-[10px] font-black uppercase tracking-widest flex items-center justify-center gap-1"
        >
          <Plus className="w-3 h-3" />
          {createMut.isPending ? 'Salvando…' : 'Adicionar nota'}
        </button>
      </div>

      <div className="space-y-2 mt-3">
        {isLoading ? (
          <div className="text-[10px] text-secondary text-center py-2">Carregando…</div>
        ) : items.length === 0 ? (
          <div className="text-[10px] text-secondary text-center py-2">Sem notas ainda.</div>
        ) : (
          items.map((n: LeadNote) => <NoteRow key={n.id} note={n} leadId={leadId} onDelete={() => deleteMut.mutate(n.id)} />)
        )}
      </div>
    </div>
  );
}

function NoteRow({
  note, leadId, onDelete,
}: {
  note: LeadNote;
  leadId: number;
  onDelete: () => void;
}) {
  const qc = useQueryClient();
  const [editing, setEditing] = useState(false);
  const [text, setText] = useState(note.content);

  useEffect(() => { if (!editing) setText(note.content); }, [note.content, editing]);

  const saveMut = useMutation({
    mutationFn: () => leadContextApi.updateNote(leadId, note.id, text.trim()),
    onSuccess: () => {
      setEditing(false);
      qc.invalidateQueries({ queryKey: ['lead-notes', leadId] });
    },
    onError: handleApiError('Erro ao salvar nota'),
  });

  return (
    <div className="bg-bg-primary border border-border rounded-lg p-2 group">
      {editing ? (
        <>
          <textarea
            value={text}
            onChange={(e) => setText(e.target.value)}
            rows={3}
            className="w-full bg-bg-surface border border-border rounded px-2 py-1.5 text-[11px] resize-none"
          />
          <div className="flex justify-end gap-1.5 mt-1">
            <button
              onClick={() => setEditing(false)}
              className="text-[10px] text-secondary hover:text-primary"
            >
              cancelar
            </button>
            <button
              onClick={() => saveMut.mutate()}
              disabled={!text.trim() || saveMut.isPending}
              className="text-[10px] text-accent-amethyst font-bold hover:underline disabled:opacity-30"
            >
              {saveMut.isPending ? 'salvando…' : 'salvar'}
            </button>
          </div>
        </>
      ) : (
        <>
          <p className="text-[11px] leading-relaxed whitespace-pre-wrap">{note.content}</p>
          <div className="flex justify-between items-center mt-1.5 opacity-60 group-hover:opacity-100 transition-opacity">
            <span className="text-[9px] text-secondary">
              {fmtRelative(note.updated_at || note.created_at)}
            </span>
            <div className="flex gap-1">
              <button
                onClick={() => setEditing(true)}
                className="text-secondary hover:text-accent-amethyst p-0.5"
                title="Editar"
              >
                <Edit3 className="w-2.5 h-2.5" />
              </button>
              <button
                onClick={() => {
                  if (confirm('Remover esta nota?')) onDelete();
                }}
                className="text-secondary hover:text-rose-400 p-0.5"
                title="Remover"
              >
                <Trash2 className="w-2.5 h-2.5" />
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
