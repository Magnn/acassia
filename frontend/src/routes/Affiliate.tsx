import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Users, Copy, TrendingUp, Crown, Award, Handshake,
  CheckCircle2, Calendar, Wallet,
} from 'lucide-react';
import { affiliateApi } from '../api/affiliate';
import { handleApiError } from '../lib/handleApiError';
import { toast } from '../lib/toast';

const TIER_COLORS: Record<string, string> = {
  standard: 'text-zinc-400 bg-zinc-500/10 border-zinc-500/30',
  silver: 'text-gray-200 bg-gray-300/10 border-gray-300/30',
  gold: 'text-amber-400 bg-amber-500/10 border-amber-500/30',
};

export default function Affiliate() {
  const qc = useQueryClient();

  const { data: me, isLoading } = useQuery({
    queryKey: ['affiliate-me'],
    queryFn: affiliateApi.me,
  });

  const enrollMut = useMutation({
    mutationFn: () => affiliateApi.enroll(),
    onSuccess: () => {
      toast.success('Você é afiliado agora!');
      qc.invalidateQueries({ queryKey: ['affiliate-me'] });
    },
    onError: handleApiError('Erro ao virar afiliado'),
  });

  if (isLoading) {
    return (
      <div className="p-10 max-w-5xl mx-auto animate-pulse">
        <div className="h-32 bg-bg-surface rounded-3xl" />
      </div>
    );
  }

  if (!me?.enrolled) {
    return <EnrollScreen onEnroll={() => enrollMut.mutate()} pending={enrollMut.isPending} />;
  }

  return <AffiliateDashboard me={me} />;
}

function EnrollScreen({ onEnroll, pending }: { onEnroll: () => void; pending: boolean }) {
  return (
    <div className="p-10 max-w-3xl mx-auto space-y-8">
      <div className="text-center space-y-4">
        <div className="w-16 h-16 mx-auto rounded-3xl bg-accent-amethyst/10 flex items-center justify-center">
          <Handshake className="w-8 h-8 text-accent-amethyst" />
        </div>
        <h1 className="text-4xl font-black tracking-tight">Programa de Afiliados</h1>
        <p className="text-secondary text-base font-medium max-w-xl mx-auto">
          Indique outras tarólogas pra Meu Mistério e ganhe comissão recorrente todo mês.
        </p>
      </div>

      {/* Tier table */}
      <div className="grid grid-cols-3 gap-3">
        <TierCard tier="standard" pct={30} threshold={0} icon={Users} />
        <TierCard tier="silver" pct={40} threshold={10} icon={Award} />
        <TierCard tier="gold" pct={50} threshold={50} icon={Crown} />
      </div>

      <div className="bg-bg-surface border border-border rounded-3xl p-6 space-y-3">
        <h3 className="text-sm font-black flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4 text-emerald-500" />
          Como funciona
        </h3>
        <ul className="space-y-2 text-xs text-secondary">
          <li>• Você ganha um link único: <code className="bg-bg-primary px-1 rounded">meumisterio.com.br/r/SEUCODE</code></li>
          <li>• Indica pra tarólogos no Insta, WhatsApp, indicações</li>
          <li>• Quando alguém assina via seu link → ganha % da mensalidade</li>
          <li>• Pagamento mensal via Pix (você cadastra a chave)</li>
          <li>• Comissão recorrente — enquanto a pessoa estiver assinante</li>
        </ul>
      </div>

      <button
        onClick={onEnroll}
        disabled={pending}
        className="w-full px-6 py-4 bg-accent-amethyst hover:bg-accent-amethyst/90 disabled:opacity-30 text-white rounded-2xl text-sm font-black uppercase tracking-widest"
      >
        {pending ? 'Ativando...' : 'Quero ser afiliado'}
      </button>
    </div>
  );
}

function TierCard({
  tier, pct, threshold, icon: Icon,
}: {
  tier: string;
  pct: number;
  threshold: number;
  icon: typeof Users;
}) {
  return (
    <div className={`p-5 border-2 rounded-3xl ${TIER_COLORS[tier]}`}>
      <Icon className="w-6 h-6 mb-2" />
      <div className="text-[10px] uppercase tracking-widest font-black">{tier}</div>
      <div className="text-3xl font-black mt-1">{pct}%</div>
      <div className="text-[10px] mt-1">
        {threshold === 0 ? 'inicial' : `${threshold}+ ativos`}
      </div>
    </div>
  );
}

