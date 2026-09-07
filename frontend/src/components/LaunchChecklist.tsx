import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { CheckCircle2, Circle } from 'lucide-react';
import { onboardingApi } from '../api/onboarding';

export default function LaunchChecklist() {
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['launch-readiness'],
    queryFn: onboardingApi.getReadiness,
    staleTime: 15_000,
    refetchInterval: 30_000,
  });
  return (
    <section aria-labelledby="launch-title" className="bg-bg-surface border border-border rounded-3xl p-6 space-y-4">
      <h3 id="launch-title" className="text-lg font-bold">Prepare seu atendimento</h3>
      {isLoading && <p role="status" className="text-sm text-secondary">Verificando configuração…</p>}
      {error && <div role="alert" className="text-sm text-secondary">
        Não foi possível verificar os próximos passos.{' '}
        <button onClick={() => void refetch()} className="underline">Tentar novamente</button>
      </div>}
      {data && <>
        <p className="text-sm text-secondary">{data.completed_count} de {data.total} etapas concluídas.
          {data.checks_complete ? ' Agora acompanhe conversões e recuperação nas métricas e revise as conversas.' : ' Teste a jornada antes de receber clientes.'}
        </p>
        <ul className="grid gap-3 sm:grid-cols-2">
          {data.steps.map(step => <li key={step.key}>
            <Link to={step.href} className="flex items-center gap-2 text-sm hover:underline focus-visible:outline focus-visible:outline-2 rounded">
              {step.completed ? <CheckCircle2 aria-hidden="true" className="w-4 h-4 text-emerald-500 shrink-0" /> : <Circle aria-hidden="true" className="w-4 h-4 text-secondary shrink-0" />}
              <span className="sr-only">{step.completed ? 'Concluído: ' : 'Pendente: '}</span>{step.label}
            </Link>
          </li>)}
        </ul>
        {data.next_step && <Link to={data.next_step.href} className="inline-block rounded-xl bg-accent-amethyst text-white px-4 py-2 text-sm font-bold">Continuar: {data.next_step.label}</Link>}
      </>}
    </section>
  );
}
