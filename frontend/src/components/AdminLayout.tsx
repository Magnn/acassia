import { useEffect, useState } from 'react';
import { NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom';
import {
  ShieldCheck,
  Users,
  CreditCard,
  Activity,
  Flag,
  Megaphone,
  AlertTriangle,
  TrendingUp,
  ScrollText,
  LogOut,
  Lock,
  AlertOctagon,
} from 'lucide-react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { adminApi } from '../api/admin';
import { authApi } from '../api/auth';
import { ApiError } from '../api/client';
import { toast } from '../lib/toast';

interface NavItem {
  to: string;
  icon: typeof Users;
  label: string;
  group?: string;
}

const NAV_ITEMS: NavItem[] = [
  { to: '/admin/tenants', icon: Users, label: 'Tenants', group: 'core' },
  { to: '/admin/billing', icon: CreditCard, label: 'Faturamento', group: 'core' },
  { to: '/admin/metrics', icon: TrendingUp, label: 'Métricas', group: 'core' },
  { to: '/admin/audit', icon: ScrollText, label: 'Audit log', group: 'core' },
  { to: '/admin/activity', icon: Activity, label: 'Atividade', group: 'monitoring' },
  { to: '/admin/at-risk', icon: AlertTriangle, label: 'At-risk', group: 'monitoring' },
  { to: '/admin/fraud', icon: AlertOctagon, label: 'Fraude', group: 'monitoring' },
  { to: '/admin/feature-flags', icon: Flag, label: 'Feature flags', group: 'system' },
  { to: '/admin/broadcasts', icon: Megaphone, label: 'Broadcasts', group: 'system' },
];

const GROUP_LABELS: Record<string, string> = {
  core: 'Operação',
  monitoring: 'Monitoramento',
  system: 'Sistema',
};

export default function AdminLayout() {
  const location = useLocation();
  const navigate = useNavigate();
  const [showChallenge, setShowChallenge] = useState(false);
  const [totpCode, setTotpCode] = useState('');

  const { data: user, error: userError } = useQuery({
    queryKey: ['me'],
    queryFn: authApi.me,
    staleTime: Infinity,
    retry: false,
  });

  const { data: twoFAStatus, refetch: refetchTwoFA } = useQuery({
    queryKey: ['admin-2fa-status'],
    queryFn: adminApi.twoFAStatus,
    retry: false,
  });

  // Probe inicial: tenta um endpoint admin pra ver se já tem cookie 2FA válido
  const { error: probeError } = useQuery({
    queryKey: ['admin-probe'],
    queryFn: () => adminApi.listTenants({ limit: 1 }),
    retry: false,
    staleTime: 30 * 1000,
  });

  const challengeMutation = useMutation({
    mutationFn: (totp: string) => adminApi.twoFAChallenge(totp),
    onSuccess: () => {
      setShowChallenge(false);
      setTotpCode('');
      toast.success('Acesso admin liberado por 15min');
      refetchTwoFA();
      window.location.reload();
    },
    onError: (e: unknown) => {
      const msg = e instanceof ApiError ? (e.body as { error?: string })?.error || 'Código inválido' : 'Erro';
      toast.error(msg);
    },
  });

  const logoutAdminMutation = useMutation({
    mutationFn: adminApi.twoFALogout,
    onSuccess: () => {
      toast.success('Saiu do modo admin');
      navigate('/dashboard');
    },
  });

  useEffect(() => {
    if (userError) {
      window.location.href = '/saas/login?next=' + encodeURIComponent(location.pathname);
    }
  }, [userError, location.pathname]);

  // Detecta probe falhou com 403 → precisa challenge 2FA
  useEffect(() => {
    if (probeError instanceof ApiError) {
      const body = probeError.body as { error?: string; reason?: string } | null;
      if (probeError.status === 403 && body?.reason === '2fa_required') {
        if (twoFAStatus?.enabled) {
          setShowChallenge(true);
        } else {
          // Não tem 2FA setup: mostra mensagem direta
          toast.error('Configure 2FA antes de acessar admin');
          navigate('/admin/setup-2fa');
        }
      } else if (probeError.status === 403) {
        toast.error('Acesso admin negado: ' + (body?.reason || 'forbidden'));
        navigate('/dashboard');
      }
    }
  }, [probeError, twoFAStatus, navigate]);

  if (!user) {
    return (
      <div className="min-h-screen bg-[#0d0d0d] flex items-center justify-center">
        <div className="w-12 h-12 border-4 border-red-500/20 border-t-red-500 rounded-full animate-spin" />
      </div>
    );
  }

  // Bloqueio se não-admin
  if (user.role !== 'admin') {
    return (
      <div className="min-h-screen bg-[#0d0d0d] text-white flex items-center justify-center p-8">
        <div className="max-w-md text-center space-y-6">
          <div className="w-20 h-20 mx-auto rounded-3xl bg-red-500/10 border border-red-500/20 flex items-center justify-center">
            <Lock className="w-10 h-10 text-red-500" />
          </div>
          <h1 className="text-2xl font-black">Acesso Restrito</h1>
          <p className="text-zinc-400 text-sm">
            Esta área é exclusiva pra administradores da plataforma Acássia.
          </p>
          <button
            onClick={() => navigate('/dashboard')}
            className="px-6 py-3 bg-zinc-800 hover:bg-zinc-700 rounded-2xl text-sm font-bold transition-all"
          >
            Voltar pro Dashboard
          </button>
        </div>
      </div>
    );
  }

  // Modal challenge 2FA
  if (showChallenge) {
    return (
      <div className="min-h-screen bg-[#0d0d0d] flex items-center justify-center p-8">
        <div className="max-w-md w-full bg-zinc-900 border border-red-900/40 rounded-[32px] p-10 space-y-6 shadow-2xl">
          <div className="w-16 h-16 mx-auto rounded-2xl bg-red-500/10 flex items-center justify-center">
            <ShieldCheck className="w-8 h-8 text-red-500" />
          </div>
          <div className="text-center">
            <h2 className="text-xl font-black text-white">Verificação 2FA</h2>
            <p className="text-zinc-400 text-sm mt-2">
              Entre o código TOTP do seu autenticador pra acessar /admin
            </p>
          </div>
          <input
            type="text"
            inputMode="numeric"
            pattern="[0-9]*"
            maxLength={6}
            value={totpCode}
            onChange={(e) => setTotpCode(e.target.value.replace(/\D/g, ''))}
            placeholder="123456"
            autoFocus
            className="w-full text-center text-2xl font-mono tracking-[0.4em] bg-zinc-950 border border-zinc-800 rounded-2xl py-5 text-white placeholder:text-zinc-700 focus:border-red-500/50 focus:outline-none"
          />
          <div className="flex gap-3">
            <button
              onClick={() => navigate('/dashboard')}
              className="flex-1 px-5 py-3 bg-zinc-800 hover:bg-zinc-700 rounded-2xl text-sm font-bold transition-all text-white"
            >
              Cancelar
            </button>
            <button
              onClick={() => challengeMutation.mutate(totpCode)}
              disabled={totpCode.length !== 6 || challengeMutation.isPending}
              className="flex-1 px-5 py-3 bg-red-600 hover:bg-red-500 disabled:opacity-30 disabled:cursor-not-allowed rounded-2xl text-sm font-black transition-all text-white"
            >
              {challengeMutation.isPending ? 'Validando...' : 'Verificar'}
            </button>
          </div>
          <button
            onClick={() => navigate('/admin/recover')}
            className="w-full text-xs text-zinc-500 hover:text-zinc-300 underline"
          >
            Perdi acesso ao meu autenticador
          </button>
        </div>
      </div>
    );
  }

  const groups: { id: string; items: NavItem[] }[] = [];
  for (const item of NAV_ITEMS) {
    const gid = item.group ?? '_';
    let g = groups.find((x) => x.id === gid);
    if (!g) {
      g = { id: gid, items: [] };
      groups.push(g);
    }
    g.items.push(item);
  }

  return (
    <div className="flex h-screen w-full bg-[#0d0d0d] text-white overflow-hidden font-sans">
      {/* Sidebar */}
      <aside className="w-[260px] flex-shrink-0 bg-[#0a0a0a] border-r border-zinc-900 flex flex-col">
        {/* Brand */}
        <div className="flex items-center gap-3 h-[64px] px-5 border-b border-zinc-900">
          <div className="w-9 h-9 rounded-xl bg-red-600 flex items-center justify-center">
            <ShieldCheck className="w-5 h-5 text-white" strokeWidth={2.5} />
          </div>
          <div className="flex flex-col leading-none">
            <span className="text-sm font-black tracking-tight">ACÁSSIA</span>
            <span className="text-[9px] text-red-500 font-black tracking-[0.2em] uppercase mt-0.5">
              Admin Console
            </span>
          </div>
        </div>

        {/* Nav */}
        <nav className="flex-1 py-5 px-3 overflow-y-auto space-y-6">
          {groups.map((g) => (
            <div key={g.id}>
              <div className="text-[9px] font-black tracking-[0.2em] text-zinc-600 uppercase px-3 mb-2">
                {GROUP_LABELS[g.id] ?? ''}
              </div>
              <ul className="space-y-0.5">
                {g.items.map((item) => (
                  <li key={item.to}>
                    <NavLink
                      to={item.to}
                      className={({ isActive }) =>
                        [
                          'group flex items-center gap-3 px-3 py-2.5 rounded-xl',
                          'text-xs font-bold transition-all',
                          isActive
                            ? 'bg-red-600/20 text-red-400 border border-red-900/40'
                            : 'text-zinc-400 hover:bg-zinc-900/60 hover:text-white border border-transparent',
                        ].join(' ')
                      }
                    >
                      <item.icon className="w-4 h-4 flex-shrink-0" strokeWidth={2} />
                      <span className="truncate">{item.label}</span>
                    </NavLink>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </nav>

        {/* Footer */}
        <div className="border-t border-zinc-900 p-3 space-y-2">
          <div className="px-3 py-2 bg-zinc-950 rounded-xl border border-zinc-900">
            <div className="text-[9px] text-zinc-600 uppercase tracking-widest mb-1">Logado como</div>
            <div className="text-xs font-black text-white truncate">{user.email}</div>
            <div className="text-[10px] text-red-500 font-bold mt-0.5">{user.role}</div>
          </div>
          <button
            onClick={() => logoutAdminMutation.mutate()}
            className="w-full flex items-center justify-center gap-2 px-3 py-2 bg-zinc-900 hover:bg-zinc-800 rounded-xl text-[11px] font-black uppercase tracking-widest transition-all text-zinc-400 hover:text-white"
          >
            <LogOut className="w-3.5 h-3.5" />
            Sair do admin
          </button>
        </div>
      </aside>

      {/* Main */}
      <main className="flex-1 flex flex-col min-w-0 h-full overflow-hidden">
        {/* Header alerta tema admin */}
        <header className="h-[48px] bg-red-950/30 border-b border-red-900/40 px-6 flex items-center justify-between flex-shrink-0">
          <div className="flex items-center gap-3 text-xs font-black text-red-300 uppercase tracking-widest">
            <AlertTriangle className="w-4 h-4" />
            Modo Administrativo
          </div>
          <div className="text-[10px] text-zinc-500 font-mono">
            {user.email} · 2FA ativo
          </div>
        </header>
        <div className="flex-1 overflow-auto bg-[#0d0d0d]">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
