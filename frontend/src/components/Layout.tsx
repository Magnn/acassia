import { useState, useMemo } from 'react';
import { NavLink, Outlet, useLocation } from 'react-router-dom';
import {
  LayoutDashboard,
  MessageSquare,
  Workflow,
  Bot,
  Megaphone,
  Kanban,
  Plug,
  Store,
  FolderTree,
  Mic,
  Library,
  CalendarClock,
  Settings as SettingsIcon,
  CreditCard,
  ShieldCheck,
  Power,
  ChevronDown,
  Menu,
  X,
  Sparkles,
  type LucideIcon,
} from 'lucide-react';
import Logo, { Wordmark } from './Logo';
import { useTheme } from '../context/ThemeContext';
import { useQuery } from '@tanstack/react-query';
import { authApi } from '../api/auth';

interface NavItem {
  to: string;
  icon: LucideIcon;
  label: string;
  badge?: string;
  roles?: ('admin' | 'user')[];
}

interface NavSection {
  title: string;
  items: NavItem[];
}

const NAVIGATION_SECTIONS: NavSection[] = [
  {
    title: 'Principal',
    items: [
      { to: '/blueprints', icon: Workflow, label: 'Funis & Automações' },
      { to: '/agents', icon: Bot, label: 'Agentes de IA (WhatsApp)' },
      { to: '/leads', icon: MessageSquare, label: 'Conversas & Inbox' },
      { to: '/dashboard', icon: LayoutDashboard, label: 'Visão Geral' },
      { to: '/pipeline', icon: Kanban, label: 'Pipeline & CRM' },
      { to: '/broadcast', icon: Megaphone, label: 'Disparos WhatsApp' },
      { to: '/integrations', icon: Plug, label: 'Conexão & API Meta' },
    ],
  },
  {
    title: 'Modelos & Recursos',
    items: [
      { to: '/templates', icon: FolderTree, label: 'Templates de Funil' },
      { to: '/coach', icon: Sparkles, label: 'Copilot Estratégico' },
      { to: '/marketplace', icon: Store, label: 'Marketplace de Fluxos' },
      { to: '/voice', icon: Mic, label: 'Voz & Áudios IA' },
      { to: '/audio-library', icon: Library, label: 'Biblioteca de Mídia' },
      { to: '/scheduling', icon: CalendarClock, label: 'Agendamentos' },
    ],
  },
  {
    title: 'Configurações',
    items: [
      { to: '/settings/devices', icon: SettingsIcon, label: 'Configurações' },
      { to: '/billing', icon: CreditCard, label: 'Plano & Faturamento' },
      { to: '/admin/tenants', icon: ShieldCheck, label: 'Super Admin', roles: ['admin'] },
    ],
  },
];

