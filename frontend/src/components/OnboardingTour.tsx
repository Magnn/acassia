import { useEffect, useMemo, useState } from 'react';
import { useLocation } from 'react-router-dom';
import { ArrowRight, X, Sparkles } from 'lucide-react';

interface TourStep {
  id: string;
  title: string;
  body: string;
  /** Selector CSS pra elemento alvo. Tour faz spotlight + tooltip ao lado. */
  target?: string;
  /** Posicao do tooltip relativa ao target. */
  position?: 'top' | 'bottom' | 'left' | 'right' | 'center';
  /** Pagina onde este passo aparece. Se nao casar, pula. */
  route_match?: RegExp;
}

const FIRST_LOGIN_TOUR: TourStep[] = [
  {
    id: 'welcome',
    title: 'Bem-vinda ao Acássia ✨',
    body: 'Esse é seu painel — vou te guiar em 5 passos rápidos. Pode pular a qualquer momento.',
    position: 'center',
  },
  {
    id: 'sidebar',
    title: 'Navegação',
    body: 'No menu lateral você acessa Conversas, Fluxos, Tarot, Voice, e tudo mais. Use Ctrl+K (ou Cmd+K) pra busca rápida em qualquer lugar.',
    target: 'aside, nav, [data-tour="sidebar"]',
    position: 'right',
  },
  {
    id: 'inbox',
    title: 'Inbox',
    body: 'Aqui rolam todas as conversas com seus leads em tempo real. Filtros de score (Hot/Warm/Cold) e tema espiritual no topo. Atalhos: j/k pra navegar, / pra buscar.',
    route_match: /\/leads/,
    position: 'center',
  },
  {
    id: 'flows',
    title: 'Fluxos',
    body: 'Crie e edite seus funis no /blueprints. Use templates prontos no /templates pra começar em 1 clique.',
    position: 'center',
  },
  {
    id: 'integrations',
    title: 'Conectar WhatsApp',
    body: 'Pra deixar o sistema vivo, vá em Integrações e cole sua credencial Meta Cloud API. A gente valida na hora.',
    position: 'center',
  },
];

const TOURS_DONE_KEY = 'acassia.tours.done';

function tourCompleted(tourId: string): boolean {
  try {
    const raw = localStorage.getItem(TOURS_DONE_KEY) || '[]';
    const done: string[] = JSON.parse(raw);
    return done.includes(tourId);
  } catch {
    return false;
  }
}

function markTourDone(tourId: string): void {
  try {
    const raw = localStorage.getItem(TOURS_DONE_KEY) || '[]';
    const done: string[] = JSON.parse(raw);
    if (!done.includes(tourId)) {
      done.push(tourId);
      localStorage.setItem(TOURS_DONE_KEY, JSON.stringify(done));
    }
  } catch {
    // ignora
  }
}

export default function OnboardingTour() {
  const location = useLocation();
  const [active, setActive] = useState(false);
  const [stepIdx, setStepIdx] = useState(0);
  const [targetRect, setTargetRect] = useState<DOMRect | null>(null);

  // Auto-start first-login tour
  useEffect(() => {
    if (tourCompleted('first_login')) return;
    // Delay pequeno pra layout assentar
    const t = setTimeout(() => setActive(true), 1200);
    return () => clearTimeout(t);
  }, []);

  const visibleSteps = useMemo(
    () =>
      FIRST_LOGIN_TOUR.filter((s) => !s.route_match || s.route_match.test(location.pathname)),
    [location.pathname],
  );

  const currentStep = visibleSteps[stepIdx];

  // Calcula posicao do alvo
  useEffect(() => {
    if (!active || !currentStep?.target) {
      setTargetRect(null);
      return;
    }
    const el = document.querySelector(currentStep.target);
    if (el instanceof HTMLElement) {
      setTargetRect(el.getBoundingClientRect());
      el.scrollIntoView({ behavior: 'smooth', block: 'center' });
    } else {
      setTargetRect(null);
    }
  }, [active, currentStep]);

  if (!active || !currentStep) return null;

  const isLast = stepIdx === visibleSteps.length - 1;

  const next = () => {
    if (isLast) finish();
    else setStepIdx((i) => i + 1);
  };
  const skip = () => finish();
  const finish = () => {
    markTourDone('first_login');
    setActive(false);
  };

  // Tooltip positioning
  const tooltipStyle: React.CSSProperties = {};
  if (targetRect && currentStep.position && currentStep.position !== 'center') {
    const padding = 16;
    if (currentStep.position === 'right') {
      tooltipStyle.top = `${targetRect.top + targetRect.height / 2 - 100}px`;
      tooltipStyle.left = `${targetRect.right + padding}px`;
    } else if (currentStep.position === 'left') {
      tooltipStyle.top = `${targetRect.top + targetRect.height / 2 - 100}px`;
      tooltipStyle.right = `${window.innerWidth - targetRect.left + padding}px`;
    } else if (currentStep.position === 'bottom') {
      tooltipStyle.top = `${targetRect.bottom + padding}px`;
      tooltipStyle.left = `${targetRect.left + targetRect.width / 2 - 200}px`;
    } else if (currentStep.position === 'top') {
      tooltipStyle.bottom = `${window.innerHeight - targetRect.top + padding}px`;
      tooltipStyle.left = `${targetRect.left + targetRect.width / 2 - 200}px`;
    }
  }

  const isCenter = !targetRect || currentStep.position === 'center';

  return (
    <>
      {/* Overlay com hole no target */}
      <div className="fixed inset-0 z-[200] pointer-events-auto" onClick={skip}>
        <div className="absolute inset-0 bg-black/70" />
        {targetRect && (
          <div
            className="absolute border-2 border-accent-amethyst rounded-lg shadow-[0_0_30px_rgba(155,107,222,0.6)]"
            style={{
              top: targetRect.top - 4,
              left: targetRect.left - 4,
              width: targetRect.width + 8,
              height: targetRect.height + 8,
              pointerEvents: 'none',
            }}
          />
        )}
      </div>

      {/* Tooltip */}
      <div
        className={`fixed z-[201] bg-bg-surface border border-accent-amethyst/40 rounded-2xl shadow-2xl p-5 w-[400px] ${
          isCenter ? 'left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2' : ''
        }`}
        style={isCenter ? undefined : tooltipStyle}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-start justify-between mb-3">
          <div className="flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-accent-amethyst" />
            <span className="text-[10px] font-black uppercase tracking-widest text-secondary">
              Passo {stepIdx + 1} de {visibleSteps.length}
            </span>
          </div>
          <button
            onClick={skip}
            className="text-secondary hover:text-primary"
            title="Pular tour"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
        <h3 className="text-lg font-black tracking-tight mb-2">{currentStep.title}</h3>
        <p className="text-sm text-secondary leading-relaxed mb-4">{currentStep.body}</p>
        <div className="flex items-center justify-between gap-3">
          <button
            onClick={skip}
            className="text-[11px] font-bold text-secondary hover:text-primary"
          >
            Pular tour
          </button>
          <button
            onClick={next}
            className="px-4 py-2 bg-accent-amethyst hover:bg-accent-amethyst/90 text-white rounded-xl text-xs font-black uppercase tracking-widest flex items-center gap-2"
          >
            {isLast ? 'Concluir' : 'Próximo'}
            <ArrowRight className="w-3 h-3" />
          </button>
        </div>
      </div>
    </>
  );
}
