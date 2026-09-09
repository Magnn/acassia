import { useState, useMemo, useEffect } from 'react';
import { NavLink, Outlet, useLocation } from 'react-router-dom';
import {
  LayoutDashboard,
  MessageSquare,
  Workflow,
  Bot,
  Megaphone,
  GitBranch,
  Kanban,
  Plug,
  Smartphone,
  FolderTree,
  Mic,
  Library,
  CalendarClock,
  Settings as SettingsIcon,
  CreditCard,
  ShieldCheck,
  Power,
  ChevronDown,
  ChevronUp,
  Menu,
  X,
  Sparkles,
  TrendingUp,
  Layers,
  type LucideIcon,
} from 'lucide-react';
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
  collapsible?: boolean;
  defaultOpen?: boolean;
  items: NavItem[];
}

// ═══ ESTRUTURA DE NAVEGAÇÃO ENXUTA (PADRÃO CHATBOTX / LINEAR) ═══
const NAVIGATION_SECTIONS: NavSection[] = [
  {
    title: 'Principal',
    collapsible: false,
    items: [
      { to: '/leads', icon: MessageSquare, label: 'Conversas / Live Chat', badge: 'Ao Vivo' },
      { to: '/blueprints', icon: Workflow, label: 'Funis & Automações' },
      { to: '/agents', icon: Bot, label: 'Agentes de IA' },
      { to: '/broadcast', icon: Megaphone, label: 'Disparos em Massa' },
      { to: '/sequences', icon: GitBranch, label: 'Sequências (Drip)' },
      { to: '/growth-tools', icon: TrendingUp, label: 'Growth Tools (Redes & Cupons)' },
      { to: '/pipeline', icon: Kanban, label: 'Contatos & CRM' },
      { to: '/wa-connection', icon: Smartphone, label: 'Conexão WhatsApp & Meta', badge: 'Oficial' },
      { to: '/dashboard', icon: LayoutDashboard, label: 'Visão Geral' },
    ],
  },
  {
    title: 'Recursos & Mídia',
    collapsible: true,
    defaultOpen: false,
    items: [
      { to: '/templates', icon: FolderTree, label: 'Templates de Funil' },
      { to: '/voice', icon: Mic, label: 'Voz & Áudios IA (Cigana)' },
      { to: '/audio-library', icon: Library, label: 'Biblioteca de Áudios' },
      { to: '/coach', icon: Sparkles, label: 'Copilot Estratégico' },
      { to: '/scheduling', icon: CalendarClock, label: 'Agendamentos' },
    ],
  },
  {
    title: 'Configurações',
    collapsible: true,
    defaultOpen: false,
    items: [
      { to: '/integrations', icon: Plug, label: 'Webhooks & Integrações' },
      { to: '/settings/devices', icon: SettingsIcon, label: 'Configurações do Sistema' },
      { to: '/billing', icon: CreditCard, label: 'Plano & Faturamento' },
      { to: '/admin/tenants', icon: ShieldCheck, label: 'Super Admin', roles: ['admin'] },
    ],
  },
];

