import { Outlet, NavLink } from 'react-router-dom';
import { Compass, Library, CalendarDays, UserCircle, Flame, Moon, Users, BookOpen } from 'lucide-react';
import { Wordmark } from '../../components/Logo';

const NAV = [
  { to: '/portal/explore', icon: Compass, label: 'Explorar' },
  { to: '/portal/vault', icon: Library, label: 'Meu Cofre' },
  { to: '/portal/schedule', icon: CalendarDays, label: 'Agenda' },
  { to: '/portal/rituals', icon: Flame, label: 'Rituais' },
  { to: '/portal/dreams', icon: Moon, label: 'Sonhos' },
  { to: '/portal/journal', icon: BookOpen, label: 'Diário' },
  { to: '/portal/community', icon: Users, label: 'Comunidade' },
];

export default function PortalLayout() {
  return (
    <div className="min-h-screen bg-black text-white selection:bg-accent-amethyst/30 flex flex-col">
      {/* Top Navbar */}
      <header className="h-16 border-b border-zinc-900 bg-zinc-950/80 backdrop-blur-xl sticky top-0 z-50 flex items-center px-6 justify-between">
        <div className="flex items-center gap-2">
          <Wordmark className="text-xl" />
          <span className="text-xs font-bold uppercase tracking-widest text-accent-amethyst bg-accent-amethyst/10 px-2 py-0.5 rounded-full ml-2">
            Portal
          </span>
        </div>
        
        <nav className="hidden md:flex items-center gap-1">
          {NAV.map(n => (
            <NavLink 
              key={n.to}
              to={n.to} 
              className={({isActive}) => `flex items-center gap-1.5 px-3 py-2 rounded-lg text-xs font-bold transition-all ${isActive ? 'text-white bg-zinc-800' : 'text-zinc-500 hover:text-zinc-300 hover:bg-zinc-900'}`}
            >
              <n.icon className="w-3.5 h-3.5" /> {n.label}
            </NavLink>
          ))}
        </nav>

        <div className="flex items-center gap-4">
          <button className="flex items-center gap-2 text-sm font-bold text-zinc-400 hover:text-white transition-colors">
            <UserCircle className="w-6 h-6" />
            <span className="hidden sm:block">Minha Conta</span>
          </button>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="flex-1 max-w-7xl w-full mx-auto p-6 animate-fade-in">
        <Outlet />
      </main>

      {/* Mobile Bottom Bar */}
      <div className="md:hidden fixed bottom-0 left-0 right-0 h-16 bg-zinc-950 border-t border-zinc-900 flex items-center justify-around z-50 px-1">
        {NAV.slice(0, 5).map(n => (
          <NavLink key={n.to} to={n.to} className={({isActive}) => `flex flex-col items-center gap-0.5 ${isActive ? 'text-accent-amethyst' : 'text-zinc-500'}`}>
            <n.icon className="w-5 h-5" />
            <span className="text-[8px] font-bold uppercase">{n.label}</span>
          </NavLink>
        ))}
      </div>
    </div>
  );
}
