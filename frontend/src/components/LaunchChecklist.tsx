import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { CheckCircle2, Circle, ArrowRight, Sparkles, ChevronDown, ChevronUp } from 'lucide-react';
import { onboardingApi } from '../api/onboarding';

export default function LaunchChecklist() {
  const [collapsed, setCollapsed] = useState(false);
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['launch-readiness'],
    queryFn: onboardingApi.getReadiness,
    staleTime: 15_000,
    refetchInterval: 30_000,
  });

  if (isLoading) {
    return (
      <div className="bg-bg-surface border border-border rounded-3xl p-5 animate-pulse text-xs text-secondary flex items-center gap-2">
        <Sparkles className="w-4 h-4 text-indigo-400" />
        <span>Verificando checklist de prontidão do sistema...</span>
      </div>
    );
  }

  if (error || !data) {
    return null;
  }

  const percent = data.total > 0 ? Math.round((data.completed_count / data.total) * 100) : 0;
  const isComplete = data.checks_complete;

  return (
    <section
      aria-labelledby="launch-title"
      className={`relative overflow-hidden rounded-3xl border transition-all ${
        isComplete
          ? 'bg-bg-surface/80 border-border/80'
          : 'bg-gradient-to-br from-indigo-950/20 via-bg-surface to-bg-surface border-indigo-500/30 shadow-lg shadow-indigo-500/5'
      }`}
    >
      <div className="p-6">
        <div className="flex items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className={`w-10 h-10 rounded-2xl flex items-center justify-center shrink-0 shadow-sm ${
              isComplete
                ? 'bg-emerald-500/10 border border-emerald-500/20 text-emerald-400'
                : 'bg-indigo-500/10 border border-indigo-500/20 text-indigo-400'
            }`}>
              {isComplete ? <CheckCircle2 className="w-5 h-5" /> : <Sparkles className="w-5 h-5" />}
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 id="launch-title" className="text-base font-bold text-primary">
                  {isComplete ? 'Operação Pronta para Vendas' : 'Checklist de Ativação'}
                </h3>
                <span className={`px-2 py-0.5 rounded-full text-[10px] font-mono font-bold ${
                  isComplete
                    ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/30'
                    : 'bg-indigo-500/10 text-indigo-400 border border-indigo-500/30'
                }`}>
                  {percent}% Concluído
                </span>
              </div>
              <p className="text-xs text-secondary mt-0.5">
                {data.completed_count} de {data.total} etapas finalizadas.
                {isComplete
                  ? ' Seu número WhatsApp oficial está pronto e recebendo leads.'
                  : ' Complete as etapas pendentes para garantir o atendimento automatizado.'}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {data.next_step && (
              <Link
                to={data.next_step.href}
                className="hidden sm:inline-flex items-center gap-1.5 px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-bold transition-all shadow-sm shadow-indigo-600/20"
              >
                <span>Continuar: {data.next_step.label}</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </Link>
            )}
            <button
              onClick={() => setCollapsed(!collapsed)}
              className="p-1.5 rounded-xl hover:bg-bg-primary text-secondary hover:text-primary transition-colors"
              title={collapsed ? 'Expandir' : 'Recolher'}
            >
              {collapsed ? <ChevronDown className="w-4 h-4" /> : <ChevronUp className="w-4 h-4" />}
            </button>
          </div>
        </div>

        {/* Progress bar */}
        <div className="w-full h-1.5 bg-bg-primary rounded-full overflow-hidden mt-4 border border-border/50">
          <div
            className={`h-full transition-all duration-700 ease-out rounded-full ${
              isComplete ? 'bg-emerald-500' : 'bg-gradient-to-r from-indigo-500 to-emerald-400'
            }`}
            style={{ width: `${percent}%` }}
          />
        </div>

        {/* Steps list */}
        {!collapsed && (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-2.5 mt-5 pt-4 border-t border-border">
            {data.steps.map((step) => (
              <Link
                key={step.key}
                to={step.href}
                className={`p-3 rounded-2xl border transition-all flex items-start gap-2.5 ${
                  step.completed
                    ? 'bg-bg-primary/40 border-border hover:border-emerald-500/30'
                    : 'bg-indigo-500/5 border-indigo-500/20 hover:border-indigo-500/40 shadow-sm'
                }`}
              >
                {step.completed ? (
                  <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
                ) : (
                  <Circle className="w-4 h-4 text-indigo-400 shrink-0 mt-0.5" />
                )}
                <div className="min-w-0">
                  <span className={`text-xs font-bold block truncate ${
                    step.completed ? 'text-secondary line-through' : 'text-primary'
                  }`}>
                    {step.label}
                  </span>
                  <span className="text-[10px] text-secondary">
                    {step.completed ? 'Concluído' : 'Configurar agora →'}
                  </span>
                </div>
              </Link>
            ))}
          </div>
        )}
      </div>
    </section>
  );
}
