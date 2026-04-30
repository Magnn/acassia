import { useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import {
  Search, Command, ArrowRight, MessageSquare, Bot, FolderTree,
  CreditCard, Settings, Activity, Sparkles, BookOpen, Plug,
  ShieldCheck, Library, CalendarDays, Volume2, Wand2, Compass, Store,
} from 'lucide-react';
import { inboxApi } from '../api/inbox';
import { blueprintsApi } from '../api/blueprints';

interface CommandItem {
  id: string;
  label: string;
  group: 'navegar' | 'criar' | 'configurar' | 'leads' | 'fluxos';
  Icon: typeof Search;
  to?: string;
  action?: () => void;
  keywords?: string;
  shortcut?: string;
}

const STATIC_NAV: CommandItem[] = [
  { id: 'nav-dashboard', label: 'Visão Geral', group: 'navegar', Icon: Activity, to: '/dashboard', keywords: 'home painel inicio' },
  { id: 'nav-inbox', label: 'Conversas / Inbox', group: 'navegar', Icon: MessageSquare, to: '/leads', keywords: 'leads chat inbox' },
  { id: 'nav-blueprints', label: 'Fluxos', group: 'navegar', Icon: FolderTree, to: '/blueprints', keywords: 'flow funnel blueprint' },
  { id: 'nav-templates', label: 'Templates', group: 'navegar', Icon: FolderTree, to: '/templates', keywords: 'kits modelos' },
  { id: 'nav-marketplace', label: 'Marketplace', group: 'navegar', Icon: Store, to: '/marketplace', keywords: 'comprar vender flow' },
  { id: 'nav-tarot', label: 'Tarot Virtual', group: 'navegar', Icon: Wand2, to: '/tarot', keywords: 'cartas tiragem' },
  { id: 'nav-pix', label: 'Pix QR', group: 'navegar', Icon: CreditCard, to: '/pix', keywords: 'pagamento pix qr' },
  { id: 'nav-voice', label: 'Voice Cloning', group: 'navegar', Icon: Volume2, to: '/voice', keywords: 'audio voz clonada' },
  { id: 'nav-audio-lib', label: 'Biblioteca de Áudios', group: 'navegar', Icon: Library, to: '/audio-library', keywords: 'audios pre gravados' },
  { id: 'nav-coach', label: 'Cigana Coach', group: 'navegar', Icon: Bot, to: '/coach', keywords: 'ia coach review' },
  { id: 'nav-affiliate', label: 'Afiliados', group: 'navegar', Icon: CreditCard, to: '/affiliate', keywords: 'indicacao referral' },
  { id: 'nav-lunar', label: 'Lunar', group: 'navegar', Icon: Sparkles, to: '/lunar', keywords: 'lua fase' },
  { id: 'nav-spiritual', label: 'Perfil Espiritual', group: 'navegar', Icon: Compass, to: '/spiritual', keywords: 'mapa astral numerologia signo' },
  { id: 'nav-calendar', label: 'Calendário Espiritual', group: 'navegar', Icon: CalendarDays, to: '/calendar', keywords: 'datas rituais' },
  { id: 'nav-horoscope', label: 'Horóscopo Diário', group: 'navegar', Icon: Sparkles, to: '/horoscope', keywords: 'horoscopo signo daily' },
  { id: 'nav-funnel', label: 'Analytics — Funnel', group: 'navegar', Icon: Activity, to: '/analytics/funnel', keywords: 'metrics funnel conversion' },
  { id: 'nav-recovery', label: 'Analytics — Recuperação', group: 'navegar', Icon: Activity, to: '/analytics/recovery', keywords: 'recovery winback' },
  { id: 'nav-runs', label: 'Execuções', group: 'navegar', Icon: Activity, to: '/runs', keywords: 'logs run debug' },
  { id: 'nav-agents', label: 'Atendentes', group: 'navegar', Icon: Bot, to: '/agents', keywords: 'studio agente persona' },
  { id: 'nav-integrations', label: 'Integrações', group: 'configurar', Icon: Plug, to: '/integrations', keywords: 'whatsapp webhook conectar' },
  { id: 'nav-tenant-config', label: 'Variáveis & Segredos', group: 'configurar', Icon: Settings, to: '/tenant-config', keywords: 'env config secret' },
  { id: 'nav-billing', label: 'Assinatura / Billing', group: 'configurar', Icon: CreditCard, to: '/billing', keywords: 'plano pagamento' },
  { id: 'nav-settings-devices', label: 'Dispositivos', group: 'configurar', Icon: Settings, to: '/settings/devices', keywords: 'sessoes celular dispositivo' },
  { id: 'nav-settings-security', label: 'Segurança', group: 'configurar', Icon: ShieldCheck, to: '/settings/security', keywords: '2fa senha ssh' },
  { id: 'nav-settings-privacy', label: 'Privacidade (LGPD)', group: 'configurar', Icon: ShieldCheck, to: '/settings/privacy', keywords: 'lgpd privacidade dados' },
  { id: 'nav-onboarding', label: 'Onboarding wizard', group: 'configurar', Icon: BookOpen, to: '/onboarding', keywords: 'tutorial primeiros passos' },
];


function fuzzyScore(haystack: string, needle: string): number {
  if (!needle) return 0;
  const h = haystack.toLowerCase();
  const n = needle.toLowerCase();
  if (h === n) return 1000;
  if (h.startsWith(n)) return 800;
  if (h.includes(n)) return 500;
  // letters in order
  let hi = 0;
  for (const ch of n) {
    const next = h.indexOf(ch, hi);
    if (next < 0) return 0;
    hi = next + 1;
  }
  return 100 + Math.max(0, 50 - (hi - n.length));
}


export default function CommandPalette({
  open, onClose,
}: {
  open: boolean;
  onClose: () => void;
}) {
  const navigate = useNavigate();
  const [query, setQuery] = useState('');
  const [activeIdx, setActiveIdx] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (open) {
      setQuery('');
      setActiveIdx(0);
      setTimeout(() => inputRef.current?.focus(), 30);
    }
  }, [open]);

  // Lazy queries só rodam quando palette aberto e query > 1 char
  const enabledLeads = open && query.length >= 2;
  const { data: leadsData } = useQuery({
    queryKey: ['cmdk-leads', query],
    queryFn: () => inboxApi.getLeads({ search: query, limit: 5 }),
    enabled: enabledLeads,
    staleTime: 60_000,
  });

  const enabledFlows = open && query.length >= 1;
  const { data: flowsData } = useQuery({
    queryKey: ['cmdk-flows'],
    queryFn: () => blueprintsApi.list(),
    enabled: enabledFlows,
    staleTime: 5 * 60_000,
  });

  const items = useMemo<CommandItem[]>(() => {
    const all: CommandItem[] = [...STATIC_NAV];

    // Add lead matches dynamically
    (leadsData?.items ?? []).forEach((l) => {
      all.push({
        id: `lead-${l.id}`,
        label: l.nome || l.telefone,
        group: 'leads',
        Icon: MessageSquare,
        action: () => navigate(`/leads?lead=${l.id}`),
        keywords: `${l.telefone} lead`,
      });
    });

    // Add flow matches
    (flowsData ?? []).slice(0, 8).forEach((bp) => {
      all.push({
        id: `flow-${bp.id}`,
        label: bp.title,
        group: 'fluxos',
        Icon: FolderTree,
        action: () => navigate(`/flows/${bp.id}`),
        keywords: `${bp.slug} blueprint flow editar`,
      });
    });

    if (!query.trim()) return all;

    return all
      .map((it) => ({
        item: it,
        score: Math.max(
          fuzzyScore(it.label, query),
          fuzzyScore(it.keywords || '', query),
        ),
      }))
      .filter((x) => x.score > 0)
      .sort((a, b) => b.score - a.score)
      .map((x) => x.item);
  }, [query, leadsData, flowsData, navigate]);

  // Group items
  const grouped = useMemo(() => {
    const groups: Record<string, CommandItem[]> = {
      navegar: [], criar: [], configurar: [], leads: [], fluxos: [],
    };
    items.slice(0, 50).forEach((it) => groups[it.group].push(it));
    return groups;
  }, [items]);

  const flatVisible = useMemo(() => items.slice(0, 50), [items]);

  // Keyboard nav
  useEffect(() => {
    if (!open) return;
    function onKey(e: KeyboardEvent) {
      if (e.key === 'Escape') {
        e.preventDefault();
        onClose();
        return;
      }
      if (e.key === 'ArrowDown') {
        e.preventDefault();
        setActiveIdx((i) => Math.min(flatVisible.length - 1, i + 1));
        return;
      }
      if (e.key === 'ArrowUp') {
        e.preventDefault();
        setActiveIdx((i) => Math.max(0, i - 1));
        return;
      }
      if (e.key === 'Enter') {
        e.preventDefault();
        const sel = flatVisible[activeIdx];
        if (sel) execute(sel);
      }
    }
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, flatVisible, activeIdx]);

  const execute = (item: CommandItem) => {
    onClose();
    setTimeout(() => {
      if (item.to) navigate(item.to);
      else if (item.action) item.action();
    }, 50);
  };

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-[100] bg-black/60 backdrop-blur-sm flex items-start justify-center pt-[15vh]"
      onClick={onClose}
    >
      <div
        className="w-full max-w-xl bg-bg-surface border border-border rounded-2xl shadow-2xl overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center gap-3 px-4 py-3 border-b border-border">
          <Search className="w-4 h-4 text-secondary" />
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={(e) => { setQuery(e.target.value); setActiveIdx(0); }}
            placeholder="Buscar ações, leads, fluxos…"
            className="flex-1 bg-transparent outline-none text-sm"
          />
          <span className="text-[9px] uppercase tracking-widest text-secondary font-bold flex items-center gap-1">
            <Command className="w-3 h-3" />K
          </span>
        </div>

        <div className="max-h-[55vh] overflow-y-auto">
          {flatVisible.length === 0 ? (
            <div className="px-6 py-12 text-center text-secondary text-sm">
              Nenhum resultado pra "{query}".
            </div>
          ) : (
            (['navegar', 'leads', 'fluxos', 'configurar', 'criar'] as const).map((g) => {
              const list = grouped[g];
              if (list.length === 0) return null;
              return (
                <div key={g}>
                  <div className="px-4 pt-3 pb-1 text-[9px] uppercase tracking-widest text-secondary font-black">
                    {g}
                  </div>
                  {list.map((it) => {
                    const idx = flatVisible.indexOf(it);
                    const active = idx === activeIdx;
                    const Icon = it.Icon;
                    return (
                      <button
                        key={it.id}
                        onClick={() => execute(it)}
                        onMouseEnter={() => setActiveIdx(idx)}
                        className={`w-full px-4 py-2 flex items-center gap-3 text-left transition-all ${
                          active ? 'bg-accent-amethyst/10 border-l-2 border-accent-amethyst' : 'border-l-2 border-transparent'
                        }`}
                      >
                        <Icon className="w-3.5 h-3.5 text-secondary flex-shrink-0" />
                        <span className="text-sm flex-1 truncate">{it.label}</span>
                        {active && <ArrowRight className="w-3 h-3 text-accent-amethyst" />}
                      </button>
                    );
                  })}
                </div>
              );
            })
          )}
        </div>

        <div className="px-4 py-2 border-t border-border bg-bg-primary/50 flex items-center justify-between text-[9px] uppercase tracking-widest text-secondary font-bold">
          <span className="flex items-center gap-3">
            <span>↑↓ navegar</span>
            <span>↵ executar</span>
            <span>Esc fechar</span>
          </span>
          <span>{flatVisible.length} resultados</span>
        </div>
      </div>
    </div>
  );
}


export function useCmdK() {
  const [open, setOpen] = useState(false);

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        setOpen((v) => !v);
      }
    }
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, []);

  return { open, setOpen };
}
