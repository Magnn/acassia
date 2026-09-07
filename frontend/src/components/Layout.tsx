import { useState, useEffect } from 'react';
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
  Package,
  Settings as SettingsIcon,
  CreditCard,
  ShieldCheck,
  Store,
  Sparkles,
  Compass,
  CalendarDays,
  Library,
  CalendarClock,
  Globe,
  Megaphone,
  RefreshCw,
  BookOpen,
  GraduationCap,
  Ticket,
  Receipt,
  Users,
  Moon,
  Flame,
  Eye,
  Heart,
  Target,
  Mic,
  Wand2,
  Star,
  Rocket,
  Kanban,
  Webhook,
  UsersRound,
  Building2,
  ClipboardCheck,
  ChevronDown,
  Smartphone,
  Workflow,
  type LucideIcon,
} from 'lucide-react';
import Logo, { Wordmark } from './Logo';
import { useTheme } from '../context/ThemeContext';
import { useQuery } from '@tanstack/react-query';
import { authApi } from '../api/auth';

// ═══════════════════════════════════════════════════════════════
// Google Ads Style: Rail (icons) + Panel (sub-items) + Content
// ═══════════════════════════════════════════════════════════════

interface SubItem {
  to: string;
  icon: LucideIcon;
  label: string;
  roles?: ('admin' | 'user')[];
}

interface SubGroup {
  label: string;
  items: SubItem[];
  defaultOpen?: boolean;
}

interface RailHub {
  id: string;
  icon: LucideIcon;
  label: string;
  emoji?: string;
  sections: SubGroup[];
  roles?: ('admin' | 'user')[];
}

const RAIL_HUBS: RailHub[] = [
  {
    id: 'painel', icon: LayoutDashboard, label: 'Painel',
    sections: [
      { label: '', items: [
        { to: '/dashboard', icon: LayoutDashboard, label: 'Visão Geral' },
        { to: '/catalog', icon: Package, label: 'Meus Produtos' },
      ]},
    ],
  },
  {
    id: 'contatos', icon: MessageSquare, label: 'Contatos',
    sections: [
      { label: '', items: [
        { to: '/leads', icon: MessageSquare, label: 'Conversas' },
        { to: '/pipeline', icon: Kanban, label: 'Pipeline' },
        { to: '/scheduling', icon: CalendarClock, label: 'Agendamento' },
        { to: '/profile', icon: Globe, label: 'Perfil Público' },
        { to: '/subscriptions', icon: RefreshCw, label: 'Assinaturas' },
      ]},
    ],
  },
  {
    id: 'campanhas', icon: Megaphone, label: 'Campanhas',
    sections: [
      { label: 'Disparo', defaultOpen: true, items: [
        { to: '/broadcast', icon: Megaphone, label: 'Broadcast' },
        { to: '/launches', icon: Rocket, label: 'Lançamentos' },
      ]},
      { label: 'Grupos & Links', defaultOpen: true, items: [
        { to: '/wa-groups', icon: UsersRound, label: 'Grupos WhatsApp' },
        { to: '/smart-links', icon: Webhook, label: 'Smart Links' },
      ]},
      { label: 'Eventos', items: [
        { to: '/events', icon: Ticket, label: 'Eventos & Retiros' },
      ]},
    ],
  },
  {
    id: 'automacoes', icon: Workflow, label: 'Automações & IA',
    sections: [
      { label: 'Funis & Construtor', defaultOpen: true, items: [
        { to: '/blueprints', icon: FolderTree, label: 'Funis de Vendas' },
        { to: '/templates', icon: FolderTree, label: 'Templates de Funil' },
        { to: '/marketplace', icon: Store, label: 'Marketplace de Fluxos' },
      ]},
      { label: 'Agentes & Inteligência', defaultOpen: true, items: [
        { to: '/voice', icon: Mic, label: 'Voz & Áudios IA' },
        { to: '/coach', icon: Bot, label: 'Agente de Vendas IA' },
        { to: '/reading', icon: Sparkles, label: 'Análise de Imagens & Visão' },
      ]},
      { label: 'Módulos Especializados', items: [
        { to: '/tarot', icon: Wand2, label: 'Tarot Virtual' },
        { to: '/lunar', icon: Moon, label: 'Lunar' },
        { to: '/horoscope', icon: Star, label: 'Horóscopo Diário' },
        { to: '/spiritual', icon: Compass, label: 'Perfil Espiritual' },
        { to: '/calendar', icon: CalendarDays, label: 'Calendário Espiritual' },
      ]},
      { label: 'Comunidade & Conteúdo', items: [
        { to: '/audio-library', icon: Library, label: 'Biblioteca de Mídia' },
        { to: '/journal', icon: BookOpen, label: 'Diário & Notas' },
        { to: '/trails', icon: GraduationCap, label: 'Trilhas de Conteúdo' },
        { to: '/rituals', icon: Flame, label: 'Rotinas Diárias' },
        { to: '/dreams', icon: Eye, label: 'Sonhos' },
        { to: '/vision-board', icon: Target, label: 'Quadro de Metas' },
        { to: '/community', icon: Users, label: 'Comunidade' },
      ]},
    ],
  },
  {
    id: 'monetizacao', icon: CreditCard, label: 'Monetização',
    sections: [
      { label: '', items: [
        { to: '/content', icon: Package, label: 'Infoprodutos' },
        { to: '/social-content', icon: Megaphone, label: 'Gerador Conteúdo' },
        { to: '/pix', icon: CreditCard, label: 'Pix QR' },
        { to: '/affiliate', icon: Heart, label: 'Afiliados' },
        { to: '/fiscal', icon: Receipt, label: 'Notas Fiscais' },
      ]},
    ],
  },
  {
    id: 'config', icon: SettingsIcon, label: 'Config.',
    sections: [
      { label: 'Operação', defaultOpen: true, items: [
        { to: '/departments', icon: Building2, label: 'Departamentos' },
        { to: '/checkout-webhooks', icon: Webhook, label: 'Checkout Webhooks' },
        { to: '/service-ratings', icon: ClipboardCheck, label: 'Avaliações (NPS)' },
      ]},
      { label: 'Integrações', items: [
        { to: '/integrations', icon: Plug, label: 'Integrações' },
        { to: '/tenant-config', icon: KeyRound, label: 'Variáveis & Segredos' },
        { to: '/billing', icon: CreditCard, label: 'Assinatura Plataforma' },
      ]},
      { label: 'Avançado', items: [
        { to: '/agents', icon: Bot, label: 'Atendentes' },
        { to: '/runs', icon: Activity, label: 'Execuções' },
        { to: '/analytics/funnel', icon: Activity, label: 'Funil Analytics' },
        { to: '/analytics/recovery', icon: Activity, label: 'Recuperação' },
        { to: '/admin/tenants', icon: ShieldCheck, label: 'Admin Console', roles: ['admin'] },
      ]},
    ],
  },
];

