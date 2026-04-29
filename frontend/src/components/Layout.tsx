import { useState } from 'react';
import { NavLink, Outlet, useLocation } from 'react-router-dom';
import {
  Activity,
  Bot,
  FolderTree,
  KeyRound,
  LayoutDashboard,
  MessageSquare,
  PanelLeftClose,
  PanelLeftOpen,
  Plug,
  Settings as SettingsIcon,
  Users,
} from 'lucide-react';
import Logo, { Wordmark } from './Logo';

interface NavItem {
  to: string;
  icon: typeof LayoutDashboard;
  label: string;
  group?: string;
}

const NAV_ITEMS: NavItem[] = [
  { to: '/dashboard', icon: LayoutDashboard, label: 'Visão geral', group: 'painel' },
  { to: '/inbox', icon: MessageSquare, label: 'Caixa', group: 'painel' },
  { to: '/contacts', icon: Users, label: 'Contatos', group: 'painel' },
  { to: '/blueprints', icon: FolderTree, label: 'Fluxos', group: 'oraculo' },
  { to: '/agents', icon: Bot, label: 'Atendentes', group: 'oraculo' },
  { to: '/runs', icon: Activity, label: 'Execuções', group: 'oraculo' },
  { to: '/integrations', icon: Plug, label: 'Integrações', group: 'config' },
  { to: '/tenant-config', icon: KeyRound, label: 'Variáveis & Segredos', group: 'config' },
  { to: '/settings', icon: SettingsIcon, label: 'Ajustes', group: 'config' },
];

const GROUP_LABELS: Record<string, string> = {
  painel: 'Painel',
  oraculo: 'Oráculo',
  config: 'Configuração',
};

const PAGE_TITLES: Record<string, string> = {
  '/dashboard': 'Visão Geral',
  '/inbox': 'Caixa de Entrada',
  '/contacts': 'Contatos',
  '/blueprints': 'Fluxos',
  '/agents': 'Atendentes — Studio',
  '/runs': 'Execuções',
  '/integrations': 'Integrações',
  '/tenant-config': 'Variáveis & Segredos',
  '/settings': 'Ajustes',
};

export default function Layout() {
  const [collapsed, setCollapsed] = useState(false);
  const location = useLocation();
  const pageTitle = PAGE_TITLES[location.pathname] ?? '';

  // Agrupa items por group preservando ordem.
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
    <div className="flex h-screen w-full bg-sibila-onyx text-sibila-moonlight overflow-hidden font-sans">
      {/* ── Sidebar ─────────────────────────────────────────────────── */}
      <aside
        className={[
          'flex-shrink-0 border-r border-sibila-mist bg-sibila-veil/60 backdrop-blur-sm',
          'transition-[width] duration-300 flex flex-col',
          collapsed ? 'w-[68px]' : 'w-[230px]',
        ].join(' ')}
      >
        {/* Brand */}
        <div className="flex items-center gap-3 h-[60px] px-4 border-b border-sibila-mist flex-shrink-0">
          <span
            className={[
              'w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0',
              'bg-sibila-obsidian border border-sibila-stone/60',
              'text-sibila-ember shadow-glow-ember',
            ].join(' ')}
          >
            <Logo size={18} />
          </span>
          {!collapsed && (
            <div className="flex flex-col leading-none">
              <Wordmark className="text-[17px] text-sibila-moonlight" />
              <span className="text-[9px] text-sibila-amethyst font-semibold tracking-widest-2 uppercase mt-0.5">
                Oráculo
              </span>
            </div>
          )}
        </div>

        {/* Nav */}
        <nav className="flex-1 py-3 px-2 overflow-y-auto">
          {groups.map((g, gi) => (
            <div key={g.id} className={gi > 0 ? 'mt-4' : ''}>
              {!collapsed && (
                <div className="text-[9px] font-semibold tracking-widest-2 text-sibila-smoke uppercase px-3 pb-1.5 pt-1">
                  {GROUP_LABELS[g.id] ?? ''}
                </div>
              )}
              <ul className="space-y-0.5">
                {g.items.map((item) => (
                  <li key={item.to}>
                    <NavLink
                      to={item.to}
                      title={collapsed ? item.label : undefined}
                      className={({ isActive }) =>
                        [
                          'group relative flex items-center gap-2.5 px-3 py-2 rounded-md',
                          'text-[13px] font-medium transition-colors',
                          isActive
                            ? 'bg-sibila-obsidian text-sibila-moonlight'
                            : 'text-sibila-fog hover:bg-sibila-obsidian/50 hover:text-sibila-moonlight',
                          collapsed ? 'justify-center' : '',
                        ].join(' ')
                      }
                    >
                      {({ isActive }) => (
                        <>
                          {isActive && (
                            <span className="absolute left-0 top-1/2 -translate-y-1/2 w-[2px] h-5 bg-sibila-ember rounded-r" />
                          )}
                          <item.icon
                            className={[
                              'w-[15px] h-[15px] flex-shrink-0',
                              isActive
                                ? 'text-sibila-ember'
                                : 'text-sibila-fog group-hover:text-sibila-moonlight',
                            ].join(' ')}
                            strokeWidth={1.8}
                          />
                          {!collapsed && <span>{item.label}</span>}
                        </>
                      )}
                    </NavLink>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </nav>

        {/* Collapse toggle */}
        <div className="px-2 py-2 border-t border-sibila-mist flex-shrink-0">
          <button
            onClick={() => setCollapsed(!collapsed)}
            className="w-full flex items-center justify-center p-1.5 rounded-md text-sibila-smoke hover:text-sibila-moonlight hover:bg-sibila-obsidian/60 transition-colors"
            title={collapsed ? 'Expandir' : 'Recolher'}
          >
            {collapsed ? (
              <PanelLeftOpen className="w-4 h-4" strokeWidth={1.8} />
            ) : (
              <PanelLeftClose className="w-4 h-4" strokeWidth={1.8} />
            )}
          </button>
        </div>
      </aside>

      {/* ── Main ────────────────────────────────────────────────────── */}
      <main className="flex-1 flex flex-col min-w-0 h-full overflow-hidden">
        <header className="h-[60px] border-b border-sibila-mist bg-sibila-veil/40 backdrop-blur-sm px-6 flex items-center justify-between flex-shrink-0">
          <div className="flex items-baseline gap-3">
            <h1 className="font-display text-[18px] text-sibila-moonlight tracking-wide">
              {pageTitle}
            </h1>
          </div>
          <div className="flex items-center gap-3">
            <button
              className="text-[11px] tracking-wider-2 uppercase text-sibila-smoke hover:text-sibila-moonlight transition-colors"
              title="Documentação (em breve)"
            >
              ajuda
            </button>
            <span className="w-px h-5 bg-sibila-mist" />
            <div
              className="w-8 h-8 rounded-full bg-sibila-obsidian border border-sibila-stone/60 flex items-center justify-center text-[10px] font-bold text-sibila-fog"
              title="Conta"
            >
              AD
            </div>
          </div>
        </header>
        <div className="flex-1 overflow-auto bg-sibila-onyx">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
