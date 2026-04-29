import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  CheckCircle2,
  ChevronRight,
  CircleDashed,
  Clock,
  RefreshCw,
  XCircle,
} from 'lucide-react';
import { runsApi } from '../api/runs';

export default function Runs() {
  const [selected, setSelected] = useState<number | null>(null);

  const {
    data: runs = [],
    isLoading,
    refetch,
    isFetching,
  } = useQuery({
    queryKey: ['flow-runs'],
    queryFn: () => runsApi.list({ limit: 100 }),
    refetchInterval: 15000,
  });

  return (
    <div className="p-8 max-w-7xl mx-auto text-slate-100 h-full flex flex-col">
      <div className="flex items-center justify-between mb-6 flex-shrink-0">
        <div>
          <h2 className="text-2xl font-bold font-display">Execuções de fluxo</h2>
          <p className="text-sm text-slate-400 mt-1">
            Histórico de runs disparados nos blueprints publicados deste tenant.
          </p>
        </div>
        <button
          onClick={() => refetch()}
          disabled={isFetching}
          className="text-xs px-2 py-1 rounded border border-cigana-border hover:border-cigana-purple flex items-center gap-1 disabled:opacity-50"
        >
          <RefreshCw className={`w-3 h-3 ${isFetching ? 'animate-spin' : ''}`} />
          Atualizar
        </button>
      </div>

      <div className="flex-1 min-h-0 flex gap-4">
        {/* Lista */}
        <div className="flex-1 min-w-0 bg-cigana-surface border border-cigana-border rounded-xl overflow-hidden flex flex-col">
          <div className="px-4 py-2 border-b border-cigana-border text-[11px] uppercase tracking-wide text-slate-400 grid grid-cols-[80px,1fr,90px,140px,30px] gap-3 flex-shrink-0">
            <span>Run</span>
            <span>Blueprint / Lead</span>
            <span>Status</span>
            <span>Iniciado</span>
            <span></span>
          </div>
          <ul className="flex-1 overflow-y-auto divide-y divide-cigana-border/50">
            {isLoading && (
              <li className="px-4 py-4 text-xs text-slate-500">Carregando…</li>
            )}
            {!isLoading && runs.length === 0 && (
              <li className="px-4 py-4 text-xs text-slate-500">
                Nenhuma execução registrada ainda.
              </li>
            )}
            {runs.map((r) => (
              <li
                key={r.id}
                onClick={() => setSelected(r.id === selected ? null : r.id)}
                className={[
                  'px-4 py-2 grid grid-cols-[80px,1fr,90px,140px,30px] gap-3 items-center cursor-pointer text-sm hover:bg-cigana-bg/40',
                  selected === r.id ? 'bg-cigana-bg/60' : '',
                ].join(' ')}
              >
                <span className="font-mono text-xs text-slate-300">#{r.id}</span>
                <span className="text-slate-200 truncate">
                  bp #{r.blueprint_id}
                  {r.lead_id != null && (
                    <span className="text-slate-500 ml-2">· lead {r.lead_id}</span>
                  )}
                </span>
                <StatusChip status={r.status} />
                <span className="text-[11px] text-slate-500 truncate">
                  {r.started_at ? new Date(r.started_at).toLocaleString() : '—'}
                </span>
                <ChevronRight
                  className={`w-3 h-3 text-slate-500 transition-transform ${
                    selected === r.id ? 'rotate-90 text-cigana-purple' : ''
                  }`}
                />
              </li>
            ))}
          </ul>
        </div>

        {/* Detalhe */}
        {selected != null && (
          <div className="w-96 flex-shrink-0 bg-cigana-surface border border-cigana-border rounded-xl overflow-hidden flex flex-col animate-slide-in-right">
            <RunDetail runId={selected} onClose={() => setSelected(null)} />
          </div>
        )}
      </div>
    </div>
  );
}

