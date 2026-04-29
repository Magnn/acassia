import { NavLink, Outlet } from 'react-router-dom';
import {
  ClipboardList,
  Globe2,
  MessageSquareText,
  ShieldCheck,
  Smartphone,
  Sparkles,
  Tag,
  TimerReset,
  User,
  Variable,
} from 'lucide-react';

interface SubItem {
  to: string;
  Icon: typeof Smartphone;
  label: string;
  hint?: string;
}

const SUB_ITEMS: SubItem[] = [
  { to: '/settings/devices', Icon: Smartphone, label: 'Dispositivos', hint: "WhatsApp's conectados" },
  { to: '/settings/account', Icon: User, label: 'Minha Conta', hint: 'Configurar minha conta' },
  { to: '/settings/security', Icon: ShieldCheck, label: 'Segurança', hint: '2FA + sessões' },
  { to: '/settings/labels', Icon: Tag, label: 'Etiquetas', hint: 'Configurar etiquetas' },
  { to: '/settings/fields', Icon: Variable, label: 'Campos', hint: 'Campos personalizados' },
  { to: '/settings/timezone', Icon: Globe2, label: 'Fuso Horário', hint: 'Configurar fuso horário' },
  { to: '/settings/quick-replies', Icon: Sparkles, label: 'Respostas Rápidas', hint: 'Mensagens rápidas (chat)' },
  { to: '/settings/templates', Icon: MessageSquareText, label: 'Templates WhatsApp', hint: 'Modelos de mensagens' },
  { to: '/settings/recovery', Icon: TimerReset, label: 'Recuperação', hint: 'Cadência de reengajamento' },
  { to: '/settings/logs', Icon: ClipboardList, label: 'Logs', hint: 'Logs do sistema' },
];

export default function SettingsLayout() {
  return (
    <div className="flex h-full bg-bg-primary overflow-hidden">
      {/* Submenu lateral interno */}
      <aside className="w-[320px] flex-shrink-0 border-r border-border bg-bg-sidebar overflow-y-auto">
        <div className="px-8 py-8">
          <h2 className="text-2xl font-black tracking-tight text-primary">Ajustes</h2>
          <p className="text-[11px] text-secondary font-bold uppercase tracking-widest mt-2 opacity-60">
            Workspace & Conexões
          </p>
        </div>
        <nav className="px-4 pb-8">
          <ul className="space-y-1">
            {SUB_ITEMS.map((item) => (
              <li key={item.to}>
                <NavLink
                  to={item.to}
                  className={({ isActive }) =>
                    [
                      'group flex items-center gap-4 px-4 py-3.5 rounded-2xl transition-all duration-200',
                      isActive
                        ? 'bg-bg-surface text-primary shadow-sm border border-border/50'
                        : 'text-secondary hover:bg-bg-surface/50 hover:text-primary',
                    ].join(' ')
                  }
                >
                  {({ isActive }) => (
                    <>
                      <div
                        className={[
                          'w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0 transition-all shadow-sm border',
                          isActive
                            ? 'bg-accent-amethyst/10 border-accent-amethyst/20 text-accent-amethyst'
                            : 'bg-bg-primary border-border/50 text-secondary group-hover:text-primary group-hover:border-border',
                        ].join(' ')}
                      >
                        <item.Icon className="w-5 h-5" strokeWidth={2} />
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="text-sm font-bold leading-none">
                          {item.label}
                        </div>
                        {item.hint && (
                          <div className="text-[10px] text-secondary font-medium mt-1 truncate opacity-70">
                            {item.hint}
                          </div>
                        )}
                      </div>
                    </>
                  )}
                </NavLink>
              </li>
            ))}
          </ul>
        </nav>
      </aside>

      {/* Área de conteúdo */}
      <section className="flex-1 min-w-0 overflow-auto bg-bg-primary/50 backdrop-blur-sm">
        <div className="h-full w-full">
           <Outlet />
        </div>
      </section>
    </div>
  );
}
