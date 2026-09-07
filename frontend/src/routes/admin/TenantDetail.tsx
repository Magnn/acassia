import { useState } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  ArrowLeft,
  Mail,
  Calendar,
  Phone,
  ShieldCheck,
  Crown,
  AlertTriangle,
  Plus,
  Pin,
  Trash2,
  Edit3,
  CheckCircle2,
  XCircle,
  Activity,
  BarChart3,
  Eye,
} from 'lucide-react';
import { adminApi, type AdminNote, type AdminTenantOverview } from '../../api/admin';
import { toast } from '../../lib/toast';
import { ApiError } from '../../api/client';

type Tab = 'overview' | 'notes' | 'commercial' | 'audit';

export default function TenantDetail() {
  const { tenantId } = useParams<{ tenantId: string }>();
  const navigate = useNavigate();
  const [tab, setTab] = useState<Tab>('overview');

  const { data: overview, isLoading, error } = useQuery({
    queryKey: ['admin-tenant-overview', tenantId],
    queryFn: () => adminApi.tenantOverview(tenantId!),
    enabled: !!tenantId,
  });

  if (isLoading) {
    return (
      <div className="p-8 space-y-6 animate-pulse">
        <div className="h-8 w-1/3 bg-zinc-900 rounded" />
        <div className="h-32 bg-zinc-900 rounded-2xl" />
        <div className="h-64 bg-zinc-900 rounded-2xl" />
      </div>
    );
  }

  if (error || !overview) {
    const status = error instanceof ApiError ? error.status : null;
    return (
      <div className="p-12 max-w-xl mx-auto text-center space-y-4">
        <XCircle className="w-16 h-16 text-red-500 mx-auto" />
        <h2 className="text-xl font-black">{status === 404 ? 'Tenant não encontrado' : 'Erro ao carregar'}</h2>
        <button
          onClick={() => navigate('/admin/tenants')}
          className="px-5 py-2.5 bg-zinc-800 hover:bg-zinc-700 rounded-2xl text-sm font-bold"
        >
          Voltar
        </button>
      </div>
    );
  }

  const isAdminUser = overview.user.role === 'admin';

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-6">
      {/* Back nav */}
      <Link
        to="/admin/tenants"
        className="inline-flex items-center gap-2 text-xs text-zinc-500 hover:text-white font-bold uppercase tracking-widest"
      >
        <ArrowLeft className="w-3.5 h-3.5" /> Voltar
      </Link>

      {/* Header */}
      <div className="bg-zinc-900/50 border border-zinc-800 rounded-3xl p-8">
        <div className="flex items-start justify-between gap-6">
          <div className="flex items-center gap-5">
            <div className="w-16 h-16 rounded-2xl bg-zinc-800 flex items-center justify-center text-2xl font-black uppercase">
              {(overview.user.name || overview.user.email).substring(0, 2)}
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-2xl font-black">{overview.user.name || overview.user.email}</h1>
                {isAdminUser && <Crown className="w-5 h-5 text-amber-500" />}
                {overview.user.is_verified && <CheckCircle2 className="w-4 h-4 text-emerald-500" />}
                {overview.user.totp_enabled && <ShieldCheck className="w-4 h-4 text-blue-500" />}
              </div>
              <div className="text-sm text-zinc-500 mt-1">{overview.user.email}</div>
              <div className="text-[10px] text-zinc-600 font-mono mt-1">{overview.tenant_id}</div>
            </div>
          </div>

          {/* Quick actions */}
          <ImpersonateButton overview={overview} />
        </div>

        {/* Status badges */}
        <div className="flex flex-wrap gap-2 mt-6">
          <PlanBadge plan={overview.plan.key} label={overview.plan.label} source={overview.plan.source} />
          {overview.lifecycle.is_suspended && (
            <span className="inline-flex items-center gap-1 px-2.5 py-1 bg-amber-950 border border-amber-900 rounded-md text-[10px] font-black uppercase tracking-widest text-amber-300">
              <AlertTriangle className="w-3 h-3" /> Suspenso
            </span>
          )}
          {overview.lifecycle.is_deleted && (
            <span className="inline-flex items-center gap-1 px-2.5 py-1 bg-red-950 border border-red-900 rounded-md text-[10px] font-black uppercase tracking-widest text-red-300">
              <Trash2 className="w-3 h-3" /> Deletado
            </span>
          )}
          {overview.lifecycle.trial_ends_at && new Date(overview.lifecycle.trial_ends_at) > new Date() && (
            <span className="inline-flex items-center gap-1 px-2.5 py-1 bg-blue-950 border border-blue-900 rounded-md text-[10px] font-black uppercase tracking-widest text-blue-300">
              Trial até {new Date(overview.lifecycle.trial_ends_at).toLocaleDateString('pt-BR')}
            </span>
          )}
          {overview.lifecycle.dunning_status && (
            <span className="inline-flex items-center gap-1 px-2.5 py-1 bg-red-950 border border-red-900 rounded-md text-[10px] font-black uppercase tracking-widest text-red-300">
              Dunning: {overview.lifecycle.dunning_status}
            </span>
          )}
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 border-b border-zinc-800 overflow-x-auto">
        {([
          ['overview', 'Visão Geral'],
          ['commercial', 'Comercial'],
          ['notes', `Notas (${overview.notes_count})`],
          ['audit', 'Audit'],
        ] as Array<[Tab, string]>).map(([t, label]) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-5 py-3 text-xs font-black uppercase tracking-widest border-b-2 transition-all whitespace-nowrap ${
              tab === t
                ? 'border-red-500 text-white'
                : 'border-transparent text-zinc-500 hover:text-zinc-300'
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      {/* Tab content */}
      {tab === 'overview' && <OverviewTab overview={overview} />}
      {tab === 'commercial' && <CommercialTab tenantId={tenantId!} overview={overview} />}
      {tab === 'notes' && <NotesTab tenantId={tenantId!} />}
      {tab === 'audit' && <AuditTab tenantId={tenantId!} />}
    </div>
  );
}

function ImpersonateButton({ overview }: { overview: AdminTenantOverview }) {
  const [open, setOpen] = useState(false);
  const [reason, setReason] = useState('');
  const [totp, setTotp] = useState('');
  const [duration, setDuration] = useState(60);

  const isAdminTarget = overview.user.role === 'admin';
  const isBlocked = isAdminTarget || overview.lifecycle.is_suspended || overview.lifecycle.is_deleted;

  const startMut = useMutation({
    mutationFn: () =>
      adminApi.startImpersonate(overview.user.id, reason, totp, duration),
    onSuccess: (data) => {
      toast.success(`Entrando como ${data.target.email}`);
      window.location.href = data.redirect_to;
    },
    onError: (e: unknown) => {
      const body = e instanceof ApiError ? (e.body as { error?: string }) : null;
      const errMsg: Record<string, string> = {
        totp_invalid: 'Código TOTP inválido',
        totp_required: 'Digite o TOTP',
        cannot_impersonate_admin: 'Não pode impersonar outro admin',
        cannot_self_impersonate: 'Não pode impersonar a si mesmo',
        target_suspended: 'Tenant está suspenso',
        target_deleted: 'Tenant está deletado',
        target_inactive: 'Conta inativa',
        reason_too_short: 'Motivo precisa de ao menos 10 caracteres',
        admin_2fa_not_enabled: 'Configure 2FA no admin primeiro',
      };
      toast.error(errMsg[body?.error || ''] || 'Erro ao impersonar');
    },
  });

  if (!open) {
    return (
      <div className="flex gap-2">
        <button
          onClick={() => setOpen(true)}
          disabled={isBlocked}
          title={isBlocked ? (isAdminTarget ? 'Não pode impersonar admin' : 'Tenant indisponível') : undefined}
          className="flex items-center gap-2 px-4 py-2.5 bg-red-900/40 hover:bg-red-800/40 disabled:opacity-30 disabled:cursor-not-allowed rounded-xl text-xs font-black uppercase tracking-widest border border-red-900/40 transition-all text-red-300 hover:text-white"
        >
          <Eye className="w-3.5 h-3.5" />
          Impersonate
        </button>
        <LifecycleActions overview={overview} />
      </div>
    );
  }

  return (
    <div className="fixed inset-0 z-50 bg-black/70 flex items-center justify-center p-6">
      <div className="bg-zinc-900 border border-red-900/40 rounded-3xl p-8 max-w-lg w-full space-y-5">
        <div className="flex items-center gap-3">
          <div className="w-12 h-12 rounded-2xl bg-red-500/10 flex items-center justify-center">
            <Eye className="w-6 h-6 text-red-500" />
          </div>
          <div>
            <h2 className="text-lg font-black">Entrar como {overview.user.email}</h2>
            <p className="text-xs text-zinc-500 font-medium">
              Suas ações ficarão gravadas no audit log
            </p>
          </div>
        </div>

        <div className="space-y-4">
          <div>
            <label className="text-[10px] uppercase font-black tracking-widest text-zinc-500 mb-1.5 block">
              Motivo (mín. 10 chars)
            </label>
            <textarea
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              rows={2}
              placeholder="Ex: ticket #1234 — fluxo não está mandando msg de oferta"
              className="w-full bg-zinc-950 border border-zinc-800 rounded-xl px-3 py-2 text-sm text-white placeholder:text-zinc-600 focus:outline-none focus:border-red-500/50 resize-none"
            />
            <div className="text-[10px] text-zinc-600 mt-1 font-mono">
              {reason.length} chars
            </div>
          </div>

          <div>
            <label className="text-[10px] uppercase font-black tracking-widest text-zinc-500 mb-1.5 block">
              Duração da sessão
            </label>
            <div className="flex gap-2">
              {[15, 60, 240].map((m) => (
                <button
                  key={m}
                  onClick={() => setDuration(m)}
                  className={`flex-1 px-3 py-2 rounded-xl text-xs font-bold transition-all ${
                    duration === m
                      ? 'bg-red-600 text-white'
                      : 'bg-zinc-800 text-zinc-400 hover:bg-zinc-700 hover:text-white'
                  }`}
                >
                  {m === 60 ? '1h' : m === 240 ? '4h' : '15min'}
                </button>
              ))}
            </div>
          </div>

          <div>
            <label className="text-[10px] uppercase font-black tracking-widest text-zinc-500 mb-1.5 block">
              Verificação 2FA
            </label>
            <input
              type="text"
              inputMode="numeric"
              maxLength={6}
              value={totp}
              onChange={(e) => setTotp(e.target.value.replace(/\D/g, ''))}
              placeholder="123456"
              className="w-full text-center text-xl font-mono tracking-[0.4em] bg-zinc-950 border border-zinc-800 rounded-xl py-3 text-white placeholder:text-zinc-700 focus:outline-none focus:border-red-500/50"
            />
          </div>
        </div>

        <div className="bg-amber-950/20 border border-amber-900/40 rounded-xl p-3 flex gap-2">
          <AlertTriangle className="w-4 h-4 text-amber-500 flex-shrink-0 mt-0.5" />
          <p className="text-[11px] text-amber-200/80">
            Você verá a interface como o tenant vê. Mudanças que você fizer
            durante a sessão ficam gravadas em audit log com seu nome.
          </p>
        </div>

        <div className="flex gap-3">
          <button
            onClick={() => { setOpen(false); setReason(''); setTotp(''); }}
            className="flex-1 px-5 py-3 bg-zinc-800 hover:bg-zinc-700 rounded-2xl text-sm font-bold"
          >
            Cancelar
          </button>
          <button
            onClick={() => startMut.mutate()}
            disabled={reason.length < 10 || totp.length !== 6 || startMut.isPending}
            className="flex-1 px-5 py-3 bg-red-600 hover:bg-red-500 disabled:opacity-30 disabled:cursor-not-allowed rounded-2xl text-sm font-black uppercase tracking-widest"
          >
            {startMut.isPending ? 'Entrando...' : `Entrar como ${overview.user.name || 'user'}`}
          </button>
        </div>
      </div>
    </div>
  );
}

type LifecycleAction = 'suspend' | 'reactivate' | 'delete' | 'restore';

function LifecycleActions({ overview }: { overview: AdminTenantOverview }) {
  const qc = useQueryClient();
  const navigate = useNavigate();
  const [action, setAction] = useState<LifecycleAction | null>(null);
  const [reason, setReason] = useState('');
  const [confirmEmail, setConfirmEmail] = useState('');
  const [confirmCheckbox, setConfirmCheckbox] = useState(false);

  const { tenant_id } = overview;
  const isSuspended = overview.lifecycle.is_suspended;
  const isDeleted = overview.lifecycle.is_deleted;
  const isAdminTarget = overview.user.role === 'admin';

  const onSuccess = () => {
    qc.invalidateQueries({ queryKey: ['admin-tenant-overview', tenant_id] });
    qc.invalidateQueries({ queryKey: ['admin-tenants'] });
    setAction(null);
    setReason(''); setConfirmEmail(''); setConfirmCheckbox(false);
  };

  const onError = (e: unknown) => {
    const body = e instanceof ApiError ? (e.body as { error?: string }) : null;
    const msgs: Record<string, string> = {
      reason_too_short: 'Motivo precisa de ao menos 5 caracteres',
      already_suspended: 'Tenant já está suspenso',
      not_suspended: 'Tenant não está suspenso',
      already_deleted: 'Tenant já está deletado',
      not_deleted: 'Tenant não está deletado',
      cannot_suspend_admin: 'Não pode suspender admin protegido',
      cannot_delete_admin: 'Não pode deletar admin protegido',
      confirm_email_mismatch: 'Email digitado não bate com o do tenant',
      tenant_not_found: 'Tenant não encontrado',
    };
    toast.error(msgs[body?.error || ''] || 'Erro');
  };

  const suspendMut = useMutation({
    mutationFn: () => adminApi.suspendTenant(tenant_id, reason),
    onSuccess: () => { toast.success('Tenant suspenso'); onSuccess(); },
    onError,
  });
  const reactivateMut = useMutation({
    mutationFn: () => adminApi.reactivateTenant(tenant_id, reason),
    onSuccess: () => { toast.success('Tenant reativado'); onSuccess(); },
    onError,
  });
  const deleteMut = useMutation({
    mutationFn: () => adminApi.deleteTenant(tenant_id, confirmEmail, reason),
    onSuccess: () => { toast.success('Tenant deletado (recuperável por 30d)'); navigate('/admin/tenants'); },
    onError,
  });
  const restoreMut = useMutation({
    mutationFn: () => adminApi.restoreTenant(tenant_id, reason),
    onSuccess: () => { toast.success('Tenant restaurado'); onSuccess(); },
    onError,
  });

  // Botões de ação dependendo do estado atual
  if (!action) {
    return (
      <>
        {isDeleted ? (
          <button
            onClick={() => setAction('restore')}
            className="flex items-center gap-2 px-4 py-2.5 bg-emerald-900/40 hover:bg-emerald-800/40 rounded-xl text-xs font-black uppercase tracking-widest border border-emerald-900/40 text-emerald-300"
          >
            <CheckCircle2 className="w-3.5 h-3.5" />
            Restaurar
          </button>
        ) : isSuspended ? (
          <>
            <button
              onClick={() => setAction('reactivate')}
              className="flex items-center gap-2 px-4 py-2.5 bg-emerald-900/40 hover:bg-emerald-800/40 rounded-xl text-xs font-black uppercase tracking-widest border border-emerald-900/40 text-emerald-300"
            >
              <CheckCircle2 className="w-3.5 h-3.5" />
              Reativar
            </button>
            {!isAdminTarget && (
              <button
                onClick={() => setAction('delete')}
                className="flex items-center gap-2 px-4 py-2.5 bg-zinc-900 hover:bg-red-900/40 rounded-xl text-xs font-black uppercase tracking-widest text-zinc-400 hover:text-red-400"
              >
                <Trash2 className="w-3.5 h-3.5" />
                Deletar
              </button>
            )}
          </>
        ) : (
          <>
            <button
              onClick={() => setAction('suspend')}
              disabled={isAdminTarget}
              title={isAdminTarget ? 'Não pode suspender admin' : undefined}
              className="flex items-center gap-2 px-4 py-2.5 bg-amber-900/40 hover:bg-amber-800/40 disabled:opacity-30 disabled:cursor-not-allowed rounded-xl text-xs font-black uppercase tracking-widest border border-amber-900/40 text-amber-300"
            >
              <AlertTriangle className="w-3.5 h-3.5" />
              Suspender
            </button>
            {!isAdminTarget && (
              <button
                onClick={() => setAction('delete')}
                className="flex items-center gap-2 px-4 py-2.5 bg-zinc-900 hover:bg-red-900/40 rounded-xl text-xs font-black uppercase tracking-widest text-zinc-400 hover:text-red-400"
              >
                <Trash2 className="w-3.5 h-3.5" />
                Deletar
              </button>
            )}
          </>
        )}
      </>
    );
  }

  // Modal pra cada action
  const config: Record<LifecycleAction, { title: string; desc: string; cta: string; ctaColor: string; onConfirm: () => void; pending: boolean }> = {
    suspend: {
      title: 'Suspender tenant',
      desc: 'O tenant não conseguirá logar. Webhooks WhatsApp irão pra DLQ. Dados preservados.',
      cta: 'Suspender',
      ctaColor: 'bg-amber-600 hover:bg-amber-500',
      onConfirm: () => suspendMut.mutate(),
      pending: suspendMut.isPending,
    },
    reactivate: {
      title: 'Reativar tenant',
      desc: 'Tenant volta a logar normalmente. Mensagens da DLQ no período suspenso são descartadas.',
      cta: 'Reativar',
      ctaColor: 'bg-emerald-600 hover:bg-emerald-500',
      onConfirm: () => reactivateMut.mutate(),
      pending: reactivateMut.isPending,
    },
    delete: {
      title: 'Deletar tenant',
      desc: 'Soft-delete: dados ficam preservados por 30 dias para recuperação. Após esse prazo, hard-delete permanente.',
      cta: 'Deletar',
      ctaColor: 'bg-red-600 hover:bg-red-500',
      onConfirm: () => deleteMut.mutate(),
      pending: deleteMut.isPending,
    },
    restore: {
      title: 'Restaurar tenant',
      desc: 'Desfaz a deleção e reativa a conta. Disponível durante a janela de 30 dias.',
      cta: 'Restaurar',
      ctaColor: 'bg-emerald-600 hover:bg-emerald-500',
      onConfirm: () => restoreMut.mutate(),
      pending: restoreMut.isPending,
    },
  };

  const cfg = config[action];
  const canSubmit =
    reason.length >= 5 &&
    (action !== 'delete' || (confirmEmail.toLowerCase() === overview.user.email.toLowerCase() && confirmCheckbox));

  return (
    <div className="fixed inset-0 z-50 bg-black/70 flex items-center justify-center p-6">
      <div className="bg-zinc-900 border border-zinc-800 rounded-3xl p-8 max-w-lg w-full space-y-5">
        <div className="flex items-center gap-3">
          <div className={`w-12 h-12 rounded-2xl flex items-center justify-center ${
            action === 'delete' ? 'bg-red-500/10' :
            action === 'suspend' ? 'bg-amber-500/10' :
            'bg-emerald-500/10'
          }`}>
            {action === 'delete' ? <Trash2 className="w-6 h-6 text-red-500" /> :
             action === 'suspend' ? <AlertTriangle className="w-6 h-6 text-amber-500" /> :
             <CheckCircle2 className="w-6 h-6 text-emerald-500" />}
          </div>
          <div>
            <h2 className="text-lg font-black">{cfg.title}</h2>
            <p className="text-xs text-zinc-500 font-medium">{overview.user.email}</p>
          </div>
        </div>

        <p className="text-sm text-zinc-400">{cfg.desc}</p>

        <div>
          <label className="text-[10px] uppercase font-black tracking-widest text-zinc-500 mb-1.5 block">
            Motivo (mín. 5 chars)
          </label>
          <textarea
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            rows={2}
            placeholder="Ex: violou TOS, abuso de spam..."
            className="w-full bg-zinc-950 border border-zinc-800 rounded-xl px-3 py-2 text-sm text-white placeholder:text-zinc-600 focus:outline-none focus:border-zinc-600 resize-none"
          />
        </div>

        {action === 'delete' && (
          <>
            <div>
              <label className="text-[10px] uppercase font-black tracking-widest text-zinc-500 mb-1.5 block">
                Digite o email pra confirmar
              </label>
              <input
                type="text"
                value={confirmEmail}
                onChange={(e) => setConfirmEmail(e.target.value)}
                placeholder={overview.user.email}
                className="w-full bg-zinc-950 border border-zinc-800 rounded-xl px-3 py-2 text-sm font-mono text-white placeholder:text-zinc-700 focus:outline-none focus:border-red-500/50"
              />
            </div>
            <label className="flex items-start gap-2 text-xs text-zinc-400 cursor-pointer">
              <input
                type="checkbox"
                checked={confirmCheckbox}
                onChange={(e) => setConfirmCheckbox(e.target.checked)}
                className="mt-0.5"
              />
              <span>
                Entendo que após 30 dias os dados serão removidos permanentemente e
                não poderão ser recuperados.
              </span>
            </label>
          </>
        )}

        <div className="flex gap-3">
          <button
            onClick={() => { setAction(null); setReason(''); setConfirmEmail(''); setConfirmCheckbox(false); }}
            className="flex-1 px-5 py-3 bg-zinc-800 hover:bg-zinc-700 rounded-2xl text-sm font-bold"
          >
            Cancelar
          </button>
          <button
            onClick={cfg.onConfirm}
            disabled={!canSubmit || cfg.pending}
            className={`flex-1 px-5 py-3 ${cfg.ctaColor} disabled:opacity-30 disabled:cursor-not-allowed rounded-2xl text-sm font-black uppercase tracking-widest`}
          >
            {cfg.pending ? 'Processando...' : cfg.cta}
          </button>
        </div>
      </div>
    </div>
  );
}

function PlanBadge({ plan, label, source }: { plan: string; label: string; source: string }) {
  const colors: Record<string, string> = {
    free: 'bg-zinc-800 text-zinc-400 border-zinc-700',
    starter: 'bg-blue-950 text-blue-300 border-blue-900',
    pro: 'bg-purple-950 text-purple-300 border-purple-900',
    enterprise: 'bg-amber-950 text-amber-300 border-amber-900',
  };
  return (
    <span className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-md text-[10px] font-black uppercase tracking-widest border ${colors[plan] || colors.free}`}>
      {label}
      {source !== 'free' && source !== 'stripe' && (
        <span className="opacity-60 ml-1">({source})</span>
      )}
    </span>
  );
}

function OverviewTab({ overview }: { overview: NonNullable<Awaited<ReturnType<typeof adminApi.tenantOverview>>> }) {
  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
      {/* Métricas */}
      <Card title="Métricas (30 dias)" icon={BarChart3}>
        <Stat label="Leads (total)" value={overview.metrics.leads_total} />
        <Stat label="Leads (30d)" value={overview.metrics.leads_30d} />
        <Stat label="Mensagens (total)" value={overview.metrics.msgs_total} />
        <Stat label="Mensagens (30d)" value={overview.metrics.msgs_30d} />
      </Card>

      {/* User info */}
      <Card title="Conta" icon={ShieldCheck}>
        <KV k="Email" v={overview.user.email} icon={Mail} />
        <KV k="Telefone" v={overview.user.phone || '—'} icon={Phone} />
        <KV k="Timezone" v={overview.user.timezone} />
        <KV k="Signup" v={fmtDate(overview.user.signup_at)} icon={Calendar} />
        <KV k="Último login" v={fmtDate(overview.user.last_login_at)} />
        <KV k="2FA" v={overview.user.totp_enabled ? 'Ativo' : 'Inativo'} />
      </Card>

      {/* Plano + limits */}
      <Card title={`Plano: ${overview.plan.label}`} icon={Crown}>
        <KV k="Origem" v={overview.plan.source} />
        <KV k="Preço" v={overview.plan.price_brl > 0 ? `R$${overview.plan.price_brl}/mo` : 'Grátis'} />
        <div className="border-t border-zinc-800 pt-3 mt-3 space-y-2">
          {Object.entries(overview.plan.limits).map(([k, v]) => (
            <div key={k} className="flex justify-between text-[11px]">
              <span className="text-zinc-500">{k}</span>
              <span className="font-mono text-white">{v === -1 ? '∞' : v.toLocaleString('pt-BR')}</span>
            </div>
          ))}
        </div>
      </Card>

      {/* Override ativo */}
      {overview.active_override && (
        <Card title="Override Ativo" icon={AlertTriangle}>
          <KV k="Plano forçado" v={overview.active_override.plan} />
          <KV k="Expira em" v={fmtDate(overview.active_override.expires_at) || 'permanente'} />
          <div className="text-[10px] text-zinc-500 mt-2 italic">
            "{overview.active_override.reason}"
          </div>
        </Card>
      )}

      {/* Grants ativos */}
      {overview.active_grants.length > 0 && (
        <Card title="Cotas Extras" icon={Activity}>
          {overview.active_grants.map((g) => (
            <div key={g.id} className="border-b border-zinc-800 last:border-0 pb-2 mb-2 last:pb-0 last:mb-0">
              <div className="flex justify-between text-xs">
                <span className="text-zinc-400">{g.kind}</span>
                <span className="font-mono text-white">+{g.amount.toLocaleString('pt-BR')}</span>
              </div>
              <div className="flex justify-between text-[10px] text-zinc-500 mt-0.5">
                <span>Usado: {g.used_amount.toLocaleString('pt-BR')}</span>
                <span>{g.expires_at ? fmtDate(g.expires_at) : 'sem expirar'}</span>
              </div>
            </div>
          ))}
        </Card>
      )}

      {/* Health */}
      {overview.health && (
        <Card title="Health Score" icon={Activity}>
          <div className="text-center">
            <div className="text-4xl font-black">{overview.health.score}</div>
            <div className="text-xs uppercase tracking-widest mt-1 font-bold">{overview.health.band}</div>
          </div>
        </Card>
      )}
    </div>
  );
}

function NotesTab({ tenantId }: { tenantId: string }) {
  const qc = useQueryClient();
  const [content, setContent] = useState('');
  const [pinned, setPinned] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editContent, setEditContent] = useState('');

  const { data, isLoading } = useQuery({
    queryKey: ['admin-notes', tenantId],
    queryFn: () => adminApi.listNotes(tenantId),
  });

  const createMut = useMutation({
    mutationFn: () => adminApi.createNote(tenantId, content, pinned),
    onSuccess: () => {
      setContent(''); setPinned(false);
      qc.invalidateQueries({ queryKey: ['admin-notes', tenantId] });
      qc.invalidateQueries({ queryKey: ['admin-tenant-overview', tenantId] });
      toast.success('Nota criada');
    },
  });

  const updateMut = useMutation({
    mutationFn: ({ id, patch }: { id: number; patch: { content?: string; pinned?: boolean } }) =>
      adminApi.updateNote(tenantId, id, patch),
    onSuccess: () => {
      setEditingId(null);
      qc.invalidateQueries({ queryKey: ['admin-notes', tenantId] });
    },
  });

  const deleteMut = useMutation({
    mutationFn: (id: number) => adminApi.deleteNote(tenantId, id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['admin-notes', tenantId] });
      qc.invalidateQueries({ queryKey: ['admin-tenant-overview', tenantId] });
      toast.success('Nota deletada');
    },
  });

  const notes: AdminNote[] = data?.notes ?? [];

  return (
    <div className="space-y-4">
      {/* Composer */}
      <div className="bg-zinc-900/50 border border-zinc-800 rounded-2xl p-5 space-y-3">
        <textarea
          value={content}
          onChange={(e) => setContent(e.target.value)}
          placeholder="Adicionar nota interna sobre o tenant..."
          rows={3}
          className="w-full bg-zinc-950 border border-zinc-800 rounded-xl px-4 py-3 text-sm text-white placeholder:text-zinc-600 focus:outline-none focus:border-red-500/50 resize-none"
        />
        <div className="flex items-center justify-between">
          <label className="flex items-center gap-2 text-xs text-zinc-400 font-bold cursor-pointer">
            <input
              type="checkbox"
              checked={pinned}
              onChange={(e) => setPinned(e.target.checked)}
              className="rounded"
            />
            Pinar no topo
          </label>
          <button
            onClick={() => createMut.mutate()}
            disabled={!content.trim() || createMut.isPending}
            className="flex items-center gap-2 px-5 py-2 bg-red-600 hover:bg-red-500 disabled:opacity-30 rounded-xl text-xs font-black uppercase tracking-widest"
          >
            <Plus className="w-3.5 h-3.5" /> Adicionar
          </button>
        </div>
      </div>

      {/* List */}
      {isLoading ? (
        <div className="text-zinc-500 text-sm text-center py-8">Carregando...</div>
      ) : notes.length === 0 ? (
        <div className="text-zinc-600 text-sm text-center py-12">
          Nenhuma nota ainda. Use pra documentar contexto importante sobre o tenant.
        </div>
      ) : (
        <div className="space-y-2">
          {notes.map((n) => (
            <div
              key={n.id}
              className={`p-4 border rounded-2xl ${
                n.pinned ? 'bg-amber-950/20 border-amber-900/40' : 'bg-zinc-900/50 border-zinc-800'
              }`}
            >
              {editingId === n.id ? (
                <div className="space-y-3">
                  <textarea
                    value={editContent}
                    onChange={(e) => setEditContent(e.target.value)}
                    rows={3}
                    className="w-full bg-zinc-950 border border-zinc-800 rounded-xl px-3 py-2 text-sm text-white"
                  />
                  <div className="flex gap-2">
                    <button
                      onClick={() => updateMut.mutate({ id: n.id, patch: { content: editContent } })}
                      className="px-4 py-1.5 bg-emerald-600 hover:bg-emerald-500 rounded-lg text-xs font-black uppercase tracking-widest"
                    >
                      Salvar
                    </button>
                    <button
                      onClick={() => setEditingId(null)}
                      className="px-4 py-1.5 bg-zinc-800 hover:bg-zinc-700 rounded-lg text-xs font-bold"
                    >
                      Cancelar
                    </button>
                  </div>
                </div>
              ) : (
                <>
                  <div className="flex items-start justify-between gap-3">
                    <p className="text-sm text-white whitespace-pre-wrap flex-1">{n.content}</p>
                    <div className="flex items-center gap-1 opacity-60 hover:opacity-100">
                      {n.pinned && <Pin className="w-3.5 h-3.5 text-amber-500" />}
                      <button
                        onClick={() => updateMut.mutate({ id: n.id, patch: { pinned: !n.pinned } })}
                        className="p-1 hover:bg-zinc-800 rounded text-zinc-500 hover:text-white"
                        title={n.pinned ? 'Despinar' : 'Pinar'}
                      >
                        <Pin className={`w-3.5 h-3.5 ${n.pinned ? 'fill-current' : ''}`} />
                      </button>
                      <button
                        onClick={() => { setEditingId(n.id); setEditContent(n.content); }}
                        className="p-1 hover:bg-zinc-800 rounded text-zinc-500 hover:text-white"
                      >
                        <Edit3 className="w-3.5 h-3.5" />
                      </button>
                      <button
                        onClick={() => {
                          if (confirm('Deletar essa nota?')) deleteMut.mutate(n.id);
                        }}
                        className="p-1 hover:bg-zinc-800 rounded text-zinc-500 hover:text-red-400"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </div>
                  <div className="text-[10px] text-zinc-600 mt-2 font-mono">
                    {fmtDate(n.created_at)}
                    {n.updated_at && ' (editado)'}
                  </div>
                </>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function Card({ title, icon: Icon, children }: { title: string; icon: typeof BarChart3; children: React.ReactNode }) {
  return (
    <div className="bg-zinc-900/50 border border-zinc-800 rounded-2xl p-5">
      <div className="flex items-center gap-2 mb-4">
        <Icon className="w-4 h-4 text-zinc-500" />
        <h3 className="text-[11px] font-black uppercase tracking-widest text-zinc-400">{title}</h3>
      </div>
      <div className="space-y-2">{children}</div>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: number }) {
  return (
    <div className="flex justify-between items-baseline">
      <span className="text-[11px] text-zinc-500">{label}</span>
      <span className="text-base font-black font-mono">{value.toLocaleString('pt-BR')}</span>
    </div>
  );
}

function KV({ k, v, icon: Icon }: { k: string; v: string | null; icon?: typeof Mail }) {
  return (
    <div className="flex items-center justify-between gap-3 text-[11px]">
      <span className="text-zinc-500 flex items-center gap-1.5">
        {Icon && <Icon className="w-3 h-3" />}
        {k}
      </span>
      <span className="text-white truncate max-w-[160px]" title={v || '—'}>
        {v || '—'}
      </span>
    </div>
  );
}

function fmtDate(iso: string | null): string {
  if (!iso) return '—';
  return new Date(iso).toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit', year: '2-digit' });
}

function fmtDateTime(iso: string): string {
  return new Date(iso).toLocaleString('pt-BR', {
    day: '2-digit', month: '2-digit', year: '2-digit',
    hour: '2-digit', minute: '2-digit',
  });
}

// ─── CommercialTab — Plan overrides + Quota grants + Feature flags ────

function CommercialTab({ tenantId, overview }: { tenantId: string; overview: AdminTenantOverview }) {
  const [section, setSection] = useState<'plan' | 'quota' | 'flags'>('plan');

  return (
    <div className="space-y-4">
      <div className="flex gap-1 bg-zinc-900/50 p-1 rounded-xl w-fit">
        {([
          ['plan', 'Plano'],
          ['quota', 'Cotas Extras'],
          ['flags', 'Feature Flags'],
        ] as Array<['plan' | 'quota' | 'flags', string]>).map(([s, label]) => (
          <button
            key={s}
            onClick={() => setSection(s)}
            className={`px-4 py-1.5 rounded-lg text-[11px] font-black uppercase tracking-widest transition-all ${
              section === s
                ? 'bg-zinc-800 text-white'
                : 'text-zinc-500 hover:text-zinc-300'
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      {section === 'plan' && <PlanOverridesSection tenantId={tenantId} overview={overview} />}
      {section === 'quota' && <QuotaGrantsSection tenantId={tenantId} />}
      {section === 'flags' && <FeatureFlagsSection tenantId={tenantId} />}
    </div>
  );
}

function PlanOverridesSection({ tenantId, overview }: { tenantId: string; overview: AdminTenantOverview }) {
  const qc = useQueryClient();
  const [open, setOpen] = useState(false);
  const [plan, setPlan] = useState('pro');
  const [duration, setDuration] = useState<number | null>(90);
  const [reason, setReason] = useState('');

  const { data, isLoading } = useQuery({
    queryKey: ['admin-plan-overrides', tenantId],
    queryFn: () => adminApi.listPlanOverrides(tenantId, true),
  });

  const createMut = useMutation({
    mutationFn: () => adminApi.createPlanOverride(tenantId, {
      plan, duration_days: duration, pauses_stripe: true, reason,
    }),
    onSuccess: (data) => {
      toast.success(`Override aplicado — plano efetivo: ${data.effective_plan_now}`);
      setOpen(false); setReason('');
      qc.invalidateQueries({ queryKey: ['admin-plan-overrides', tenantId] });
      qc.invalidateQueries({ queryKey: ['admin-tenant-overview', tenantId] });
    },
    onError: handleAdminError('Erro ao aplicar override'),
  });

  const revokeMut = useMutation({
    mutationFn: ({ id, reason }: { id: number; reason: string }) =>
      adminApi.revokePlanOverride(tenantId, id, reason),
    onSuccess: () => {
      toast.success('Override revogado');
      qc.invalidateQueries({ queryKey: ['admin-plan-overrides', tenantId] });
      qc.invalidateQueries({ queryKey: ['admin-tenant-overview', tenantId] });
    },
    onError: handleAdminError('Erro ao revogar'),
  });

  const overrides = data?.overrides ?? [];

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm text-zinc-400">
            Plano efetivo: <span className="font-black text-white">{overview.plan.label}</span>
            <span className="text-zinc-600 ml-2">({overview.plan.source})</span>
          </p>
        </div>
        <button
          onClick={() => setOpen(true)}
          className="flex items-center gap-2 px-4 py-2 bg-purple-900/40 hover:bg-purple-800/40 border border-purple-900/40 rounded-xl text-xs font-black uppercase tracking-widest text-purple-300"
        >
          <Plus className="w-3.5 h-3.5" />
          Aplicar override
        </button>
      </div>

      {isLoading ? (
        <div className="text-zinc-500 text-sm text-center py-8">Carregando...</div>
      ) : overrides.length === 0 ? (
        <div className="text-zinc-600 text-sm text-center py-12 border border-dashed border-zinc-800 rounded-2xl">
          Nenhum override aplicado.
        </div>
      ) : (
        <div className="space-y-2">
          {overrides.map((o) => (
            <div
              key={o.id}
              className={`p-4 border rounded-2xl ${
                o.revoked_at ? 'bg-zinc-950 border-zinc-900 opacity-60' : 'bg-purple-950/20 border-purple-900/40'
              }`}
            >
              <div className="flex items-start justify-between gap-3">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="px-2 py-0.5 bg-purple-900/40 rounded text-[10px] font-black uppercase tracking-widest text-purple-300">
                      → {o.plan}
                    </span>
                    {o.revoked_at && (
                      <span className="text-[10px] text-zinc-500">REVOGADO</span>
                    )}
                  </div>
                  <p className="text-sm text-white">{o.reason}</p>
                  <div className="text-[10px] text-zinc-500 mt-2 space-x-3">
                    <span>Iniciado: {fmtDateTime(o.starts_at)}</span>
                    <span>Expira: {o.expires_at ? fmtDateTime(o.expires_at) : 'permanente'}</span>
                    {o.pauses_stripe && <span className="text-amber-500">⏸ Stripe pausado</span>}
                  </div>
                  {o.revoked_at && (
                    <div className="text-[10px] text-zinc-500 mt-1 italic">
                      Revogado em {fmtDateTime(o.revoked_at)} — {o.revoked_reason}
                    </div>
                  )}
                </div>
                {!o.revoked_at && (
                  <button
                    onClick={() => {
                      const r = prompt('Motivo da revogação:');
                      if (r) revokeMut.mutate({ id: o.id, reason: r });
                    }}
                    className="text-[10px] text-zinc-500 hover:text-red-400 font-black uppercase tracking-widest"
                  >
                    Revogar
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {open && (
        <div className="fixed inset-0 z-50 bg-black/70 flex items-center justify-center p-6">
          <div className="bg-zinc-900 border border-purple-900/40 rounded-3xl p-8 max-w-lg w-full space-y-5">
            <h3 className="text-lg font-black">Aplicar override de plano</h3>

            <div>
              <label className="text-[10px] uppercase font-black tracking-widest text-zinc-500 mb-1.5 block">
                Plano forçado
              </label>
              <div className="grid grid-cols-3 gap-2">
                {(['starter', 'pro', 'enterprise'] as const).map((p) => (
                  <button
                    key={p}
                    onClick={() => setPlan(p)}
                    className={`px-3 py-2 rounded-xl text-xs font-bold transition-all ${
                      plan === p
                        ? 'bg-purple-600 text-white'
                        : 'bg-zinc-800 text-zinc-400 hover:bg-zinc-700'
                    }`}
                  >
                    {p}
                  </button>
                ))}
              </div>
            </div>

            <div>
              <label className="text-[10px] uppercase font-black tracking-widest text-zinc-500 mb-1.5 block">
                Duração
              </label>
              <div className="flex gap-2 flex-wrap">
                {[
                  { v: 30, l: '30d' },
                  { v: 90, l: '90d' },
                  { v: 365, l: '1 ano' },
                  { v: null, l: 'Permanente' },
                ].map(({ v, l }) => (
                  <button
                    key={l}
                    onClick={() => setDuration(v)}
                    className={`px-3 py-2 rounded-xl text-xs font-bold transition-all ${
                      duration === v
                        ? 'bg-purple-600 text-white'
                        : 'bg-zinc-800 text-zinc-400 hover:bg-zinc-700'
                    }`}
                  >
                    {l}
                  </button>
                ))}
              </div>
            </div>

            <div>
              <label className="text-[10px] uppercase font-black tracking-widest text-zinc-500 mb-1.5 block">
                Motivo (mín 5 chars)
              </label>
              <textarea
                value={reason}
                onChange={(e) => setReason(e.target.value)}
                rows={2}
                placeholder="Ex: deal afiliado top — comp 90 dias"
                className="w-full bg-zinc-950 border border-zinc-800 rounded-xl px-3 py-2 text-sm text-white placeholder:text-zinc-600 focus:outline-none focus:border-purple-500/50 resize-none"
              />
            </div>

            <div className="flex gap-3">
              <button
                onClick={() => setOpen(false)}
                className="flex-1 px-5 py-3 bg-zinc-800 hover:bg-zinc-700 rounded-2xl text-sm font-bold"
              >
                Cancelar
              </button>
              <button
                onClick={() => createMut.mutate()}
                disabled={reason.length < 5 || createMut.isPending}
                className="flex-1 px-5 py-3 bg-purple-600 hover:bg-purple-500 disabled:opacity-30 rounded-2xl text-sm font-black uppercase tracking-widest"
              >
                {createMut.isPending ? 'Aplicando...' : 'Aplicar override'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

const QUOTA_KIND_LABELS: Record<string, string> = {
  gemini_tokens_month: 'Tokens Gemini/mês',
  wa_msgs_month: 'Mensagens WhatsApp/mês',
  leads_month: 'Leads/mês',
};

function QuotaGrantsSection({ tenantId }: { tenantId: string }) {
  const qc = useQueryClient();
  const [open, setOpen] = useState(false);
  const [kind, setKind] = useState('gemini_tokens_month');
  const [amount, setAmount] = useState('10000');
  const [duration, setDuration] = useState<number | null>(30);
  const [reason, setReason] = useState('');

  const { data, isLoading } = useQuery({
    queryKey: ['admin-quota-grants', tenantId],
    queryFn: () => adminApi.listQuotaGrants(tenantId, true),
  });

  const createMut = useMutation({
    mutationFn: () => adminApi.createQuotaGrant(tenantId, {
      kind, amount: parseInt(amount, 10), duration_days: duration, reason,
    }),
    onSuccess: (data) => {
      toast.success(`Cota concedida — total: ${data.new_effective_quota.toLocaleString('pt-BR')}`);
      setOpen(false); setReason(''); setAmount('10000');
      qc.invalidateQueries({ queryKey: ['admin-quota-grants', tenantId] });
      qc.invalidateQueries({ queryKey: ['admin-tenant-overview', tenantId] });
    },
    onError: handleAdminError('Erro ao conceder cota'),
  });

  const revokeMut = useMutation({
    mutationFn: ({ id, reason }: { id: number; reason: string }) =>
      adminApi.revokeQuotaGrant(tenantId, id, reason),
    onSuccess: () => {
      toast.success('Grant revogado');
      qc.invalidateQueries({ queryKey: ['admin-quota-grants', tenantId] });
      qc.invalidateQueries({ queryKey: ['admin-tenant-overview', tenantId] });
    },
    onError: handleAdminError('Erro ao revogar'),
  });

  const grants = data?.grants ?? [];
  const isExpired = (g: { expires_at: string | null }) =>
    g.expires_at !== null && new Date(g.expires_at) < new Date();

  return (
    <div className="space-y-4">
      <div className="flex justify-end">
        <button
          onClick={() => setOpen(true)}
          className="flex items-center gap-2 px-4 py-2 bg-emerald-900/40 hover:bg-emerald-800/40 border border-emerald-900/40 rounded-xl text-xs font-black uppercase tracking-widest text-emerald-300"
        >
          <Plus className="w-3.5 h-3.5" />
          Conceder cota extra
        </button>
      </div>

      {isLoading ? (
        <div className="text-zinc-500 text-sm text-center py-8">Carregando...</div>
      ) : grants.length === 0 ? (
        <div className="text-zinc-600 text-sm text-center py-12 border border-dashed border-zinc-800 rounded-2xl">
          Nenhuma cota extra concedida.
        </div>
      ) : (
        <div className="space-y-2">
          {grants.map((g) => {
            const expired = isExpired(g);
            const used_pct = g.amount > 0 ? (g.used_amount / g.amount) * 100 : 0;
            return (
              <div
                key={g.id}
                className={`p-4 border rounded-2xl ${
                  expired ? 'bg-zinc-950 border-zinc-900 opacity-60' : 'bg-emerald-950/20 border-emerald-900/40'
                }`}
              >
                <div className="flex items-start justify-between gap-3 mb-2">
                  <div>
                    <div className="text-xs font-black uppercase tracking-widest text-zinc-400">
                      {QUOTA_KIND_LABELS[g.kind] || g.kind}
                    </div>
                    <div className="text-2xl font-black font-mono mt-1">
                      +{g.amount.toLocaleString('pt-BR')}
                    </div>
                  </div>
                  {!expired && (
                    <button
                      onClick={() => {
                        const r = prompt('Motivo da revogação:');
                        if (r) revokeMut.mutate({ id: g.id, reason: r });
                      }}
                      className="text-[10px] text-zinc-500 hover:text-red-400 font-black uppercase tracking-widest"
                    >
                      Revogar
                    </button>
                  )}
                </div>
                {/* Progress used */}
                <div className="space-y-1">
                  <div className="flex justify-between text-[10px] text-zinc-500">
                    <span>Usado: {g.used_amount.toLocaleString('pt-BR')}</span>
                    <span>{used_pct.toFixed(0)}%</span>
                  </div>
                  <div className="h-1.5 bg-zinc-800 rounded-full overflow-hidden">
                    <div className="h-full bg-emerald-500" style={{ width: `${Math.min(100, used_pct)}%` }} />
                  </div>
                </div>
                <div className="text-[10px] text-zinc-500 mt-2 space-x-3">
                  <span>Concedido: {fmtDateTime(g.created_at)}</span>
                  <span>{g.expires_at ? `Expira: ${fmtDateTime(g.expires_at)}` : 'Sem expiração'}</span>
                  {expired && <span className="text-red-500">EXPIRADO</span>}
                </div>
                <p className="text-[11px] text-zinc-400 mt-2 italic">"{g.reason}"</p>
              </div>
            );
          })}
        </div>
      )}

      {open && (
        <div className="fixed inset-0 z-50 bg-black/70 flex items-center justify-center p-6">
          <div className="bg-zinc-900 border border-emerald-900/40 rounded-3xl p-8 max-w-lg w-full space-y-5">
            <h3 className="text-lg font-black">Conceder cota extra</h3>

            <div>
              <label className="text-[10px] uppercase font-black tracking-widest text-zinc-500 mb-1.5 block">
                Tipo de cota
              </label>
              <select
                value={kind}
                onChange={(e) => setKind(e.target.value)}
                className="w-full bg-zinc-950 border border-zinc-800 rounded-xl px-3 py-2.5 text-sm text-white focus:outline-none focus:border-emerald-500/50"
              >
                {Object.entries(QUOTA_KIND_LABELS).map(([k, l]) => (
                  <option key={k} value={k}>{l}</option>
                ))}
              </select>
            </div>

            <div>
              <label className="text-[10px] uppercase font-black tracking-widest text-zinc-500 mb-1.5 block">
                Quantidade
              </label>
              <input
                type="number"
                value={amount}
                onChange={(e) => setAmount(e.target.value)}
                min={1}
                max={100_000_000}
                className="w-full bg-zinc-950 border border-zinc-800 rounded-xl px-3 py-2.5 text-sm font-mono text-white focus:outline-none focus:border-emerald-500/50"
              />
            </div>

            <div>
              <label className="text-[10px] uppercase font-black tracking-widest text-zinc-500 mb-1.5 block">
                Validade
              </label>
              <div className="flex gap-2 flex-wrap">
                {[
                  { v: 30, l: '30d' }, { v: 90, l: '90d' }, { v: 365, l: '1 ano' },
                  { v: null, l: 'Sem expirar' },
                ].map(({ v, l }) => (
                  <button
                    key={l}
                    onClick={() => setDuration(v)}
                    className={`px-3 py-2 rounded-xl text-xs font-bold transition-all ${
                      duration === v
                        ? 'bg-emerald-600 text-white'
                        : 'bg-zinc-800 text-zinc-400 hover:bg-zinc-700'
                    }`}
                  >
                    {l}
                  </button>
                ))}
              </div>
            </div>

            <div>
              <label className="text-[10px] uppercase font-black tracking-widest text-zinc-500 mb-1.5 block">
                Motivo
              </label>
              <textarea
                value={reason}
                onChange={(e) => setReason(e.target.value)}
                rows={2}
                placeholder="Ex: pico TikTok viral mês 04/2026"
                className="w-full bg-zinc-950 border border-zinc-800 rounded-xl px-3 py-2 text-sm text-white placeholder:text-zinc-600 focus:outline-none focus:border-emerald-500/50 resize-none"
              />
            </div>

            <div className="flex gap-3">
              <button
                onClick={() => setOpen(false)}
                className="flex-1 px-5 py-3 bg-zinc-800 hover:bg-zinc-700 rounded-2xl text-sm font-bold"
              >
                Cancelar
              </button>
              <button
                onClick={() => createMut.mutate()}
                disabled={reason.length < 5 || !amount || parseInt(amount, 10) < 1 || createMut.isPending}
                className="flex-1 px-5 py-3 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-30 rounded-2xl text-sm font-black uppercase tracking-widest"
              >
                {createMut.isPending ? 'Concedendo...' : 'Conceder'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function FeatureFlagsSection({ tenantId }: { tenantId: string }) {
  const qc = useQueryClient();

  const { data, isLoading } = useQuery({
    queryKey: ['admin-tenant-flags', tenantId],
    queryFn: () => adminApi.listTenantFlags(tenantId),
  });

  const setMut = useMutation({
    mutationFn: ({ key, enabled }: { key: string; enabled: boolean }) =>
      adminApi.setTenantFlag(tenantId, key, enabled),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['admin-tenant-flags', tenantId] }),
    onError: handleAdminError('Erro ao alterar flag'),
  });

  const removeMut = useMutation({
    mutationFn: (key: string) => adminApi.removeTenantFlag(tenantId, key),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['admin-tenant-flags', tenantId] }),
    onError: handleAdminError('Erro ao remover override'),
  });

  const flags = data?.flags ?? [];

  return (
    <div className="space-y-3">
      {isLoading ? (
        <div className="text-zinc-500 text-sm text-center py-8">Carregando...</div>
      ) : flags.length === 0 ? (
        <div className="text-zinc-600 text-sm text-center py-12 border border-dashed border-zinc-800 rounded-2xl">
          Nenhuma feature flag global definida.
          <br />
          <span className="text-[10px] text-zinc-700 mt-2 block">
            Crie em /admin/feature-flags (em breve)
          </span>
        </div>
      ) : (
        flags.map((f) => (
          <div
            key={f.key}
            className="p-4 bg-zinc-900/50 border border-zinc-800 rounded-2xl flex items-center justify-between gap-3"
          >
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 mb-0.5">
                <span className="font-mono text-sm font-bold">{f.key}</span>
                <span className={`px-1.5 py-0.5 rounded text-[9px] font-black uppercase tracking-widest ${
                  f.source === 'tenant_override' ? 'bg-purple-900/40 text-purple-300' :
                  f.source === 'rollout' ? 'bg-blue-900/40 text-blue-300' :
                  'bg-zinc-800 text-zinc-500'
                }`}>
                  {f.source}
                </span>
              </div>
              {f.description && (
                <p className="text-[11px] text-zinc-500">{f.description}</p>
              )}
              <div className="text-[10px] text-zinc-600 mt-0.5">
                Default: {f.default_value ? 'on' : 'off'} · Rollout: {f.rollout_pct}%
              </div>
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setMut.mutate({ key: f.key, enabled: !f.value })}
                className={`px-3 py-1.5 rounded-lg text-xs font-black uppercase tracking-widest transition-all ${
                  f.value
                    ? 'bg-emerald-600 hover:bg-emerald-500 text-white'
                    : 'bg-zinc-800 hover:bg-zinc-700 text-zinc-400'
                }`}
              >
                {f.value ? 'ON' : 'off'}
              </button>
              {f.tenant_override && (
                <button
                  onClick={() => removeMut.mutate(f.key)}
                  className="text-[10px] text-zinc-500 hover:text-red-400 font-black uppercase tracking-widest"
                  title="Remove override (volta pro default)"
                >
                  ×
                </button>
              )}
            </div>
          </div>
        ))
      )}
    </div>
  );
}

// ─── AuditTab ────────────────────────────────────────────────────────

function AuditTab({ tenantId }: { tenantId: string }) {
  const [filter, setFilter] = useState('');
  const [cursor, setCursor] = useState(0);

  const { data, isLoading } = useQuery({
    queryKey: ['admin-audit', tenantId, filter, cursor],
    queryFn: () => adminApi.listTenantAudit(tenantId, {
      event_type: filter || undefined,
      cursor, limit: 50,
    }),
  });

  const events = data?.events ?? [];

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2">
        <input
          type="text"
          value={filter}
          onChange={(e) => { setFilter(e.target.value); setCursor(0); }}
          placeholder="Filtrar por event_type (use * pra prefix)"
          className="flex-1 bg-zinc-950 border border-zinc-800 rounded-xl px-3 py-2 text-xs font-mono text-white placeholder:text-zinc-600 focus:outline-none focus:border-zinc-600"
        />
        <span className="text-xs text-zinc-500">
          {data?.total ?? 0} eventos
        </span>
      </div>

      {isLoading ? (
        <div className="text-zinc-500 text-sm text-center py-8">Carregando...</div>
      ) : events.length === 0 ? (
        <div className="text-zinc-600 text-sm text-center py-12 border border-dashed border-zinc-800 rounded-2xl">
          Nenhum evento de audit ainda.
        </div>
      ) : (
        <div className="bg-zinc-900/50 border border-zinc-800 rounded-2xl overflow-hidden">
          <table className="w-full text-xs">
            <thead className="bg-zinc-950/60">
              <tr className="text-left text-[10px] font-black uppercase tracking-widest text-zinc-500">
                <th className="px-3 py-2">Quando</th>
                <th className="px-3 py-2">Tipo</th>
                <th className="px-3 py-2">Actor</th>
                <th className="px-3 py-2">Target</th>
                <th className="px-3 py-2">Detalhe</th>
              </tr>
            </thead>
            <tbody>
              {events.map((e) => (
                <tr key={e.id} className="border-t border-zinc-900 hover:bg-zinc-900/40">
                  <td className="px-3 py-2 text-zinc-400 font-mono text-[11px] whitespace-nowrap">
                    {fmtDateTime(e.timestamp)}
                  </td>
                  <td className="px-3 py-2 font-mono text-[11px] text-white">
                    {e.event_type}
                  </td>
                  <td className="px-3 py-2 text-zinc-400">
                    {e.actor_user_id ? `#${e.actor_user_id}` : '—'}
                    {e.impersonator_user_id && (
                      <span className="ml-1 px-1 py-0.5 bg-red-900/40 rounded text-[9px] text-red-300">
                        via #{e.impersonator_user_id}
                      </span>
                    )}
                  </td>
                  <td className="px-3 py-2 text-zinc-500 font-mono text-[10px] truncate max-w-[140px]">
                    {e.target_type ? `${e.target_type}/${e.target_id || '—'}` : '—'}
                  </td>
                  <td className="px-3 py-2 text-[10px] text-zinc-500 max-w-[280px] truncate">
                    {e.payload && Object.keys(e.payload).length > 0
                      ? JSON.stringify(e.payload)
                      : '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {data && data.cursor_next !== null && (
            <div className="border-t border-zinc-800 px-3 py-2 flex justify-end">
              <button
                onClick={() => setCursor(data.cursor_next!)}
                className="text-xs text-zinc-500 hover:text-white font-black uppercase tracking-widest"
              >
                Próxima página →
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ─── Helper unificado de error handler ────────────────────────────────

function handleAdminError(fallback: string) {
  return (e: unknown) => {
    const body = e instanceof ApiError ? (e.body as { error?: string }) : null;
    const known: Record<string, string> = {
      reason_too_short: 'Motivo precisa de pelo menos 5 caracteres',
      plan_invalid: 'Plano inválido',
      kind_invalid: 'Tipo de cota inválido',
      amount_invalid: 'Quantidade inválida (1 a 100M)',
      duration_invalid: 'Duração inválida',
      override_not_found: 'Override não encontrado',
      already_revoked: 'Já estava revogado',
      grant_not_found: 'Grant não encontrado',
      flag_not_found: 'Flag não encontrada — crie em /admin/feature-flags primeiro',
      key_invalid: 'Chave inválida (use snake_case)',
      tenant_not_found: 'Tenant não encontrado',
      tenant_deleted: 'Tenant deletado',
    };
    toast.error(known[body?.error || ''] || fallback);
  };
}