// ── Panel Sub-Group (collapsible) ──
function PanelSubGroup({ group, pathname, userRole }: { group: SubGroup; pathname: string; userRole?: string }) {
  const hasActive = group.items.some(i => pathname === i.to || pathname.startsWith(i.to + '/'));
  const [open, setOpen] = useState(group.defaultOpen || hasActive || !group.label);

  const items = group.items.filter(i => !i.roles || (userRole && i.roles.includes(userRole as 'admin' | 'user')));
  if (items.length === 0) return null;

  return (
    <div className="mb-1">
      {group.label && (
        <button
          onClick={() => setOpen(!open)}
          className={[
            'w-full flex items-center justify-between px-4 py-2 text-left transition-all',
            hasActive ? 'text-primary' : 'text-secondary hover:text-primary',
          ].join(' ')}
        >
          <span className="text-[10px] font-black uppercase tracking-widest">{group.label}</span>
          <ChevronDown className={`w-3 h-3 transition-transform duration-200 ${open ? '' : '-rotate-90'}`} />
        </button>
      )}
      {open && (
        <ul className="space-y-0.5">
          {items.map(item => (
            <li key={item.to}>
              <NavLink
                to={item.to}
                className={({ isActive }) => [
                  'flex items-center gap-2.5 px-4 py-2 rounded-lg mx-1 text-[13px] font-semibold transition-all duration-150',
                  isActive
                    ? 'bg-accent-amethyst text-white shadow-md shadow-accent-amethyst/20'
                    : 'text-secondary hover:bg-bg-surface hover:text-primary',
                ].join(' ')}
              >
                <item.icon className="w-4 h-4 flex-shrink-0" strokeWidth={1.8} />
                <span className="truncate">{item.label}</span>
              </NavLink>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

export default function Layout() {
  const location = useLocation();
  const { toggle } = useTheme();
  
  // Find which hub owns the current route
  const findActiveHub = (): string => {
    for (const hub of RAIL_HUBS) {
      for (const section of hub.sections) {
        if (section.items.some(i => location.pathname === i.to || location.pathname.startsWith(i.to + '/'))) {
          return hub.id;
        }
      }
    }
    return 'painel';
  };

  const [activeHub, setActiveHub] = useState(findActiveHub);
  const [panelOpen, setPanelOpen] = useState(true);

  // Auto-update active hub when route changes
  useEffect(() => {
    const hub = findActiveHub();
    setActiveHub(hub);
    setPanelOpen(true);
  }, [location.pathname]);

  const { data: user, error: userError, isLoading: userLoading } = useQuery({
    queryKey: ['me'],
    queryFn: authApi.me,
    staleTime: Infinity,
    retry: false,
  });

  if (userError && !userLoading && !location.pathname.startsWith('/onboarding')) {
    window.location.href = '/saas/login?next=' + encodeURIComponent('/builder' + location.pathname);
    return null;
  }

  if (userLoading || !user) {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen bg-bg-primary gap-4">
        <div className="w-12 h-12 border-4 border-accent-amethyst/20 border-t-accent-amethyst rounded-full animate-spin" />
      </div>
    );
  }

  const currentHub = RAIL_HUBS.find(h => h.id === activeHub);

  return (
    <div className="flex h-screen w-full bg-bg-primary text-primary overflow-hidden font-sans selection:bg-accent-amethyst/30">

      {/* ═══ RAIL (thin icon bar — always visible) ═══ */}
      <div className="w-[72px] flex-shrink-0 bg-bg-sidebar border-r border-border flex flex-col items-center z-40 shadow-xl">
        {/* Logo */}
        <div className="h-[64px] flex items-center justify-center border-b border-border w-full">
          <div className="w-10 h-10 rounded-2xl flex items-center justify-center bg-bg-primary border border-border text-accent-amethyst hover:scale-110 transition-transform">
            <Logo size={22} />
          </div>
        </div>

        {/* Hub Icons */}
        <nav className="flex-1 flex flex-col items-center gap-1 py-4 w-full">
          {RAIL_HUBS.map(hub => {
            if (hub.roles && (!user?.role || !hub.roles.includes(user.role))) return null;
            const isActive = activeHub === hub.id;
            const HubIcon = hub.icon;

            return (
              <button
                key={hub.id}
                onClick={() => {
                  if (activeHub === hub.id) {
                    setPanelOpen(!panelOpen);
                  } else {
                    setActiveHub(hub.id);
                    setPanelOpen(true);
                  }
                }}
                className={[
                  'group relative flex flex-col items-center justify-center w-14 h-14 rounded-2xl transition-all duration-200',
                  isActive
                    ? 'bg-accent-amethyst text-white shadow-lg shadow-accent-amethyst/30'
                    : 'text-secondary hover:bg-bg-surface hover:text-primary',
                ].join(' ')}
                title={hub.label}
              >
                <HubIcon className="w-5 h-5" strokeWidth={isActive ? 2.5 : 1.8} />
                <span className={[
                  'text-[9px] font-black mt-0.5 uppercase tracking-tight leading-none',
                  isActive ? 'text-white/90' : 'text-secondary/70 group-hover:text-primary/70',
                ].join(' ')}>
                  {hub.label}
                </span>
                {/* Active indicator */}
                {isActive && (
                  <div className="absolute -left-0.5 top-1/2 -translate-y-1/2 w-1 h-8 bg-accent-amethyst rounded-r-full" />
                )}
              </button>
            );
          })}
        </nav>

        {/* Rail Footer */}
        <div className="border-t border-border py-3 flex flex-col items-center gap-2 w-full">
          <NavLink
            to="/workspaces"
            title="Trocar workspace"
            className={({ isActive }) => [
              'p-2.5 rounded-xl transition-all',
              isActive ? 'text-accent-amethyst bg-accent-amethyst/10' : 'text-secondary hover:text-accent-amethyst hover:bg-bg-surface',
            ].join(' ')}
          >
            <ArrowLeftRight className="w-4 h-4" />
          </NavLink>
          <NavLink
            to="/settings/devices"
            title="Configurações"
            className={({ isActive }) => [
              'p-2.5 rounded-xl transition-all',
              isActive ? 'text-accent-amethyst bg-accent-amethyst/10' : 'text-secondary hover:text-accent-amethyst hover:bg-bg-surface',
            ].join(' ')}
          >
            <SettingsIcon className="w-4 h-4" />
          </NavLink>
          <a href="/saas/logout" title="Sair" className="p-2.5 rounded-xl text-secondary hover:text-red-500 hover:bg-red-500/10 transition-all">
            <Power className="w-4 h-4" />
          </a>
        </div>
      </div>

      {/* ═══ PANEL (secondary sidebar — context menu) ═══ */}
      <div
        className={[
          'flex-shrink-0 bg-bg-sidebar/50 backdrop-blur-sm border-r border-border flex flex-col z-30',
          'transition-all duration-300 overflow-hidden',
          panelOpen ? 'w-[220px]' : 'w-0',
        ].join(' ')}
      >
        {panelOpen && currentHub && (
          <>
            {/* Panel Header */}
            <div className="h-[64px] flex items-center justify-between px-4 border-b border-border flex-shrink-0">
              <h2 className="text-sm font-black text-primary uppercase tracking-wider">{currentHub.label}</h2>
              <button
                onClick={() => setPanelOpen(false)}
                className="p-1.5 rounded-lg text-secondary hover:text-primary hover:bg-bg-surface transition-all"
              >
                <PanelLeftClose className="w-4 h-4" />
              </button>
            </div>

            {/* Panel Items */}
            <div className="flex-1 overflow-y-auto py-3 scrollbar-hide">
              {currentHub.sections.map((section, i) => (
                <PanelSubGroup
                  key={section.label || i}
                  group={section}
                  pathname={location.pathname}
                  userRole={user?.role}
                />
              ))}
            </div>
          </>
        )}
      </div>

      {/* ═══ MAIN CONTENT ═══ */}
      <main className="flex-1 flex flex-col min-w-0 h-full overflow-hidden relative">
        {/* Header Bar */}
        {!location.pathname.startsWith('/flows/') && (
          <header className="h-[64px] border-b border-border bg-bg-header backdrop-blur-md px-6 flex items-center justify-between flex-shrink-0 z-20 shadow-sm">
            <div className="flex items-center gap-3">
              {!panelOpen && (
                <button
                  onClick={() => setPanelOpen(true)}
                  className="p-2 rounded-lg text-secondary hover:text-primary hover:bg-bg-surface transition-all mr-1"
                >
                  <PanelLeftOpen className="w-4 h-4" />
                </button>
              )}
            </div>
            <div className="flex items-center gap-5">
              <button
                onClick={toggle}
                className="p-2 rounded-xl text-secondary hover:text-primary hover:bg-bg-surface transition-all border border-transparent hover:border-border"
                title="Alternar tema"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364-6.364l-.707.707M6.343 17.657l-.707.707m12.728 0l-.707-.707M6.343 6.343l-.707-.707M12 5a7 7 0 100 14 7 7 0 000-14z" />
                </svg>
              </button>
              <div className="h-5 w-px bg-border/60" />
              <div className="flex items-center gap-3 group cursor-pointer">
                <div className="flex flex-col items-end leading-tight">
                  <span className="text-[11px] font-black text-primary uppercase tracking-tight truncate max-w-[120px]">
                    {user?.name || user?.email?.split('@')[0] || 'Usuário'}
                  </span>
                  <span className="text-[8px] font-black text-accent-amethyst uppercase tracking-widest bg-accent-amethyst/10 px-1.5 py-0.5 rounded-md">
                    {user?.role === 'admin' ? 'Admin' : 'Tarólogo'}
                  </span>
                </div>
                <div className="w-9 h-9 rounded-2xl bg-bg-surface border-2 border-border shadow-sm flex items-center justify-center text-[10px] font-black text-accent-amethyst group-hover:scale-110 transition-transform uppercase">
                  {(user?.name || user?.email || '??').substring(0, 2)}
                </div>
              </div>
            </div>
          </header>
        )}

        {/* Content */}
        <div className="flex-1 overflow-auto bg-bg-primary scroll-smooth">
          <div className="h-full w-full">
            <Outlet />
          </div>
        </div>
      </main>
    </div>
  );
}