function StatusChip({ status }: { status: string }) {
  const meta = statusMeta(status);
  return (
    <span
      className={`text-[10px] uppercase tracking-wide px-1.5 py-0.5 rounded inline-flex items-center gap-1 ${meta.cls}`}
    >
      <meta.Icon className="w-2.5 h-2.5" />
      {status || '—'}
    </span>
  );
}

function statusMeta(status: string) {
  const s = (status || '').toLowerCase();
  if (s === 'ok' || s === 'success' || s === 'finished')
    return { cls: 'bg-emerald-500/15 text-emerald-300', Icon: CheckCircle2 };
  if (s === 'error' || s === 'failed' || s === 'fail')
    return { cls: 'bg-red-500/15 text-red-300', Icon: XCircle };
  if (s === 'running' || s === 'in_progress')
    return { cls: 'bg-sky-500/15 text-sky-300', Icon: CircleDashed };
  return { cls: 'bg-slate-700/30 text-slate-300', Icon: Clock };
}

function RunDetail({ runId, onClose }: { runId: number; onClose: () => void }) {
  const { data: run } = useQuery({
    queryKey: ['run', runId],
    queryFn: () => runsApi.get(runId),
  });
  const { data: events = [] } = useQuery({
    queryKey: ['run-events', runId],
    queryFn: () => runsApi.events(runId),
  });

  return (
    <>
      <header className="px-3 py-2 border-b border-cigana-border flex items-center justify-between flex-shrink-0">
        <span className="text-[11px] uppercase tracking-wide text-slate-400">
          Run #{runId}
        </span>
        <button
          onClick={onClose}
          className="text-slate-400 hover:text-slate-200 text-sm px-2"
        >
          ×
        </button>
      </header>

      <div className="flex-1 overflow-y-auto px-3 py-3 space-y-3 text-sm">
        {run && (
          <dl className="grid grid-cols-[110px,1fr] gap-x-2 gap-y-1 text-xs">
            <dt className="text-slate-500">blueprint</dt>
            <dd className="font-mono text-slate-300">#{run.blueprint_id}</dd>
            <dt className="text-slate-500">lead</dt>
            <dd className="font-mono text-slate-300">{run.lead_id ?? '—'}</dd>
            <dt className="text-slate-500">status</dt>
            <dd>
              <StatusChip status={run.status} />
            </dd>
            <dt className="text-slate-500">iniciado</dt>
            <dd className="text-slate-300">
              {run.started_at ? new Date(run.started_at).toLocaleString() : '—'}
            </dd>
            <dt className="text-slate-500">finalizado</dt>
            <dd className="text-slate-300">
              {run.finished_at
                ? new Date(run.finished_at).toLocaleString()
                : '—'}
            </dd>
          </dl>
        )}

        <div>
          <div className="text-[11px] uppercase tracking-wide text-slate-400 mb-1">
            Eventos ({events.length})
          </div>
          {events.length === 0 ? (
            <p className="text-[11px] text-slate-500">Sem eventos.</p>
          ) : (
            <ol className="space-y-1.5">
              {events.map((e) => (
                <li
                  key={e.id}
                  className="border-l-2 border-cigana-border pl-2 text-xs"
                >
                  <div className="flex items-baseline justify-between gap-2">
                    <span className="font-mono text-slate-300">{e.type}</span>
                    <span className="text-[10px] text-slate-500">
                      {e.ts ? new Date(e.ts).toLocaleTimeString() : ''}
                    </span>
                  </div>
                  {e.node_id && (
                    <div className="text-[10px] font-mono text-slate-500">
                      node: {e.node_id}
                    </div>
                  )}
                  {Object.keys(e.payload || {}).length > 0 && (
                    <pre className="mt-1 text-[10px] text-slate-400 bg-cigana-bg/60 rounded p-1.5 overflow-x-auto">
                      {JSON.stringify(e.payload, null, 2)}
                    </pre>
                  )}
                </li>
              ))}
            </ol>
          )}
        </div>
      </div>
    </>
  );
}
