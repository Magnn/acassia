import { useNavigate } from 'react-router-dom';
import { ArrowRight } from 'lucide-react';

/**
 * Cross-sell suggestions between features.
 * Place at the bottom of any module to drive users to related features.
 */
const CROSS_SELLS: Record<string, { emoji: string; title: string; desc: string; path: string }[]> = {
  ritual: [
    { emoji: '📔', title: 'Registre no Diário', desc: 'Como você se sentiu depois do ritual?', path: '/journal' },
    { emoji: '🔮', title: 'Leitura Multi-Modal', desc: 'Descubra o que as cartas dizem sobre sua energia.', path: '/reading' },
  ],
  dream: [
    { emoji: '🔥', title: 'Ritual de Integração', desc: 'Ritualize o que o sonho revelou.', path: '/rituals' },
    { emoji: '🎯', title: 'Vision Board', desc: 'Manifeste o que o inconsciente mostrou.', path: '/vision-board' },
  ],
  journal: [
    { emoji: '🌙', title: 'Diário de Sonhos', desc: 'O que seus sonhos estão dizendo?', path: '/dreams' },
    { emoji: '🔥', title: 'Ritual do Momento', desc: 'Transforme reflexão em ação sagrada.', path: '/rituals' },
  ],
  reading: [
    { emoji: '📔', title: 'Refletir no Diário', desc: 'Anote os insights da leitura.', path: '/journal' },
    { emoji: '👥', title: 'Compartilhar na Comunidade', desc: 'Discuta com sua tribo cósmica.', path: '/community' },
  ],
  visionboard: [
    { emoji: '🔥', title: 'Ritual de Manifestação', desc: 'Potencialize com um ritual focado.', path: '/rituals' },
    { emoji: '🔮', title: 'O que as cartas dizem?', desc: 'Valide seu caminho com uma leitura.', path: '/reading' },
  ],
  community: [
    { emoji: '🔮', title: 'Peça ao Oráculo', desc: 'Consulta privada com a IA.', path: '/reading' },
    { emoji: '📔', title: 'Escreva no Diário', desc: 'Processe o que discutiu.', path: '/journal' },
  ],
};

export function CrossSell({ source }: { source: string }) {
  const navigate = useNavigate();
  const suggestions = CROSS_SELLS[source] ?? [];

  if (suggestions.length === 0) return null;

  return (
    <div className="mt-8 pt-6 border-t border-border space-y-3">
      <h4 className="text-[10px] font-black uppercase tracking-widest text-secondary">Continue sua jornada</h4>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
        {suggestions.map(s => (
          <button key={s.path} onClick={() => navigate(s.path)}
            className="flex items-center gap-3 p-4 bg-bg-surface border border-border rounded-xl hover:border-accent-amethyst/30 transition-all text-left group">
            <span className="text-2xl">{s.emoji}</span>
            <div className="flex-1 min-w-0">
              <div className="font-bold text-sm group-hover:text-accent-amethyst transition-colors">{s.title}</div>
              <div className="text-[11px] text-secondary truncate">{s.desc}</div>
            </div>
            <ArrowRight className="w-4 h-4 text-secondary group-hover:text-accent-amethyst transition-colors" />
          </button>
        ))}
      </div>
    </div>
  );
}