export default function Layout() {
  const location = useLocation();
  const { toggle } = useTheme();
  const [mobileOpen, setMobileOpen] = useState(false);

  // Consulta do usuário logado
  const { data: user } = useQuery({
    queryKey: ['me'],
    queryFn: authApi.me,
    staleTime: 60_000,
  });

  // Fecha o menu mobile ao navegar
  const closeMobile = () => setMobileOpen(false);

  // Determina o título da página atual para os breadcrumbs
  const currentPageTitle = useMemo(() => {
    for (const sec of NAVIGATION_SECTIONS) {
      for (const item of sec.items) {
        if (location.pathname === item.to || location.pathname.startsWith(item.to + '/')) {
          return item.label;
        }
      }
    }
    if (location.pathname.startsWith('/flows/')) return 'Editor de Fluxo';
    return 'Acássia';
  }, [location.pathname]);

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-zinc-950 text-zinc-100 antialiased font-sans">
      {/* ═══ MOBILE BACKDROP ═══ */}
      {mobileOpen && (
        <div 
          className="fixed inset-0 z-40 bg-black/70 backdrop-blur-sm md:hidden transition-opacity"
          onClick={closeMobile}
        />
      )}

      {/* ═══ SINGLE SIDEBAR (Padrão ChatbotX / Linear) ═══ */}
      <aside
        className={[
          'fixed md:static inset-y-0 left-0 z-50 w-64 bg-zinc-950/95 md:bg-zinc-900/60 backdrop-blur-xl border-r border-zinc-800/80 flex flex-col transition-transform duration-200 ease-in-out',
          mobileOpen ? 'translate-x-0' : '-translate-x-full md:translate-x-0',
        ].join(' ')}
      >
        {/* Topo da Sidebar: Logo & Workspace */}
        <div className="h-16 px-5 border-b border-zinc-800/80 flex items-center justify-between flex-shrink-0">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-xl bg-gradient-to-tr from-indigo-600 to-violet-500 shadow-md shadow-indigo-500/20 flex items-center justify-center text-white font-black text-sm ring-1 ring-white/20">
              ⚡
            </div>
            <div className="flex flex-col">
              <span className="font-bold text-sm tracking-tight text-white flex items-center gap-1.5">
                Acássia
                <span className="px-1.5 py-0.2 rounded bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 text-[9px] font-bold">
                  PRO
                </span>
              </span>
              <span className="text-[11px] text-zinc-400 truncate max-w-[140px]">
                {user?.name || user?.email?.split('@')[0] || 'Meu Workspace'}
              </span>
            </div>
          </div>

          <button
            onClick={closeMobile}
            className="md:hidden p-1.5 rounded-lg text-zinc-400 hover:text-white hover:bg-zinc-800"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Itens de Navegação */}
        <div className="flex-1 overflow-y-auto px-3 py-4 space-y-6 scrollbar-thin scrollbar-thumb-zinc-800">
          {NAVIGATION_SECTIONS.map((section) => {
            const visibleItems = section.items.filter(
              (item) => !item.roles || (user?.role && item.roles.includes(user.role as 'admin' | 'user'))
            );

            if (visibleItems.length === 0) return null;

            return (
              <div key={section.title} className="space-y-1">
                <div className="px-3 mb-2 text-[10px] font-bold uppercase tracking-wider text-zinc-300">
                  {section.title}
                </div>
                {visibleItems.map((item) => {
                  const isActive =
                    location.pathname === item.to ||
                    (item.to !== '/' && location.pathname.startsWith(item.to + '/'));

                  return (
                    <NavLink
                      key={item.to}
                      to={item.to}
                      onClick={closeMobile}
                      className={[
                        'flex items-center justify-between px-3 py-2 rounded-xl text-xs font-semibold transition-all duration-150 group',
                        isActive
                          ? 'bg-indigo-600/15 text-indigo-300 border border-indigo-500/30 shadow-sm'
                          : 'text-zinc-400 hover:text-zinc-100 hover:bg-zinc-800/50',
                      ].join(' ')}
                    >
                      <div className="flex items-center gap-2.5">
                        <item.icon
                          className={[
                            'w-4 h-4 transition-colors',
                            isActive ? 'text-indigo-400' : 'text-zinc-400 group-hover:text-zinc-200',
                          ].join(' ')}
                          strokeWidth={isActive ? 2.2 : 1.8}
                        />
                        <span>{item.label}</span>
                      </div>
                      {item.badge && (
                        <span className="px-1.5 py-0.5 rounded-full text-[9px] font-bold bg-indigo-500/20 text-indigo-300">
                          {item.badge}
                        </span>
                      )}
                    </NavLink>
                  );
                })}
              </div>
            );
          })}
        </div>

        {/* Rodapé da Sidebar: Perfil do Usuário */}
        <div className="p-3 border-t border-zinc-800/80 bg-zinc-950/40 flex items-center justify-between">
          <div className="flex items-center gap-2.5 min-w-0">
            <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-indigo-500/20 to-purple-500/20 border border-indigo-500/30 flex items-center justify-center text-xs font-bold text-indigo-300 shrink-0 uppercase">
              {(user?.name || user?.email || 'US').substring(0, 2)}
            </div>
            <div className="flex flex-col min-w-0">
              <span className="text-xs font-semibold text-zinc-200 truncate">
                {user?.name || user?.email?.split('@')[0] || 'Usuário'}
              </span>
              <span className="text-[10px] text-zinc-300 truncate">
                {user?.role === 'admin' ? 'Super Admin' : 'Membro Pro'}
              </span>
            </div>
          </div>

          <a
            href="/saas/logout"
            title="Sair da conta"
            className="p-1.5 rounded-lg text-zinc-500 hover:text-rose-400 hover:bg-rose-500/10 transition-all shrink-0"
          >
            <Power className="w-4 h-4" />
          </a>
        </div>
      </aside>

      {/* ═══ ÁREA PRINCIPAL DE CONTEÚDO ═══ */}
      <main className="flex-1 flex flex-col min-w-0 h-full overflow-hidden bg-zinc-950 relative">
        {/* Header Superior Fino (Apenas fora do editor de nós full-screen) */}
        {!location.pathname.startsWith('/flows/') && (
          <header className="h-14 px-6 border-b border-zinc-800/80 bg-zinc-950/50 backdrop-blur-md flex items-center justify-between shrink-0 z-20">
            <div className="flex items-center gap-3">
              <button
                onClick={() => setMobileOpen(true)}
                className="md:hidden p-1.5 rounded-lg text-zinc-400 hover:text-white hover:bg-zinc-800"
              >
                <Menu className="w-5 h-5" />
              </button>

              {/* Breadcrumb sutil */}
              <div className="flex items-center gap-2 text-xs font-medium text-zinc-400">
                <span>Plataforma</span>
                <span>/</span>
                <span className="text-zinc-200 font-semibold">{currentPageTitle}</span>
              </div>
            </div>

            <div className="flex items-center gap-3">
              <button
                onClick={toggle}
                className="p-2 rounded-xl text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800/60 transition-all"
                title="Alternar tema"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364-6.364l-.707.707M6.343 17.657l-.707.707m12.728 0l-.707-.707M6.343 6.343l-.707-.707M12 5a7 7 0 100 14 7 7 0 000-14z" />
                </svg>
              </button>
            </div>
          </header>
        )}

        {/* Conteúdo da Rota */}
        <div className="flex-1 overflow-auto bg-zinc-950 relative">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
