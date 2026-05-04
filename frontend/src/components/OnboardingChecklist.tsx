import { useState, useEffect } from 'react';
import { CheckCircle2, Circle, ChevronRight, X, Sparkles } from 'lucide-react';
import { useOnboarding } from '../hooks/useOnboarding';

const STORAGE_KEY = 'meumisterio_onboarding_dismissed_v1';

export default function OnboardingChecklist() {
  const { data: progress } = useOnboarding();
  const [dismissed, setDismissed] = useState(false);
  const [collapsed, setCollapsed] = useState(true);

  useEffect(() => {
    if (localStorage.getItem(STORAGE_KEY) === '1') setDismissed(true);
  }, []);

  if (!progress) return null;
  if (progress.all_done) return null;
  if (dismissed) return null;

  const handleDismiss = () => {
    localStorage.setItem(STORAGE_KEY, '1');
    setDismissed(true);
  };

  return (
    <div className="fixed bottom-6 right-6 z-30 w-[340px] bg-bg-surface border border-accent-amethyst/30 rounded-3xl shadow-2xl overflow-hidden">
      {/* Header sempre visível */}
      <button
        onClick={() => setCollapsed((c) => !c)}
        className="w-full p-4 flex items-center justify-between hover:bg-accent-amethyst/5 transition-all"
      >
        <div className="flex items-center gap-3 min-w-0">
          <div className="w-9 h-9 rounded-xl bg-accent-amethyst/10 flex items-center justify-center flex-shrink-0">
            <Sparkles className="w-4 h-4 text-accent-amethyst" />
          </div>
          <div className="text-left min-w-0">
            <div className="text-xs font-black uppercase tracking-widest text-accent-amethyst">
              Progresso de Setup
            </div>
            <div className="text-sm font-black mt-0.5">
              {progress.completed_count}/{progress.total} completos · {progress.pct}%
            </div>
          </div>
        </div>
        <div className="flex items-center gap-1">
          <ChevronRight
            className={`w-4 h-4 text-secondary transition-transform ${collapsed ? '' : 'rotate-90'}`}
          />
        </div>
      </button>

      {/* Progress bar */}
      <div className="h-1 bg-bg-primary">
        <div
          className="h-full bg-gradient-to-r from-accent-amethyst to-purple-400 transition-all"
          style={{ width: `${progress.pct}%` }}
        />
      </div>

      {/* Lista colapsável */}
      {!collapsed && (
        <div className="p-3 space-y-1 max-h-[400px] overflow-y-auto">
          {progress.milestones.map((m) => (
            <div
              key={m.key}
              className={`flex items-start gap-3 p-3 rounded-xl ${
                m.completed
                  ? 'bg-emerald-500/5 border border-emerald-500/20'
                  : progress.next_suggested?.key === m.key
                    ? 'bg-accent-amethyst/10 border border-accent-amethyst/30'
                    : 'bg-bg-primary border border-transparent'
              }`}
            >
              {m.completed ? (
                <CheckCircle2 className="w-5 h-5 text-emerald-500 flex-shrink-0 mt-0.5" />
              ) : (
                <Circle className="w-5 h-5 text-secondary/40 flex-shrink-0 mt-0.5" />
              )}
              <div className="flex-1 min-w-0">
                <div
                  className={`text-xs font-black ${
                    m.completed ? 'text-emerald-500' : 'text-primary'
                  }`}
                >
                  {m.label}
                </div>
                <p className="text-[10px] text-secondary mt-0.5 leading-snug">
                  {m.description}
                </p>
              </div>
            </div>
          ))}
          <button
            onClick={handleDismiss}
            className="w-full flex items-center justify-center gap-1 mt-2 py-2 text-[10px] text-secondary/60 hover:text-secondary uppercase tracking-widest font-black"
          >
            <X className="w-3 h-3" />
            Não mostrar mais
          </button>
        </div>
      )}
    </div>
  );
}
