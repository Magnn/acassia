import { useState } from 'react';
import { NavLink, Outlet } from 'react-router-dom';
import { Activity, Bot, FolderTree, KeyRound, LayoutDashboard, MessageSquare, PanelLeftClose, PanelLeftOpen, Plug, Settings, Users } from 'lucide-react';

export default function Layout() {
  const [collapsed, setCollapsed] = useState(false);

  const navItems = [
    { to: '/dashboard', icon: LayoutDashboard, label: 'Dashboard' },
    { to: '/inbox', icon: MessageSquare, label: 'Inbox' },
    { to: '/contacts', icon: Users, label: 'Contatos' },
    { to: '/blueprints', icon: FolderTree, label: 'Flow Builder' },
    { to: '/agents', icon: Bot, label: 'Agent Studio' },
    { to: '/runs', icon: Activity, label: 'Execuções' },
    { to: '/integrations', icon: Plug, label: 'Integrações' },
    { to: '/tenant-config', icon: KeyRound, label: 'Variáveis & Segredos' },
    { to: '/settings', icon: Settings, label: 'Configurações' },
  ];

  return (
    <div className="flex h-screen w-full bg-cigana-bg text-slate-100 overflow-hidden font-sans">
      {/* Sidebar */}
      <aside
        className={`flex-shrink-0 border-r border-cigana-border bg-cigana-surface transition-all duration-300 flex flex-col ${
          collapsed ? 'w-[72px]' : 'w-[240px]'
        }`}
      >
        <div className="flex items-center gap-3 h-[58px] px-4 border-b border-cigana-border flex-shrink-0">
          <div className="w-8 h-8 bg-cigana-purple rounded-lg flex items-center justify-center font-bold text-white shadow-[0_0_16px_rgba(124,58,237,0.14)] flex-shrink-0">
            C
          </div>
          {!collapsed && (
            <div className="flex flex-col">
              <span className="font-bold text-[15px] leading-tight">Cigana</span>
              <span className="text-[10px] text-cigana-purple font-semibold tracking-widest uppercase">SaaS</span>
            </div>
          )}
        </div>

        <nav className="flex-1 py-4 px-2 space-y-1 overflow-y-auto">
          {!collapsed && (
            <div className="text-[10px] font-bold tracking-widest text-slate-500 uppercase px-3 pb-2 pt-2">
              Menu Principal
            </div>
          )}
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                  isActive
                    ? 'bg-cigana-purple/10 text-cigana-purple border border-cigana-purple/30'
                    : 'text-slate-400 hover:bg-slate-800/50 hover:text-slate-200 border border-transparent'
                } ${collapsed ? 'justify-center' : ''}`
              }
              title={collapsed ? item.label : undefined}
            >
              <item.icon className="w-[18px] h-[18px] flex-shrink-0" />
              {!collapsed && <span>{item.label}</span>}
            </NavLink>
          ))}
        </nav>

        <div className="p-3 border-t border-cigana-border flex-shrink-0 flex justify-center">
          <button
            onClick={() => setCollapsed(!collapsed)}
            className="w-full flex items-center justify-center p-2 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-slate-800/50 transition-colors"
            title={collapsed ? 'Expandir' : 'Recolher'}
          >
            {collapsed ? <PanelLeftOpen className="w-5 h-5" /> : <PanelLeftClose className="w-5 h-5" />}
          </button>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 flex flex-col min-w-0 h-full overflow-hidden">
        <header className="h-[58px] border-b border-cigana-border bg-cigana-surface px-6 flex items-center justify-between flex-shrink-0">
          <div className="flex items-center gap-4">
            <h1 className="font-semibold text-sm">Visão Geral</h1>
          </div>
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-full bg-slate-800 border border-cigana-border flex items-center justify-center text-xs font-bold text-slate-400">
              AD
            </div>
          </div>
        </header>
        <div className="flex-1 overflow-auto bg-cigana-bg">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