export default function Layout() {
  const location = useLocation();
  const { toggle } = useTheme();
  const [mobileOpen, setMobileOpen] = useState(false);

  // Estados de seções colapsadas
  const [openSections, setOpenSections] = useState<Record<string, boolean>>({
    'Recursos & Mídia': false,
    'Configurações': false,
  });

  const toggleSection = (title: string) => {
    setOpenSections((prev) => ({ ...prev, [title]: !prev[title] }));
  };

  // Consulta do usuário logado
  const { data: user, error: userError } = useQuery({
    queryKey: ['me'],
    queryFn: authApi.me,
    staleTime: 60_000,
    retry: false,
  });

  useEffect(() => {
    if (userError) {
      window.location.href = '/saas/login?next=' + encodeURIComponent(location.pathname + location.search);
    }
  }, [userError, location.pathname, location.search]);

  const closeMobile = () => setMobileOpen(false);

  // Título dinâmico da tela
  const currentPageTitle = useMemo(() => {
    for (const sec of NAVIGATION_SECTIONS) {
      for (const item of sec.items) {
        if (location.pathname === item.to || location.pathname.startsWith(item.to + '/')) {
          return item.label;
        }
      }
    }
    if (location.pathname.startsWith('/flows/')) return 'Editor Visual de Funil';
    return 'Acássia Studio';
  }, [location.pathname]);

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-zinc-950 text-zinc-100 antialiased font-sans">
      {/* Mobile Backdrop */}
      {mobileOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/70 backdrop-blur-sm md:hidden transition-opacity"
          onClick={closeMobile}
        />
      )}

      {/* ═══ SIDEBAR ENXUTA (PADRÃO CHATBOTX) ═══ */}
      <aside
        className={[
          'fixed md:static inset-y-0 left-0 z-50 w-64 bg-zinc-950 border-r border-zinc-800/80 flex flex-col transition-transform duration-200 ease-in-out',
          mobileOpen ? 'translate-x-0' : '-translate-x-full md:translate-x-0',
        ].join(' ')}
      >
        {/* Topo da Sidebar: Workspace Selector */}
        <div className="h-16 px-4 border-b border-zinc-800/80 flex items-center justify-between shrink-0">
          <div className="flex items-center gap-2.5 min-w-0">
            <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-indigo-500 to-violet-600 shadow-md shadow-indigo-500/20 flex items-center justify-center text-white font-bold text-sm shrink-0">
              ⚡
            </div>
            <div className="flex flex-col min-w-0">
              <div className="flex items-center gap-1.5">
                <span className="font-bold text-sm text-zinc-100 tracking-tight truncate">
                  Acássia
                </span>
                <span className="px-1.5 py-0.2 rounded text-[9px] font-bold bg-indigo-500/15 text-indigo-400 border border-indigo-500/25 uppercase">
                  PRO
                </span>
              </div>
              <span className="text-[11px] text-zinc-400 truncate">
                {user?.name || user?.email?.split('@')[0] || 'Meu Workspace'}
              </span>
            </div>
          </div>

          <button
            onClick={closeMobile}
            className="md:hidden p-1.5 rounded-lg text-zinc-400 hover:text-white hover:bg-zinc-800"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Lista de Navegação com Seções Enxutas */}
        <div className="flex-1 overflow-y-auto px-3 py-3 space-y-4 scrollbar-thin scrollbar-thumb-zinc-800">
          {NAVIGATION_SECTIONS.map((section) => {
            const visibleItems = section.items.filter(
              (item) => !item.roles || (user?.role && item.roles.includes(user.role as 'admin' | 'user'))
            );

            if (visibleItems.length === 0) return null;

            const isCollapsible = section.collapsible;
            // Se algum item da seção estiver ativo, mantém aberta
            const hasActiveItem = visibleItems.some(
              (item) => location.pathname === item.to || location.pathname.startsWith(item.to + '/')
            );
            const isOpen = !isCollapsible || (openSections[section.title] ?? false) || hasActiveItem;

            return (
              <div key={section.title} className="space-y-0.5">
                {/* Título da Seção */}
                {isCollapsible ? (
                  <button
                    type="button"
                    onClick={() => toggleSection(section.title)}
                    className="w-full flex items-center justify-between px-2.5 py-1 text-[10px] font-bold uppercase tracking-wider text-zinc-300 hover:text-zinc-100 transition-colors group"
                  >
                    <span>{section.title}</span>
                    <span className="text-zinc-400 group-hover:text-zinc-200">
                      {isOpen ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
                    </span>
                  </button>
                ) : (
                  <div className="px-2.5 py-1 text-[10px] font-bold uppercase tracking-wider text-zinc-300">
                    {section.title}
                  </div>
                )}

                {/* Itens */}
                {isOpen && (
                  <div className="space-y-0.5 pt-0.5">
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
                            'flex items-center justify-between px-3 py-2 rounded-xl text-xs font-medium transition-all group',
                            isActive
                              ? 'bg-zinc-800/90 text-zinc-100 font-semibold border border-zinc-700/60 shadow-sm'
                              : 'text-zinc-400 hover:text-zinc-200 hover:bg-zinc-900/80',
                          ].join(' ')}
                        >
                          <div className="flex items-center gap-2.5 min-w-0">
                            <item.icon
                              className={[
                                'w-4 h-4 transition-colors shrink-0',
                                isActive
                                  ? 'text-indigo-400'
                                  : 'text-zinc-400 group-hover:text-zinc-200',
                              ].join(' ')}
                              strokeWidth={isActive ? 2.2 : 1.8}
                            />
                            <span className="truncate">{item.label}</span>
                          </div>
                          {item.badge && (
                            <span
                              className={`px-1.5 py-0.2 rounded text-[9px] font-bold uppercase shrink-0 ${
                                item.badge === 'Ao Vivo'
                                  ? 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/30'
                                  : 'bg-indigo-500/15 text-indigo-400 border border-indigo-500/30'
                              }`}
                            >
                              {item.badge}
                            </span>
                          )}
                        </NavLink>
                      );
                    })}
                  </div>
                )}
              </div>
            );
          })}
        </div>

        {/* Rodapé da Sidebar: Perfil do Usuário */}
        <div className="p-3 border-t border-zinc-800/80 bg-zinc-950 flex items-center justify-between shrink-0">
          <div className="flex items-center gap-2.5 min-w-0">
            <div className="w-8 h-8 rounded-xl bg-zinc-800 border border-zinc-700/60 flex items-center justify-center text-xs font-bold text-zinc-200 shrink-0 uppercase">
              {(user?.name || user?.email || 'US').substring(0, 2)}
            </div>
            <div className="flex flex-col min-w-0">
              <span className="text-xs font-medium text-zinc-200 truncate">
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
            className="p-1.5 rounded-lg text-zinc-400 hover:text-rose-400 hover:bg-rose-500/10 transition-all shrink-0"
          >
            <Power className="w-4 h-4" />
          </a>
        </div>
      </aside>

      {/* ═══ ÁREA PRINCIPAL DE CONTEÚDO ═══ */}
      <main className="flex-1 flex flex-col min-w-0 h-full overflow-hidden bg-zinc-950 relative">
        {/* Header Superior Fino */}
        {!location.pathname.startsWith('/flows/') && (
          <header className="h-14 px-6 border-b border-zinc-800/80 bg-zinc-950 flex items-center justify-between shrink-0 z-20">
            <div className="flex items-center gap-3">
              <button
                onClick={() => setMobileOpen(true)}
                className="md:hidden p-1.5 rounded-lg text-zinc-400 hover:text-white hover:bg-zinc-800"
              >
                <Menu className="w-5 h-5" />
              </button>

              <div className="flex items-center gap-2 text-xs font-medium text-zinc-400">
                <span>Plataforma</span>
                <span>/</span>
                <span className="text-zinc-200 font-semibold">{currentPageTitle}</span>
              </div>
            </div>

            <div className="flex items-center gap-2.5">
              <button
                onClick={toggle}
                className="p-2 rounded-xl text-zinc-400 hover:text-zinc-200 hover:bg-zinc-900 transition-all border border-zinc-800/60"
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
