import { NavLink, Outlet } from 'react-router-dom';
import {
  ClipboardList,
  Globe2,
  MessageSquareText,
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
    <div className="flex h-full bg-sibila-onyx">
      {/* Submenu lateral interno */}
      <aside className="w-[280px] flex-shrink-0 border-r border-sibila-mist bg-sibila-veil/40 overflow-y-auto">
        <div className="px-5 py-5 border-b border-sibila-mist">
          <h2 className="font-display text-xl text-sibila-moonlight">Configurações</h2>
          <p className="text-[11px] text-sibila-smoke mt-0.5">
            Workspace e conexões deste tenant.
          </p>
        </div>
        <ul className="py-2 px-2">
          {SUB_ITEMS.map((item) => (
            <li key={item.to}>
              <NavLink
                to={item.to}
                className={({ isActive }) =>
                  [
                    'group flex items-start gap-3 px-3 py-2.5 rounded-md transition-colors',
                    isActive
                      ? 'bg-sibila-obsidian text-sibila-moonlight'
                      : 'text-sibila-fog hover:bg-sibila-obsidian/60 hover:text-sibila-moonlight',
                  ].join(' ')
                }
              >
                {({ isActive }) => (
                  <>
                    <span
                      className={[
                        'w-9 h-9 rounded-lg flex items-center justify-center flex-shrink-0 transition-colors',
                        isActive
                          ? 'bg-sibila-amethyst/20 text-sibila-amethyst'
                          : 'bg-sibila-obsidian text-sibila-fog group-hover:text-sibila-moonlight',
                      ].join(' ')}
                    >
                      <item.Icon className="w-4 h-4" strokeWidth={1.8} />
                    </span>
                    <div className="flex-1 min-w-0 mt-0.5">
                      <div className="text-sm font-medium leading-tight">
                        {item.label}
                      </div>
                      {item.hint && (
                        <div className="text-[11px] text-sibila-smoke leading-tight mt-0.5">
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
      </aside>

      {/* Área de conteúdo */}
      <section className="flex-1 min-w-0 overflow-auto">
        <Outlet />
      </section>
    </div>
  );
}
