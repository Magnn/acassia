import { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import {
  Heart, AlertTriangle, ArrowLeft, Tag, ThumbsDown,
  Sparkles, MessageCircle, ShieldCheck,
} from 'lucide-react';
import { billingApi } from '../api/billing';
import { toast } from '../lib/toast';
import { ApiError } from '../api/client';

type Step = 'reason' | 'win_back' | 'confirm';

const REASONS = [
  { id: 'too_expensive', label: 'Muito caro', icon: Tag, win_back: 'discount_50pct_3m' },
  { id: 'not_using', label: 'Não estou usando o suficiente', icon: AlertTriangle, win_back: 'pause_2_months' },
  { id: 'missing_feature', label: 'Falta uma feature que preciso', icon: Sparkles, win_back: 'feature_request' },
  { id: 'switched_tool', label: 'Mudei pra outra ferramenta', icon: ThumbsDown, win_back: null },
  { id: 'tech_issues', label: 'Problemas técnicos', icon: AlertTriangle, win_back: 'support_call' },
  { id: 'other', label: 'Outro motivo', icon: MessageCircle, win_back: null },
];

const WIN_BACK_OFFERS: Record<string, { title: string; description: string; cta: string }> = {
  discount_50pct_3m: {
    title: '50% off pelos próximos 3 meses',
    description: 'Aplicado automaticamente. Você pode cancelar depois sem multa.',
    cta: 'Aceitar desconto e ficar',
  },
  pause_2_months: {
    title: 'Pausar assinatura por 2 meses',
    description: 'Sem cobrança nos próximos 2 meses. Tudo volta ao normal depois — pode cancelar antes.',
    cta: 'Pausar 2 meses',
  },
  feature_request: {
    title: 'Conta-nos qual feature?',
    description: 'Vamos avaliar e priorizar. Te avisamos quando chegar — em até 90 dias.',
    cta: 'Mandar pedido + ficar',
  },
  support_call: {
    title: 'Vamos resolver juntos',
    description: 'Agendamos uma call rápida com nosso time pra entender e corrigir.',
    cta: 'Agendar call + ficar',
  },
};

export default function BillingCancel() {
  const navigate = useNavigate();
  const qc = useQueryClient();
  const [step, setStep] = useState<Step>('reason');
  const [reasonId, setReasonId] = useState<string | null>(null);
  const [reasonText, setReasonText] = useState('');

  const submitMut = useMutation({
    mutationFn: billingApi.submitCancellation,
    onSuccess: (res) => {
      qc.invalidateQueries({ queryKey: ['billing-state'] });
      qc.invalidateQueries({ queryKey: ['me', 'plan'] });
      toast.success(res.message);
      setTimeout(() => navigate('/billing'), 1500);
    },
    onError: (e: unknown) => {
      const body = e instanceof ApiError ? (e.body as { error?: string }) : null;
      toast.error(body?.error || 'Erro');
    },
  });

  const reason = REASONS.find(r => r.id === reasonId);
  const winBackKey = reason?.win_back;
  const winBackOffer = winBackKey ? WIN_BACK_OFFERS[winBackKey] : null;

  function acceptWinBack() {
    submitMut.mutate({
      reason_category: reasonId || undefined,
      reason_text: reasonText || undefined,
      win_back_offered: winBackKey || undefined,
      win_back_accepted: true,
    });
  }

  function confirmCancel() {
    submitMut.mutate({
      reason_category: reasonId || undefined,
      reason_text: reasonText || undefined,
      win_back_offered: winBackKey || undefined,
      win_back_accepted: winBackKey ? false : undefined,
    });
  }

  return (
    <div className="p-10 max-w-2xl mx-auto space-y-8">
      <button
        onClick={() => navigate('/billing')}
        className="flex items-center gap-2 text-secondary hover:text-primary text-xs font-bold uppercase tracking-widest"
      >
        <ArrowLeft className="w-3.5 h-3.5" />
        Voltar pra Assinatura
      </button>

      {step === 'reason' && (
        <ReasonStep
          reasonId={reasonId}
          setReasonId={setReasonId}
          reasonText={reasonText}
          setReasonText={setReasonText}
          onNext={() => setStep(winBackOffer ? 'win_back' : 'confirm')}
        />
      )}

      {step === 'win_back' && winBackOffer && (
        <WinBackStep
          offer={winBackOffer}
          reasonLabel={reason?.label || ''}
          onAccept={acceptWinBack}
          onSkip={() => setStep('confirm')}
          loading={submitMut.isPending}
        />
      )}

      {step === 'confirm' && (
        <ConfirmStep
          reasonLabel={reason?.label}
          onConfirm={confirmCancel}
          onBack={() => setStep('reason')}
          loading={submitMut.isPending}
        />
      )}
    </div>
  );
}

function ReasonStep({
  reasonId, setReasonId, reasonText, setReasonText, onNext,
}: {
  reasonId: string | null;
  setReasonId: (id: string) => void;
  reasonText: string;
  setReasonText: (t: string) => void;
  onNext: () => void;
}) {
  return (
    <div className="space-y-8">
      <div>
        <Heart className="w-12 h-12 text-rose-400 mb-4" />
        <h1 className="text-3xl font-black tracking-tight">Cancelar assinatura</h1>
        <p className="text-secondary text-sm font-medium mt-2">
          Sentimos muito. Antes de seguir, conta pra gente o motivo —
          isso ajuda a melhorar a Acássia.
        </p>
      </div>

      <div className="space-y-2">
        {REASONS.map((r) => {
          const Icon = r.icon;
          const selected = reasonId === r.id;
          return (
            <button
              key={r.id}
              onClick={() => setReasonId(r.id)}
              className={`w-full flex items-center gap-4 p-4 rounded-2xl border transition-all text-left ${
                selected
                  ? 'bg-accent-amethyst/10 border-accent-amethyst'
                  : 'bg-bg-surface border-border hover:border-accent-amethyst/30'
              }`}
            >
              <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${
                selected ? 'bg-accent-amethyst/20' : 'bg-bg-primary'
              }`}>
                <Icon className={`w-5 h-5 ${selected ? 'text-accent-amethyst' : 'text-secondary'}`} />
              </div>
              <span className={`text-sm font-bold ${selected ? 'text-primary' : 'text-secondary'}`}>
                {r.label}
              </span>
              {selected && (
                <span className="ml-auto px-2 py-0.5 bg-accent-amethyst/20 rounded text-[10px] font-black uppercase tracking-widest text-accent-amethyst">
                  Selecionado
                </span>
              )}
            </button>
          );
        })}
      </div>

      <div>
        <label className="text-[10px] uppercase font-black tracking-widest text-secondary mb-2 block">
          Quer dar mais detalhes? (opcional)
        </label>
        <textarea
          value={reasonText}
          onChange={(e) => setReasonText(e.target.value)}
          rows={3}
          placeholder="Sua opinião nos ajuda a melhorar..."
          className="w-full bg-bg-surface border border-border rounded-2xl px-4 py-3 text-sm text-primary placeholder:text-secondary/40 focus:outline-none focus:border-accent-amethyst/30 resize-none"
        />
      </div>

      <div className="flex gap-3">
        <button
          onClick={() => window.history.back()}
          className="flex-1 px-5 py-3 bg-bg-surface border border-border rounded-2xl text-sm font-bold"
        >
          Voltar
        </button>
        <button
          onClick={onNext}
          disabled={!reasonId}
          className="flex-1 px-5 py-3 bg-accent-amethyst hover:bg-accent-amethyst/90 disabled:opacity-30 text-white rounded-2xl text-sm font-black uppercase tracking-widest"
        >
          Próximo
        </button>
      </div>
    </div>
  );
}

function WinBackStep({
  offer, reasonLabel, onAccept, onSkip, loading,
}: {
  offer: { title: string; description: string; cta: string };
  reasonLabel: string;
  onAccept: () => void;
  onSkip: () => void;
  loading: boolean;
}) {
  return (
    <div className="space-y-8">
      <div className="text-center space-y-3">
        <div className="w-16 h-16 mx-auto rounded-3xl bg-gradient-to-br from-accent-amethyst to-rose-400 flex items-center justify-center">
          <Heart className="w-8 h-8 text-white" />
        </div>
        <div className="text-[10px] font-black uppercase tracking-widest text-accent-amethyst">
          Espera — temos uma oferta pra você
        </div>
        <h1 className="text-3xl font-black tracking-tight">{offer.title}</h1>
        <p className="text-secondary text-sm font-medium max-w-md mx-auto">
          Você disse que está saindo por <strong className="text-primary">"{reasonLabel}"</strong>.
          {' '}{offer.description}
        </p>
      </div>

      <div className="space-y-3">
        <button
          onClick={onAccept}
          disabled={loading}
          className="w-full px-6 py-4 bg-gradient-to-r from-accent-amethyst to-rose-400 disabled:opacity-30 text-white rounded-2xl text-sm font-black uppercase tracking-widest shadow-2xl flex items-center justify-center gap-2 hover:scale-[1.02] transition-all"
        >
          <Heart className="w-4 h-4" />
          {loading ? 'Aplicando...' : offer.cta}
        </button>
        <button
          onClick={onSkip}
          disabled={loading}
          className="w-full px-6 py-3 bg-bg-surface border border-border rounded-2xl text-xs font-bold uppercase tracking-widest text-secondary hover:text-primary"
        >
          Não obrigada — quero cancelar
        </button>
      </div>
    </div>
  );
}

function ConfirmStep({
  reasonLabel, onConfirm, onBack, loading,
}: {
  reasonLabel?: string;
  onConfirm: () => void;
  onBack: () => void;
  loading: boolean;
}) {
  return (
    <div className="space-y-8">
      <div className="text-center space-y-3">
        <div className="w-16 h-16 mx-auto rounded-3xl bg-red-500/10 flex items-center justify-center">
          <AlertTriangle className="w-8 h-8 text-red-500" />
        </div>
        <h1 className="text-3xl font-black tracking-tight">Cancelar assinatura?</h1>
        {reasonLabel && (
          <p className="text-secondary text-sm font-medium">
            Motivo: <strong className="text-primary">{reasonLabel}</strong>
          </p>
        )}
      </div>

      <div className="bg-amber-500/5 border border-amber-500/20 rounded-3xl p-6 space-y-3">
        <h3 className="text-sm font-black flex items-center gap-2">
          <ShieldCheck className="w-4 h-4" />
          O que vai acontecer
        </h3>
        <ul className="space-y-2 text-xs text-secondary">
          <li className="flex items-start gap-2">
            <span className="text-emerald-500">✓</span>
            Você mantém acesso até o fim do ciclo atual
          </li>
          <li className="flex items-start gap-2">
            <span className="text-emerald-500">✓</span>
            Nenhuma cobrança adicional será feita
          </li>
          <li className="flex items-start gap-2">
            <span className="text-emerald-500">✓</span>
            Seus dados ficam preservados por 30 dias caso queira voltar
          </li>
          <li className="flex items-start gap-2">
            <span className="text-emerald-500">✓</span>
            Pode reativar a qualquer momento durante a janela
          </li>
        </ul>
      </div>

      <div className="flex gap-3">
        <button
          onClick={onBack}
          disabled={loading}
          className="flex-1 px-5 py-3 bg-bg-surface border border-border rounded-2xl text-sm font-bold"
        >
          Voltar
        </button>
        <button
          onClick={onConfirm}
          disabled={loading}
          className="flex-1 px-5 py-3 bg-red-600 hover:bg-red-500 disabled:opacity-30 text-white rounded-2xl text-sm font-black uppercase tracking-widest"
        >
          {loading ? 'Cancelando...' : 'Confirmar cancelamento'}
        </button>
      </div>
    </div>
  );
}
