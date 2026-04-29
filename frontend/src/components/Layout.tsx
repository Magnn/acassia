import { useState } from 'react';
import { NavLink, Outlet, useLocation } from 'react-router-dom';
import {
  Activity,
  ArrowLeftRight,
  Bot,
  FolderTree,
  KeyRound,
  LayoutDashboard,
  MessageSquare,
  PanelLeftClose,
  PanelLeftOpen,
  Plug,
  Power,
  Settings as SettingsIcon,
  CreditCard,
  ShieldCheck,
  Store,
  Sparkles,
  Compass,
  CalendarDays,
} from 'lucide-react';
import Logo, { Wordmark } from './Logo';
import { useTheme } from '../context/ThemeContext';
import { useQuery } from '@tanstack/react-query';
import { authApi } from '../api/auth';

interface NavItem {
  to: string;
  icon: typeof LayoutDashboard;
  label: string;
  group?: string;
  roles?: ('admin' | 'user')[];
}

const NAV_ITEMS: NavItem[] = [
  { to: '/dashboard', icon: LayoutDashboard, label: 'Visão geral', group: 'painel', roles: ['admin', 'user'] },
  { to: '/leads', icon: MessageSquare, label: 'Contatos & Conversas', group: 'CRM', roles: ['admin', 'user'] },
  { to: '/billing', icon: CreditCard, label: 'Assinatura', group: 'conta', roles: ['admin', 'user'] },
  { to: '/blueprints', icon: FolderTree, label: 'Fluxos', group: 'oraculo', roles: ['admin'] },
  { to: '/templates', icon: FolderTree, label: 'Templates', group: 'oraculo', roles: ['admin', 'user'] },
  { to: '/marketplace', icon: Store, label: 'Marketplace', group: 'oraculo', roles: ['admin', 'user'] },
  { to: '/tarot', icon: FolderTree, label: 'Tarot Virtual', group: 'oraculo', roles: ['admin', 'user'] },
  { to: '/pix', icon: CreditCard, label: 'Pix QR', group: 'oraculo', roles: ['admin', 'user'] },
  { to: '/voice', icon: Bot, label: 'Voice IA', group: 'oraculo', roles: ['admin', 'user'] },
  { to: '/coach', icon: Bot, label: 'Cigana Coach', group: 'oraculo', roles: ['admin', 'user'] },
  { to: '/lunar', icon: Bot, label: 'Lunar', group: 'oraculo', roles: ['admin', 'user'] },
  { to: '/horoscope', icon: Sparkles, label: 'Horóscopo Diário', group: 'oraculo', roles: ['admin', 'user'] },
  { to: '/spiritual', icon: Compass, label: 'Perfil Espiritual', group: 'oraculo', roles: ['admin', 'user'] },
  { to: '/calendar', icon: CalendarDays, label: 'Calendário Espiritual', group: 'oraculo', roles: ['admin', 'user'] },
  { to: '/affiliate', icon: CreditCard, label: 'Afiliados', group: 'conta', roles: ['admin', 'user'] },
  { to: '/agents', icon: Bot, label: 'Atendentes', group: 'oraculo', roles: ['admin', 'user'] },
  { to: '/runs', icon: Activity, label: 'Execuções', group: 'oraculo', roles: ['admin'] },
  { to: '/analytics/funnel', icon: Activity, label: 'Funnel', group: 'oraculo', roles: ['admin', 'user'] },
  { to: '/analytics/recovery', icon: Activity, label: 'Recuperação', group: 'oraculo', roles: ['admin', 'user'] },
  { to: '/integrations', icon: Plug, label: 'Integrações', group: 'avancado', roles: ['admin'] },
  { to: '/tenant-config', icon: KeyRound, label: 'Variáveis & Segredos', group: 'avancado', roles: ['admin'] },
  { to: '/admin/tenants', icon: ShieldCheck, label: 'Admin Console', group: 'platform', roles: ['admin'] },
];

const GROUP_LABELS: Record<string, string> = {
  painel: 'Painel',
  CRM: 'CRM',
  conta: 'Minha Conta',
  oraculo: 'Oráculo',
  avancado: 'Avançado',
  platform: 'Plataforma',
};

const PAGE_TITLES: Record<string, string> = {
  '/dashboard': 'Visão Geral',
  '/leads': 'Contatos & Conversas',
  '/blueprints': 'Fluxos',
  '/agents': 'Atendentes — Studio',
  '/runs': 'Execuções',
  '/integrations': 'Integrações',
  '/tenant-config': 'Variáveis & Segredos',
  '/marketplace': 'Marketplace de Fluxos',
};

