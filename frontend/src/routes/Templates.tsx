import { useState } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import {
  Sparkles, Heart, Crown, Star, RefreshCw,
  Layers, ArrowRight, Check, X,
} from 'lucide-react';
import { templatesApi, type FlowTemplate } from '../api/templates';
import { handleApiError } from '../lib/handleApiError';
import { toast } from '../lib/toast';

const CATEGORY_META: Record<string, { label: string; Icon: typeof Sparkles; color: string }> = {
  amor: { label: 'Amor', Icon: Heart, color: 'text-rose-400' },
  premium: { label: 'Premium', Icon: Crown, color: 'text-amber-400' },
  astrologia: { label: 'Astrologia', Icon: Star, color: 'text-purple-400' },
  recuperacao: { label: 'Recuperação', Icon: RefreshCw, color: 'text-blue-400' },
};

export default function Templates() {
  const navigate = useNavigate();
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);
  const [previewing, setPreviewing] = useState<FlowTemplate | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ['flow-templates', selectedCategory],
    queryFn: () => templatesApi.list(selectedCategory || undefined),
  });

  const applyMut = useMutation({
    mutationFn: (id: string) => templatesApi.apply(id),
    onSuccess: (res) => {
      toast.success('Template aplicado! Redirecionando...');
      setTimeout(() => navigate(res.redirect), 800);
    },
    onError: handleApiError('Erro ao aplicar template'),
  });

  const templates = data?.templates ?? [];
  const categories = Array.from(new Set(templates.map(t => t.category).filter(Boolean))) as string[];

  return (
    <div className="p-10 max-w-6xl mx-auto space-y-8">
      <div>
        <div className="flex items-center gap-3 mb-2">
          <div className="w-10 h-10 rounded-2xl bg-accent-amethyst/10 flex items-center justify-center">
            <Layers className="w-5 h-5 text-accent-amethyst" />
          </div>
          <h1 className="text-3xl font-black tracking-tight">Templates de Fluxo</h1>
        </div>
        <p className="text-secondary text-sm font-medium">
          Comece em 2 cliques. Cada template já vem com fluxo + persona pré-configurados.
        </p>
      </div>

      {/* Category filter */}
      {categories.length > 0 && (
        <div className="flex items-center gap-2 flex-wrap">
          <button
            onClick={() => setSelectedCategory(null)}
            className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${
              !selectedCategory
                ? 'bg-accent-amethyst text-white'
                : 'bg-bg-surface text-secondary hover:text-primary'
            }`}
          >
            Todos
          </button>
          {categories.map((c) => {
            const meta = CATEGORY_META[c];
            const Icon = meta?.Icon || Sparkles;
            return (
              <button
                key={c}
                onClick={() => setSelectedCategory(c)}
                className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all flex items-center gap-1.5 ${
                  selectedCategory === c
                    ? 'bg-accent-amethyst text-white'
                    : 'bg-bg-surface text-secondary hover:text-primary'
                }`}
              >
                <Icon className="w-3.5 h-3.5" />
                {meta?.label || c}
              </button>
            );
          })}
        </div>
      )}

      {/* Grid */}
      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 animate-pulse">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="h-64 bg-bg-surface rounded-3xl" />
          ))}
        </div>
      ) : templates.length === 0 ? (
        <div className="text-center py-16 text-secondary">Nenhum template disponível.</div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {templates.map((t) => {
            const meta = t.category ? CATEGORY_META[t.category] : null;
            const Icon = meta?.Icon || Sparkles;
            return (
              <div
                key={t.id}
                className="bg-bg-surface border border-border rounded-3xl p-6 flex flex-col hover:border-accent-amethyst/30 transition-all"
              >
                <div className="flex items-start justify-between mb-3">
                  <div className={`w-10 h-10 rounded-xl bg-bg-primary flex items-center justify-center ${meta?.color || 'text-accent-amethyst'}`}>
                    <Icon className="w-5 h-5" />
                  </div>
                  {t.is_official && (
                    <span className="text-[9px] font-black uppercase tracking-widest text-accent-amethyst">
                      ✦ Oficial
                    </span>
                  )}
                </div>

                <h3 className="font-black text-lg tracking-tight">{t.name}</h3>
                <p className="text-[11px] text-secondary mt-1 line-clamp-2 flex-1">
                  {t.description}
                </p>

                <div className="flex items-center gap-3 mt-4 mb-4 text-[11px] text-secondary">
                  <span className="flex items-center gap-1">
                    <Layers className="w-3 h-3" />
                    {t.node_count} nós
                  </span>
                  {t.ticket_brl_avg > 0 && (
                    <>
                      <span>·</span>
                      <span className="font-mono">R${t.ticket_brl_avg}</span>
                    </>
                  )}
                  {t.usage_count > 0 && (
                    <>
                      <span>·</span>
                      <span>{t.usage_count} usos</span>
                    </>
                  )}
                </div>

                <div className="flex gap-2">
                  <button
                    onClick={() => setPreviewing(t)}
                    className="flex-1 px-3 py-2 bg-bg-primary border border-border hover:border-accent-amethyst/30 rounded-xl text-xs font-bold transition-all"
                  >
                    Preview
                  </button>
                  <button
                    onClick={() => applyMut.mutate(t.id)}
                    disabled={applyMut.isPending}
                    className="flex-1 px-3 py-2 bg-accent-amethyst hover:bg-accent-amethyst/90 disabled:opacity-30 text-white rounded-xl text-xs font-black uppercase tracking-widest flex items-center justify-center gap-1"
                  >
                    Aplicar
                    <ArrowRight className="w-3 h-3" />
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Preview modal */}
      {previewing && (
        <PreviewModal
          template={previewing}
          onClose={() => setPreviewing(null)}
          onApply={() => applyMut.mutate(previewing.id)}
          applying={applyMut.isPending}
        />
      )}
    </div>
  );
}

function PreviewModal({
  template, onClose, onApply, applying,
}: {
  template: FlowTemplate;
  onClose: () => void;
  onApply: () => void;
  applying: boolean;
}) {
  const { data: detail, isLoading } = useQuery({
    queryKey: ['template-detail', template.id],
    queryFn: () => templatesApi.get(template.id),
  });

  const nodes = detail?.blueprint_json
    ? (detail.blueprint_json as { nodes?: Array<{ id: string; type: string; text?: string }> }).nodes || []
    : [];

  return (
    <div className="fixed inset-0 z-50 bg-black/70 flex items-center justify-center p-6">
      <div className="bg-bg-surface border border-border rounded-3xl max-w-2xl w-full max-h-[80vh] overflow-hidden flex flex-col">
        <div className="p-6 border-b border-border flex items-start justify-between gap-3">
          <div>
            <h2 className="text-xl font-black tracking-tight">{template.name}</h2>
            <p className="text-xs text-secondary mt-1">{template.description}</p>
          </div>
          <button onClick={onClose} className="text-secondary hover:text-primary">
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="p-6 overflow-y-auto flex-1 space-y-4">
          {isLoading ? (
            <div className="text-center text-secondary text-sm py-8">Carregando...</div>
          ) : (
            <>
              <h3 className="text-[10px] font-black uppercase tracking-widest text-secondary">
                Preview do fluxo ({nodes.length} nós)
              </h3>
              {nodes.map((n, i) => (
                <div key={n.id} className="flex gap-3">
                  <div className="flex-shrink-0 w-8 h-8 rounded-lg bg-bg-primary border border-border flex items-center justify-center font-mono text-[10px] font-black">
                    {i + 1}
                  </div>
                  <div className="flex-1 bg-bg-primary border border-border rounded-xl p-3">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-[10px] font-mono text-accent-amethyst">{n.type}</span>
                      <span className="text-[10px] text-secondary">·</span>
                      <span className="text-[10px] font-mono text-secondary">{n.id}</span>
                    </div>
                    {n.text && (
                      <p className="text-xs text-primary whitespace-pre-wrap">{n.text}</p>
                    )}
                  </div>
                </div>
              ))}
            </>
          )}
        </div>

        <div className="p-4 border-t border-border flex gap-3">
          <button
            onClick={onClose}
            className="flex-1 px-5 py-3 bg-bg-primary border border-border rounded-2xl text-sm font-bold"
          >
            Fechar
          </button>
          <button
            onClick={onApply}
            disabled={applying}
            className="flex-1 px-5 py-3 bg-accent-amethyst hover:bg-accent-amethyst/90 disabled:opacity-30 text-white rounded-2xl text-sm font-black uppercase tracking-widest flex items-center justify-center gap-2"
          >
            <Check className="w-4 h-4" />
            {applying ? 'Aplicando...' : 'Aplicar este template'}
          </button>
        </div>
      </div>
    </div>
  );
}