function AffiliateDashboard({ me }: { me: NonNullable<Awaited<ReturnType<typeof affiliateApi.me>>> }) {
  const qc = useQueryClient();
  const [pixKey, setPixKey] = useState(me.pix_key || '');
  const [pixKeyType, setPixKeyType] = useState(me.pix_key_type || 'email');
  const [editingPix, setEditingPix] = useState(false);

  const { data: refsData } = useQuery({
    queryKey: ['affiliate-referrals'],
    queryFn: affiliateApi.referrals,
  });
  const { data: payoutsData } = useQuery({
    queryKey: ['affiliate-payouts'],
    queryFn: affiliateApi.payouts,
  });

  const updateMut = useMutation({
    mutationFn: () => affiliateApi.update({ pix_key: pixKey, pix_key_type: pixKeyType }),
    onSuccess: () => {
      toast.success('Chave Pix salva');
      setEditingPix(false);
      qc.invalidateQueries({ queryKey: ['affiliate-me'] });
    },
    onError: handleApiError('Erro ao salvar Pix'),
  });

  const refs = refsData?.items ?? [];
  const payouts = payoutsData?.items ?? [];

  return (
    <div className="p-10 max-w-5xl mx-auto space-y-8">
      <div>
        <div className="flex items-center gap-3 mb-2">
          <div className="w-10 h-10 rounded-2xl bg-accent-amethyst/10 flex items-center justify-center">
            <Handshake className="w-5 h-5 text-accent-amethyst" />
          </div>
          <h1 className="text-3xl font-black tracking-tight">Afiliados</h1>
        </div>
      </div>

      {/* Top stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <Stat label="Indicados" value={String(me.total_referrals || 0)} icon={Users} />
        <Stat label="Ativos" value={String(me.active_referrals || 0)} icon={CheckCircle2} />
        <Stat label="Total ganho" value={`R$${(me.total_earned_brl || 0).toFixed(2)}`} icon={TrendingUp} />
        <Stat label="A receber" value={`R$${(me.pending_brl || 0).toFixed(2)}`} icon={Wallet} />
      </div>

      {/* Tier + ref link */}
      <div className="bg-gradient-to-br from-accent-amethyst/10 to-purple-500/5 border border-accent-amethyst/30 rounded-3xl p-6 space-y-4">
        <div className="flex items-center justify-between gap-3 flex-wrap">
          <div>
            <div className="text-[10px] uppercase font-black tracking-widest text-secondary">
              Seu link de afiliado
            </div>
            <div className="font-mono text-sm mt-1 break-all">
              {me.ref_link}
            </div>
          </div>
          <div className="flex items-center gap-2">
            <span className={`px-3 py-1 rounded-md border text-[10px] font-black uppercase tracking-widest ${TIER_COLORS[me.tier || 'standard']}`}>
              {me.tier} · {me.commission_pct}%
            </span>
            <button
              onClick={() => {
                navigator.clipboard.writeText(me.ref_link || '');
                toast.success('Link copiado');
              }}
              className="px-3 py-1.5 bg-accent-amethyst hover:bg-accent-amethyst/90 text-white rounded-lg text-[10px] font-black uppercase tracking-widest flex items-center gap-1"
            >
              <Copy className="w-3 h-3" />
              Copiar
            </button>
          </div>
        </div>

        {me.tier_progress?.next_tier && me.tier_progress.needed_for_next !== null && (
          <div className="text-[11px] text-secondary">
            Faltam <strong className="text-accent-amethyst">{me.tier_progress.needed_for_next} ativos</strong>{' '}
            pra subir pra <strong className="capitalize">{me.tier_progress.next_tier}</strong>{' '}
            ({me.tier_progress.next_tier === 'silver' ? 40 : 50}% comissão).
          </div>
        )}
      </div>

      {/* Pix key */}
      <div className="bg-bg-surface border border-border rounded-3xl p-6">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-sm font-black flex items-center gap-2">
            <Wallet className="w-4 h-4 text-accent-amethyst" />
            Chave Pix pra receber
          </h3>
          {!editingPix && (
            <button
              onClick={() => setEditingPix(true)}
              className="text-[10px] text-accent-amethyst font-black uppercase tracking-widest"
            >
              Editar
            </button>
          )}
        </div>

        {editingPix ? (
          <div className="space-y-3">
            <div className="flex gap-2">
              <select
                value={pixKeyType}
                onChange={(e) => setPixKeyType(e.target.value)}
                className="bg-bg-primary border border-border rounded-xl px-3 py-2 text-sm"
              >
                <option value="email">Email</option>
                <option value="cpf">CPF</option>
                <option value="phone">Telefone</option>
                <option value="random">Chave aleatória</option>
              </select>
              <input
                type="text"
                value={pixKey}
                onChange={(e) => setPixKey(e.target.value)}
                placeholder="Sua chave Pix"
                className="flex-1 bg-bg-primary border border-border rounded-xl px-3 py-2 text-sm focus:outline-none focus:border-accent-amethyst/30"
              />
            </div>
            <div className="flex gap-2">
              <button
                onClick={() => { setEditingPix(false); setPixKey(me.pix_key || ''); }}
                className="flex-1 px-4 py-2 bg-bg-primary border border-border rounded-xl text-xs font-bold"
              >
                Cancelar
              </button>
              <button
                onClick={() => updateMut.mutate()}
                disabled={updateMut.isPending}
                className="flex-1 px-4 py-2 bg-accent-amethyst hover:bg-accent-amethyst/90 disabled:opacity-30 text-white rounded-xl text-xs font-black uppercase tracking-widest"
              >
                Salvar
              </button>
            </div>
          </div>
        ) : (
          <div className="flex items-center gap-3">
            {me.pix_key ? (
              <>
                <span className="text-[10px] uppercase font-black tracking-widest text-secondary bg-bg-primary px-2 py-1 rounded">
                  {me.pix_key_type}
                </span>
                <span className="font-mono text-sm">{me.pix_key}</span>
              </>
            ) : (
              <span className="text-secondary text-sm">Nenhuma chave cadastrada — cadastre pra receber</span>
            )}
          </div>
        )}
      </div>

      {/* Referrals list */}
      <div>
        <h3 className="text-sm font-black uppercase tracking-widest text-secondary mb-3">
          Indicações ({refs.length})
        </h3>
        {refs.length === 0 ? (
          <div className="bg-bg-surface border border-dashed border-border rounded-2xl p-8 text-center text-secondary text-sm">
            Compartilhe seu link e veja indicações aparecerem aqui.
          </div>
        ) : (
          <div className="space-y-2">
            {refs.map((r) => (
              <div key={r.id} className="bg-bg-surface border border-border rounded-2xl p-4 flex items-center justify-between">
                <div className="min-w-0">
                  <div className="font-bold text-sm truncate">
                    {r.referred_email || `User #${r.id}`}
                  </div>
                  <div className="text-[10px] text-secondary">
                    Cadastro: {r.signed_up_at && new Date(r.signed_up_at).toLocaleDateString('pt-BR')}
                    {r.first_payment_at && (
                      <> · 1ª venda: {new Date(r.first_payment_at).toLocaleDateString('pt-BR')}</>
                    )}
                  </div>
                </div>
                <div className="text-right">
                  <span className={`text-[10px] font-black uppercase tracking-widest px-2 py-0.5 rounded ${
                    r.status === 'paid' ? 'bg-emerald-500/10 text-emerald-500' :
                    r.status === 'trial' ? 'bg-blue-500/10 text-blue-400' :
                    r.status === 'churned' ? 'bg-red-500/10 text-red-400' :
                    'bg-zinc-500/10 text-zinc-400'
                  }`}>
                    {r.status}
                  </span>
                  <div className="text-xs font-mono text-emerald-500 mt-1">
                    R${r.total_commission_brl.toFixed(2)}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Payouts */}
      <div>
        <h3 className="text-sm font-black uppercase tracking-widest text-secondary mb-3">
          Histórico de pagamentos
        </h3>
        {payouts.length === 0 ? (
          <div className="bg-bg-surface border border-dashed border-border rounded-2xl p-6 text-center text-secondary text-xs">
            Sem pagamentos ainda. Os pagamentos saem mensalmente.
          </div>
        ) : (
          <div className="space-y-2">
            {payouts.map((p) => (
              <div key={p.id} className="bg-bg-surface border border-border rounded-2xl p-4 flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <Calendar className="w-4 h-4 text-secondary" />
                  <div>
                    <div className="font-bold text-sm">{fmtPeriod(p.period_yyyymm)}</div>
                    <div className="text-[10px] text-secondary">
                      {p.status === 'paid' && p.paid_at
                        ? `Pago em ${new Date(p.paid_at).toLocaleDateString('pt-BR')}`
                        : p.status}
                    </div>
                  </div>
                </div>
                <div className="text-lg font-black font-mono">
                  R${p.amount_brl.toFixed(2)}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function Stat({
  label, value, icon: Icon,
}: {
  label: string;
  value: string;
  icon: typeof Users;
}) {
  return (
    <div className="bg-bg-surface border border-border rounded-2xl p-4">
      <div className="flex items-center gap-2 mb-2">
        <Icon className="w-3.5 h-3.5 text-accent-amethyst" />
        <span className="text-[9px] font-black uppercase tracking-widest text-secondary">{label}</span>
      </div>
      <div className="text-2xl font-black tracking-tight">{value}</div>
    </div>
  );
}

function fmtPeriod(yyyymm: number): string {
  const y = Math.floor(yyyymm / 100);
  const m = yyyymm % 100;
  const months = ['', 'Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez'];
  return `${months[m] || m}/${y}`;
}