function pageTitleFor(pathname: string): string {
  if (PAGE_TITLES[pathname]) return PAGE_TITLES[pathname];
  if (pathname.startsWith('/settings')) return 'Configurações';
  return '';
}

export default function Layout() {
  const [collapsed, setCollapsed] = useState(false);
  const location = useLocation();
  const { toggle } = useTheme();
  
  const { data: user, error: userError, isLoading: userLoading } = useQuery({
    queryKey: ['me'],
    queryFn: authApi.me,
    staleTime: Infinity,
    retry: false,
  });

  // Sem sessão -> backend retorna 401 -> redireciona pro login.
  // Não bloqueia onboarding (tela própria fora do Layout).
  if (userError && !userLoading && !location.pathname.startsWith('/onboarding')) {
    window.location.href = '/saas/login?next=' + encodeURIComponent(location.pathname);
    return null;
  }

  const pageTitle = pageTitleFor(location.pathname);

  // Filtra items por role
  const filteredItems = NAV_ITEMS.filter(item => 
    !item.roles || (user?.role && item.roles.includes(user.role))
  );

  // Agrupa items por group preservando ordem.
  const groups: { id: string; items: NavItem[] }[] = [];
  for (const item of filteredItems) {
    const gid = item.group ?? '_';
    let g = groups.find((x) => x.id === gid);
    if (!g) {
      g = { id: gid, items: [] };
      groups.push(g);
    }
    g.items.push(item);
  }

  return (
    <div className="flex h-screen w-full bg-bg-primary text-primary overflow-hidden font-sans selection:bg-accent-amethyst/30">
      {/* ── Sidebar ─────────────────────────────────────────────────── */}
      <aside
        className={[
          'flex-shrink-0 border-r border-border bg-bg-sidebar relative z-30',
          'transition-[width] duration-300 flex flex-col shadow-xl',
          collapsed ? 'w-[72px]' : 'w-[260px]',
        ].join(' ')}
      >
        {/* Brand */}
        <div className="flex items-center gap-3 h-[72px] px-5 border-b border-border flex-shrink-0 bg-bg-sidebar/50">
          <div
            className={[
              'w-10 h-10 rounded-2xl flex items-center justify-center flex-shrink-0 transition-all duration-500',
              'bg-bg-primary border border-border shadow-premium group',
              'text-accent-amethyst hover:scale-110',
            ].join(' ')}
          >
            <Logo size={22} />
          </div>
          {!collapsed && (
            <div className="flex flex-col leading-none overflow-hidden">
              <Wordmark className="text-xl font-black text-primary tracking-tight" />
              <span className="text-[10px] text-accent-amethyst font-black tracking-widest uppercase mt-1 opacity-80">
                Studio
              </span>
            </div>
          )}
        </div>

        {/* Nav */}
        <nav className="flex-1 py-6 px-3 overflow-y-auto space-y-8 scrollbar-hide">
          {groups.map((g) => (
            <div key={g.id}>
              {!collapsed && (
                <div className="text-[10px] font-black tracking-[0.2em] text-secondary/50 uppercase px-4 mb-3">
                  {GROUP_LABELS[g.id] ?? ''}
                </div>
              )}
              <ul className="space-y-1">
                {g.items.map((item) => (
                  <li key={item.to}>
                    <NavLink
                      to={item.to}
                      title={collapsed ? item.label : undefined}
                      className={({ isActive }) =>
                        [
                          'group relative flex items-center gap-3 px-4 py-3 rounded-2xl',
                          'text-sm font-bold transition-all duration-200',
                          isActive
                            ? 'bg-accent-amethyst text-white shadow-lg shadow-accent-amethyst/20'
                            : 'text-secondary hover:bg-bg-surface hover:text-primary',
                          collapsed ? 'justify-center px-0' : '',
                        ].join(' ')
                      }
                    >
                      {({ isActive }) => (
                        <>
                          <item.icon
                            className={[
                              'w-5 h-5 flex-shrink-0 transition-transform duration-200 group-hover:scale-110',
                              isActive
                                ? 'text-white'
                                : 'text-secondary group-hover:text-primary',
                            ].join(' ')}
                            strokeWidth={isActive ? 2.5 : 2}
                          />
                          {!collapsed && <span className="truncate">{item.label}</span>}
                          {isActive && !collapsed && (
                             <div className="absolute right-3 w-1.5 h-1.5 rounded-full bg-white/40 shadow-sm" />
                          )}
                        </>
                      )}
                    </NavLink>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </nav>

        {/* Rodapé */}
        <div className="border-t border-border p-4 bg-bg-sidebar/30">
          <div className={[
            'flex items-center gap-2 p-1.5 bg-bg-primary/50 rounded-2xl border border-border/50',
            collapsed ? 'flex-col' : 'justify-between',
          ].join(' ')}>
            <button
              type="button"
              title="Trocar workspace"
              className="p-2.5 rounded-xl text-secondary hover:text-primary hover:bg-bg-surface transition-all"
            >
              <ArrowLeftRight className="w-5 h-5" strokeWidth={2} />
            </button>
            <NavLink
              to="/settings/devices"
              title="Configurações"
              className={({ isActive }) =>
                [
                  'p-2.5 rounded-xl transition-all',
                  isActive
                    ? 'text-accent-amethyst bg-accent-amethyst/10 shadow-inner'
                    : 'text-secondary hover:text-accent-amethyst hover:bg-bg-surface',
                ].join(' ')
              }
            >
              <SettingsIcon className="w-5 h-5" strokeWidth={2} />
            </NavLink>
            <a
              href="/saas/logout"
              title="Sair"
              className="p-2.5 rounded-xl text-secondary hover:text-red-500 hover:bg-red-500/10 transition-all"
            >
              <Power className="w-5 h-5" strokeWidth={2} />
            </a>
          </div>
          <button
            onClick={() => setCollapsed(!collapsed)}
            className="w-full mt-3 flex items-center justify-center p-2.5 rounded-xl text-secondary hover:text-primary hover:bg-bg-primary transition-all border border-transparent hover:border-border"
          >
            {collapsed ? (
              <PanelLeftOpen className="w-5 h-5" strokeWidth={2} />
            ) : (
              <PanelLeftClose className="w-5 h-5" strokeWidth={2} />
            )}
          </button>
        </div>
      </aside>

      {/* ── Main ────────────────────────────────────────────────────── */}
      <main className="flex-1 flex flex-col min-w-0 h-full overflow-hidden relative">
        <header className="h-[72px] border-b border-border bg-bg-header backdrop-blur-md px-8 flex items-center justify-between flex-shrink-0 z-20 shadow-sm">
          <div className="flex items-center gap-4">
             {collapsed && <Logo size={24} className="text-accent-amethyst opacity-50" />}
             <h1 className="font-black text-xl text-primary tracking-tight">
               {pageTitle}
             </h1>
          </div>
          <div className="flex items-center gap-6">
            <button
              onClick={toggle}
              className="p-2.5 rounded-xl text-secondary hover:text-primary hover:bg-bg-surface transition-all border border-transparent hover:border-border"
              title="Alternar tema"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364-6.364l-.707.707M6.343 17.657l-.707.707m12.728 0l-.707-.707M6.343 6.343l-.707-.707M12 5a7 7 0 100 14 7 7 0 000-14z" />
              </svg>
            </button>
            <div className="h-6 w-px bg-border/60" />
            <div className="flex items-center gap-3 group cursor-pointer">
              <div className="flex flex-col items-end leading-tight">
                 <span className="text-xs font-black text-primary uppercase tracking-tight truncate max-w-[120px]">
                   {user?.name || user?.email?.split('@')[0] || 'Usuário'}
                 </span>
                 <span className="text-[9px] font-black text-accent-amethyst uppercase tracking-widest bg-accent-amethyst/10 px-1.5 py-0.5 rounded-md">
                   {user?.role === 'admin' ? 'Administrador' : 'Tarólogo'}
                 </span>
              </div>
              <div
                className="w-10 h-10 rounded-2xl bg-bg-surface border-2 border-border shadow-sm flex items-center justify-center text-[11px] font-black text-accent-amethyst group-hover:scale-110 transition-transform uppercase"
              >
                {(user?.name || user?.email || '??').substring(0, 2)}
              </div>
            </div>
          </div>
        </header>
        <div className="flex-1 overflow-auto bg-bg-primary scroll-smooth">
          <div className="h-full w-full">
            <Outlet />
          </div>
        </div>
      </main>
    </div>
  );
}
