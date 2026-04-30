import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { Brain, Sparkles, RefreshCw, AlertCircle } from 'lucide-react';
import { coachApi, type LeadSummary } from '../api/coach';
import { handleApiError } from '../lib/handleApiError';

interface Props {
  leadId: number;
}

/**
 * Resumo IA da conversa (Frente 6.21).
 * On-demand pra economizar quota Gemini — atendente clica "Resumir"
 * pra contexto rápido em leads com muitas mensagens.
 */
export default function LeadSummaryCard({ leadId }: Props) {
  const [summary, setSummary] = useState<LeadSummary | null>(null);
  const [analyzed, setAnalyzed] = useState(0);

  const mut = useMutation({
    mutationFn: () => coachApi.leadSummary(leadId),
    onSuccess: (res) => {
      setSummary(res.summary);
      setAnalyzed(res.msgs_analyzed);
    },
    onError: handleApiError('Erro ao gerar resumo'),
  });

  const personalInfo = Array.isArray(summary?.personal_info_collected)
    ? (summary?.personal_info_collected as string[])
    : summary?.personal_info_collected
      ? [summary.personal_info_collected as string]
      : [];

  return (
    <div className="bg-bg-surface border border-border rounded-2xl p-4 space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="text-[10px] font-black uppercase tracking-widest text-secondary flex items-center gap-1.5">
          <Brain className="w-3 h-3 text-accent-amethyst" />
          Resumo da conversa
        </h3>
        <button
          onClick={() => mut.mutate()}
          disabled={mut.isPending}
          className="text-[10px] text-accent-amethyst hover:underline flex items-center gap-1 font-bold"
        >
          <RefreshCw className={`w-3 h-3 ${mut.isPending ? 'animate-spin' : ''}`} />
          {summary ? 'Atualizar' : 'Resumir'}
        </button>
      </div>

      {!summary && !mut.isPending && (
        <p className="text-[11px] text-secondary text-center py-2">
          Clique "Resumir" pra IA condensar a conversa em pontos chave.
        </p>
      )}

      {mut.isPending && (
        <p className="text-[11px] text-secondary text-center py-3">Analisando conversa…</p>
      )}

      {summary && (
        <div className="space-y-2.5 text-[11px]">
          <Field
            label="Pergunta principal"
            value={summary.main_question}
          />
          <Field
            label="Estágio do funil"
            value={summary.current_funnel_stage}
          />
          <Field
            label="Sentimento dominante"
            value={summary.sentiment_dominant}
          />
          {personalInfo.length > 0 && (
            <div>
              <div className="text-[9px] font-black uppercase tracking-widest text-secondary mb-1">
                Informação coletada
              </div>
              <ul className="space-y-0.5">
                {personalInfo.slice(0, 5).map((p, i) => (
                  <li key={i} className="text-[11px] flex gap-1.5">
                    <span className="text-secondary">•</span>
                    <span>{p}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
          {summary.suggested_next_action && (
            <div className="bg-accent-amethyst/5 border border-accent-amethyst/30 rounded-lg p-2 mt-2">
              <div className="flex items-start gap-1.5">
                <Sparkles className="w-3 h-3 text-accent-amethyst flex-shrink-0 mt-0.5" />
                <div>
                  <div className="text-[9px] font-black uppercase tracking-widest text-accent-amethyst mb-0.5">
                    Próxima ação sugerida
                  </div>
                  <p className="text-[11px] leading-relaxed">{summary.suggested_next_action}</p>
                </div>
              </div>
            </div>
          )}
          {analyzed > 0 && (
            <div className="text-[9px] text-secondary flex items-center gap-1">
              <AlertCircle className="w-2.5 h-2.5" />
              {analyzed} mensagens analisadas
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function Field({ label, value }: { label: string; value: string | undefined | null }) {
  if (!value) return null;
  return (
    <div>
      <div className="text-[9px] font-black uppercase tracking-widest text-secondary">
        {label}
      </div>
      <div className="text-[11px] mt-0.5 leading-relaxed">{value}</div>
    </div>
  );
}
