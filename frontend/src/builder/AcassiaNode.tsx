import { memo, useState } from 'react';
import {
  Handle,
  Position,
  NodeToolbar,
  useReactFlow,
  type Node,
  type NodeProps,
} from '@xyflow/react';
import {
  AlertCircle,
  AlertTriangle,
  ArrowRight,
  Bot,
  BrainCircuit,
  Check,
  Clock,
  Copy,
  CornerDownRight,
  FileText,
  GitBranch,
  Globe,
  Hash,
  HelpCircle,
  Image as ImageIcon,
  Layers,
  MessageSquare,
  Mic,
  MoreVertical,
  Play,
  PlayCircle,
  Sparkles,
  SquarePen,
  Tag,
  Trash2,
  Type,
  UserCheck,
  Video,
  Volume2,
  Zap,
} from 'lucide-react';
import type { FlowNodeData } from '../lib/adapt';
import { visualForType } from './nodeStyles';
import { toast } from '../lib/toast';

export type AcassiaFlowNode = Node<FlowNodeData, 'meumisterio'>;

export const AcassiaNode = memo(function AcassiaNode({
  id,
  data,
  selected,
}: NodeProps<AcassiaFlowNode>) {
  const d = data;
  const type = d.meumisterioType;
  const v = visualForType(type);
  const cfg = d.config || {};
  const isTrigger = type === 'trigger';
  const isEnd = type === 'end';

  const [copiedId, setCopiedId] = useState(false);

  const handleCopyId = (e: React.MouseEvent) => {
    e.stopPropagation();
    navigator.clipboard.writeText(id);
    setCopiedId(true);
    toast.success(`ID do nó copiado: ${id}`);
    setTimeout(() => setCopiedId(false), 2000);
  };

  // Node Category Badges & Color Palette
  const CATEGORY_STYLES: Record<
    string,
    { badgeBg: string; badgeText: string; iconBg: string; iconColor: string; accentBorder: string }
  > = {
    trigger: {
      badgeBg: 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400',
      badgeText: 'Gatilho Inicial',
      iconBg: 'bg-emerald-500 text-white',
      iconColor: 'text-emerald-600',
      accentBorder: 'hover:border-emerald-500/60',
    },
    conteudo: {
      badgeBg: 'bg-indigo-500/10 text-indigo-600 dark:text-indigo-400',
      badgeText: 'Mensagem WhatsApp',
      iconBg: 'bg-indigo-600 text-white',
      iconColor: 'text-indigo-600',
      accentBorder: 'hover:border-indigo-500/60',
    },
    agente_ia: {
      badgeBg: 'bg-purple-500/10 text-purple-600 dark:text-purple-400',
      badgeText: 'Agente de IA',
      iconBg: 'bg-purple-600 text-white',
      iconColor: 'text-purple-600',
      accentBorder: 'hover:border-purple-500/60',
    },
    gpt: {
      badgeBg: 'bg-purple-500/10 text-purple-600 dark:text-purple-400',
      badgeText: 'IA Generativa',
      iconBg: 'bg-purple-600 text-white',
      iconColor: 'text-purple-600',
      accentBorder: 'hover:border-purple-500/60',
    },
    pergunta: {
      badgeBg: 'bg-amber-500/10 text-amber-600 dark:text-amber-400',
      badgeText: 'Pergunta & Opções',
      iconBg: 'bg-amber-500 text-white',
      iconColor: 'text-amber-600',
      accentBorder: 'hover:border-amber-500/60',
    },
    condicao: {
      badgeBg: 'bg-sky-500/10 text-sky-600 dark:text-sky-400',
      badgeText: 'Decisão Lógica',
      iconBg: 'bg-sky-500 text-white',
      iconColor: 'text-sky-600',
      accentBorder: 'hover:border-sky-500/60',
    },
    ab_split: {
      badgeBg: 'bg-pink-500/10 text-pink-600 dark:text-pink-400',
      badgeText: 'Teste A/B',
      iconBg: 'bg-pink-500 text-white',
      iconColor: 'text-pink-600',
      accentBorder: 'hover:border-pink-500/60',
    },
    acao: {
      badgeBg: 'bg-blue-500/10 text-blue-600 dark:text-blue-400',
      badgeText: 'Ação de CRM',
      iconBg: 'bg-blue-600 text-white',
      iconColor: 'text-blue-600',
      accentBorder: 'hover:border-blue-500/60',
    },
    delay: {
      badgeBg: 'bg-orange-500/10 text-orange-600 dark:text-orange-400',
      badgeText: 'Delay Inteligente',
      iconBg: 'bg-orange-500 text-white',
      iconColor: 'text-orange-600',
      accentBorder: 'hover:border-orange-500/60',
    },
    voice_studio: {
      badgeBg: 'bg-rose-500/10 text-rose-600 dark:text-rose-400',
      badgeText: 'Voz & Áudio IA',
      iconBg: 'bg-rose-500 text-white',
      iconColor: 'text-rose-600',
      accentBorder: 'hover:border-rose-500/60',
    },
    notificar_atendente: {
      badgeBg: 'bg-blue-500/10 text-blue-600 dark:text-blue-400',
      badgeText: 'Notificar Atendente',
      iconBg: 'bg-blue-600 text-white',
      iconColor: 'text-blue-600',
      accentBorder: 'hover:border-blue-500/60',
    },
    end: {
      badgeBg: 'bg-zinc-500/10 text-zinc-600 dark:text-zinc-400',
      badgeText: 'Fim do Funil',
      iconBg: 'bg-zinc-700 text-white',
      iconColor: 'text-zinc-600',
      accentBorder: 'hover:border-zinc-500/60',
    },
  };

  const cat = CATEGORY_STYLES[type] || {
    badgeBg: 'bg-zinc-500/10 text-zinc-600 dark:text-zinc-400',
    badgeText: v.label || type,
    iconBg: 'bg-zinc-800 text-white',
    iconColor: 'text-zinc-600',
    accentBorder: 'hover:border-zinc-500/60',
  };

  return (
    <>
      {/* Start Node Badge (ChatbotX Style) */}
      {isTrigger && (
        <div className="absolute -top-7 left-3 z-20 flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-emerald-500 text-white text-[11px] font-bold shadow-sm tracking-wide">
          <span className="w-2 h-2 rounded-full bg-white animate-ping" />
          <Play className="w-3 h-3 fill-current" />
          Início do Funil
        </div>
      )}

      {/* Floating Node Toolbar (ChatbotX Style) */}
      <NodeToolbar
        isVisible={selected}
        position={Position.Top}
        offset={12}
        className="flex items-center gap-1 bg-zinc-900 text-zinc-100 p-1 rounded-xl shadow-2xl border border-zinc-700/80 backdrop-blur-md z-50 animate-in fade-in zoom-in-95 duration-150"
      >
        <button
          type="button"
          onClick={(e) => {
            e.stopPropagation();
            d.onEdit?.();
          }}
          className="flex items-center gap-1.5 px-2.5 py-1 text-xs font-medium hover:bg-zinc-800 rounded-lg transition-colors text-zinc-200 hover:text-white"
          title="Editar Configurações"
        >
          <SquarePen className="w-3.5 h-3.5 text-indigo-400" />
          Editar
        </button>

        <button
          type="button"
          onClick={(e) => {
            e.stopPropagation();
            d.onDuplicate?.();
          }}
          className="p-1.5 hover:bg-zinc-800 rounded-lg transition-colors text-zinc-300 hover:text-white"
          title="Duplicar Nó"
        >
          <Copy className="w-3.5 h-3.5" />
        </button>

        <button
          type="button"
          onClick={handleCopyId}
          className="p-1.5 hover:bg-zinc-800 rounded-lg transition-colors text-zinc-300 hover:text-white"
          title="Copiar ID do Nó"
        >
          {copiedId ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Hash className="w-3.5 h-3.5" />}
        </button>

        {!isTrigger && (
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              d.onDelete?.();
            }}
            className="p-1.5 hover:bg-red-500/20 rounded-lg transition-colors text-zinc-300 hover:text-red-400"
            title="Excluir Nó"
          >
            <Trash2 className="w-3.5 h-3.5" />
          </button>
        )}
      </NodeToolbar>

      {/* Main Node Card */}
      <div
        onDoubleClick={(e) => {
          e.stopPropagation();
          d.onEdit?.();
        }}
        className={[
          'group relative w-[310px] rounded-2xl bg-white dark:bg-zinc-900 border transition-all duration-200 shadow-sm font-sans select-none',
          selected
            ? 'border-indigo-500 dark:border-indigo-500 ring-2 ring-indigo-500/20 shadow-lg'
            : 'border-zinc-200 dark:border-zinc-800 hover:shadow-md hover:border-zinc-300 dark:hover:border-zinc-700',
          d.simActive ? 'ring-2 ring-emerald-500 shadow-lg shadow-emerald-500/20 animate-pulse' : '',
          d.lintLevel === 'error' ? 'ring-2 ring-rose-500 border-rose-500' : '',
        ].join(' ')}
      >
        {/* Lint Warning/Error Badge */}
        {d.lintLevel && (
          <div
            className={[
              'absolute -top-2 -right-2 w-5 h-5 rounded-full flex items-center justify-center text-white z-30 shadow-md',
              d.lintLevel === 'error' ? 'bg-rose-500' : 'bg-amber-500',
            ].join(' ')}
            title={d.lintLevel === 'error' ? 'Erro de validação' : 'Aviso de consistência'}
          >
            {d.lintLevel === 'error' ? (
              <AlertCircle className="w-3 h-3" />
            ) : (
              <AlertTriangle className="w-3 h-3" />
            )}
          </div>
        )}

        {/* Input Handle (Left) */}
        {!isTrigger && (
          <Handle
            type="target"
            position={Position.Left}
            className="!w-3.5 !h-3.5 !-left-[7px] !bg-white dark:!bg-zinc-900 !border-2 !border-zinc-400 dark:!border-zinc-600 hover:!border-indigo-500 hover:!scale-125 !transition-all !shadow-sm !rounded-full"
          />
        )}

        {/* Node Header */}
        <div className="flex items-center justify-between p-3.5 pb-2.5 border-b border-zinc-100 dark:border-zinc-800/80">
          <div className="flex items-center gap-2.5 min-w-0">
            <div className={`w-8 h-8 rounded-xl flex items-center justify-center shrink-0 ${cat.iconBg} shadow-sm`}>
              <v.Icon className="w-4 h-4" />
            </div>
            <div className="flex flex-col min-w-0">
              <span className="text-[13px] font-semibold text-zinc-900 dark:text-zinc-100 truncate leading-tight">
                {d.label || v.label}
              </span>
              <span className="text-[10px] font-medium text-zinc-400 dark:text-zinc-500 uppercase tracking-wider mt-0.5">
                {cat.badgeText}
              </span>
            </div>
          </div>

          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              d.onEdit?.();
            }}
            className="w-7 h-7 rounded-lg text-zinc-400 hover:text-zinc-700 dark:hover:text-zinc-200 hover:bg-zinc-100 dark:hover:bg-zinc-800 flex items-center justify-center transition-colors shrink-0"
            title="Editar Parâmetros"
          >
            <SquarePen className="w-3.5 h-3.5" />
          </button>
        </div>

        {/* Node Body / Step Viewers */}
        <div className="p-3.5 flex flex-col gap-2.5">
          {renderNodeContent(type, d, id)}
        </div>

        {/* Node Footer / Default Output Handle */}
        {!isEnd && shouldRenderDefaultContinue(type, d) && (
          <div className="relative px-3.5 py-2.5 border-t border-zinc-100 dark:border-zinc-800/80 bg-zinc-50/50 dark:bg-zinc-900/50 rounded-b-2xl flex items-center justify-end">
            <span className="text-[11px] font-medium text-zinc-400 dark:text-zinc-500 mr-3.5 flex items-center gap-1">
              Continuar
              <ArrowRight className="w-3 h-3" />
            </span>
            <Handle
              type="source"
              position={Position.Right}
              className="!w-3.5 !h-3.5 !-right-[7px] !bg-indigo-600 !border-2 !border-white dark:!border-zinc-900 hover:!scale-125 !transition-all !shadow-sm !rounded-full"
            />
          </div>
        )}
      </div>
    </>
  );
});

export default AcassiaNode;

/** Decide se exibe o handle padrão "Continuar" no rodapé */
function shouldRenderDefaultContinue(type: string, d: FlowNodeData): boolean {
  if (type === 'condicao' || type === 'ab_split') return false;
  if (type === 'pergunta') return false;
  if (type === 'agente_ia') return false;
  if (type === 'voice_studio') return false;
  if (type === 'menu' || type === 'expediente') return false;

  // Se conteudo tiver botões interativos, cada botão tem seu próprio handle
  if (type === 'conteudo') {
    const config = d.config || {};
    const hasButtons =
      Array.isArray(config.buttons) && config.buttons.length > 0;
    const hasQuickReplies =
      Array.isArray(config.quick_replies) && config.quick_replies.length > 0;
    if (hasButtons || hasQuickReplies) return false;
  }

  return true;
}

/** Renderiza o preview visual de acordo com o tipo de nó */
function renderNodeContent(type: string, d: FlowNodeData, nodeId: string) {
  const cfg = d.config || {};

  // 1. GATILHO DE ENTRADA (TRIGGER)
  if (type === 'trigger') {
    const triggerEvent = (cfg.event as string) || 'keyword';
    const keyword = (cfg.keyword as string) || '';
    return (
      <div className="flex flex-col gap-2">
        <div className="flex items-center justify-between text-[11px] font-medium text-zinc-500 dark:text-zinc-400">
          <span className="flex items-center gap-1.5">
            <Zap className="w-3.5 h-3.5 text-emerald-500" />
            Origem: WhatsApp API
          </span>
          <span className="text-[10px] bg-emerald-50 text-emerald-600 dark:bg-emerald-950/40 dark:text-emerald-400 px-2 py-0.5 rounded-full font-semibold">
            Ativo
          </span>
        </div>
        <div className="p-2.5 rounded-xl bg-zinc-50 dark:bg-zinc-800/60 border border-zinc-200/80 dark:border-zinc-700/60 flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-emerald-500" />
          <span className="text-xs text-zinc-700 dark:text-zinc-300 font-medium truncate">
            {triggerEvent === 'purchase'
              ? '🛒 Compra aprovada'
              : triggerEvent === 'abandon'
              ? '⏰ Carrinho abandonado'
              : keyword
              ? `Palavra-chave: "${keyword}"`
              : 'Qualquer mensagem recebida'}
          </span>
        </div>
      </div>
    );
  }

  // 2. MENSAGEM WHATSAPP (CONTEUDO)
  if (type === 'conteudo') {
    const rawCards = cfg.contents;
    let cards: any[] = [];
    if (Array.isArray(rawCards) && rawCards.length > 0) {
      cards = rawCards;
    } else {
      const text = cfg.text || cfg.message;
      if (typeof text === 'string' && text) {
        cards = [{ type: 'text', value: text }];
      }
    }

    const buttons = Array.isArray(cfg.buttons) ? cfg.buttons : [];
    const quickReplies = Array.isArray(cfg.quick_replies) ? cfg.quick_replies : [];
    const allButtons = [...buttons, ...quickReplies];

    return (
      <div className="flex flex-col gap-2.5">
        {/* WhatsApp Chat Bubble Mock */}
        <div className="p-3 rounded-2xl rounded-tl-sm bg-[#f0f2f5] dark:bg-zinc-800/80 border border-zinc-200/70 dark:border-zinc-700/60 shadow-inner flex flex-col gap-2">
          {cards.length > 0 ? (
            cards.map((c: any, i: number) => {
              if (c.type === 'text') {
                const parts = (c.value || '').split(/(\{\{[^{}]+\}\})/g);
                return (
                  <div key={i} className="text-xs text-zinc-800 dark:text-zinc-200 leading-relaxed break-words">
                    {parts.map((part: string, idx: number) => {
                      if (part.startsWith('{{') && part.endsWith('}}')) {
                        return (
                          <span
                            key={idx}
                            className="inline-block mx-0.5 px-1.5 py-0.5 bg-indigo-100 dark:bg-indigo-900/60 text-indigo-700 dark:text-indigo-300 font-mono text-[10px] rounded-md font-semibold"
                          >
                            {part}
                          </span>
                        );
                      }
                      return <span key={idx}>{part}</span>;
                    })}
                  </div>
                );
              }
              if (c.type === 'audio') {
                return (
                  <div key={i} className="flex items-center gap-2.5 p-2 rounded-xl bg-white dark:bg-zinc-900 border border-zinc-200/60 dark:border-zinc-700/60">
                    <div className="w-7 h-7 rounded-full bg-indigo-600 text-white flex items-center justify-center shrink-0">
                      <Play className="w-3.5 h-3.5 fill-current ml-0.5" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-1 h-3">
                        <span className="w-1 h-2 bg-indigo-400 rounded-full" />
                        <span className="w-1 h-3 bg-indigo-500 rounded-full" />
                        <span className="w-1 h-2 bg-indigo-400 rounded-full" />
                        <span className="w-1 h-3.5 bg-indigo-600 rounded-full" />
                        <span className="w-1 h-2.5 bg-indigo-500 rounded-full" />
                        <span className="w-1 h-1.5 bg-indigo-300 rounded-full" />
                      </div>
                      <span className="text-[10px] text-zinc-400 font-medium">Áudio gravado · 0:15</span>
                    </div>
                  </div>
                );
              }
              if (c.type === 'image') {
                return (
                  <div key={i} className="flex items-center gap-2 p-2 rounded-xl bg-white dark:bg-zinc-900 border border-zinc-200/60 dark:border-zinc-700/60 text-xs text-zinc-600 dark:text-zinc-300 font-medium">
                    <ImageIcon className="w-4 h-4 text-sky-500 shrink-0" />
                    <span className="truncate">Imagem anexada</span>
                  </div>
                );
              }
              if (c.type === 'document') {
                return (
                  <div key={i} className="flex items-center gap-2 p-2 rounded-xl bg-white dark:bg-zinc-900 border border-zinc-200/60 dark:border-zinc-700/60 text-xs text-zinc-600 dark:text-zinc-300 font-medium">
                    <FileText className="w-4 h-4 text-amber-500 shrink-0" />
                    <span className="truncate">Documento PDF</span>
                  </div>
                );
              }
              return null;
            })
          ) : (
            <span className="text-xs text-zinc-400 italic">Nenhum texto configurado.</span>
          )}
        </div>

        {/* Botões Interativos com seus próprios Handles */}
        {allButtons.length > 0 && (
          <div className="flex flex-col gap-1.5 mt-1">
            <span className="text-[10px] uppercase font-bold tracking-wider text-zinc-400 dark:text-zinc-500 px-1">
              Botões de Resposta
            </span>
            {allButtons.map((btn: any, idx: number) => {
              const label = typeof btn === 'string' ? btn : btn.label || btn.text || `Opção ${idx + 1}`;
              const handleId = typeof btn === 'object' && btn.id ? btn.id : `btn_${idx}`;
              return (
                <div
                  key={idx}
                  className="relative flex items-center justify-between px-3 py-2 rounded-xl bg-zinc-50 dark:bg-zinc-800/80 border border-zinc-200/80 dark:border-zinc-700/60 text-xs font-semibold text-zinc-800 dark:text-zinc-200 hover:border-indigo-400 transition-colors"
                >
                  <span className="truncate pr-4">{label}</span>
                  <Handle
                    type="source"
                    id={handleId}
                    position={Position.Right}
                    className="!w-3.5 !h-3.5 !-right-[18px] !bg-indigo-600 !border-2 !border-white dark:!border-zinc-900 hover:!scale-125 !transition-all !shadow-sm !rounded-full"
                  />
                </div>
              );
            })}
          </div>
        )}
      </div>
    );
  }

  // 3. AGENTE DE IA (AGENTE_IA / GPT)
  if (type === 'agente_ia' || type === 'gpt') {
    const model = (cfg.model as string) || 'gemini-2.5-flash';
    const prompt = (cfg.system_prompt as string) || (cfg.prompt as string) || '';
    const delay = (cfg.human_delay_seconds as number) || 3;

    return (
      <div className="flex flex-col gap-2.5">
        {/* Model Badge */}
        <div className="flex items-center justify-between">
          <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-md bg-purple-50 dark:bg-purple-950/40 text-purple-700 dark:text-purple-300 text-[11px] font-semibold border border-purple-200/60 dark:border-purple-800/40">
            <Sparkles className="w-3 h-3 text-purple-500" />
            {model}
          </span>
          <span className="text-[10px] text-zinc-400 flex items-center gap-1">
            <Clock className="w-3 h-3" />
            Delay: {delay}s
          </span>
        </div>

        {/* Prompt Preview */}
        <div className="p-2.5 rounded-xl bg-zinc-50 dark:bg-zinc-800/60 border border-zinc-200/80 dark:border-zinc-700/60 text-[11px] text-zinc-600 dark:text-zinc-400 line-clamp-3 font-mono leading-relaxed break-words">
          {prompt ? prompt : 'Nenhum prompt configurado. O agente usará a persona padrão da empresa.'}
        </div>

        {/* AI Handles */}
        <div className="flex flex-col gap-1.5 mt-1 border-t border-zinc-100 dark:border-zinc-800/80 pt-2">
          <div className="relative flex items-center justify-between text-xs py-1">
            <span className="text-zinc-700 dark:text-zinc-300 font-medium">Sucesso / Conversa</span>
            <Handle
              type="source"
              id="sucesso"
              position={Position.Right}
              className="!w-3.5 !h-3.5 !-right-[18px] !bg-purple-600 !border-2 !border-white dark:!border-zinc-900 hover:!scale-125 !transition-all !shadow-sm !rounded-full"
            />
          </div>
          <div className="relative flex items-center justify-between text-xs py-1">
            <span className="text-rose-600 dark:text-rose-400 font-medium">Transbordo / Erro</span>
            <Handle
              type="source"
              id="erro"
              position={Position.Right}
              className="!w-3.5 !h-3.5 !-right-[18px] !bg-rose-500 !border-2 !border-white dark:!border-zinc-900 hover:!scale-125 !transition-all !shadow-sm !rounded-full"
            />
          </div>
        </div>
      </div>
    );
  }

  // 4. PERGUNTA & OPÇÕES (PERGUNTA)
  if (type === 'pergunta') {
    const question = (cfg.question || cfg.body || cfg.question_text) as string;
    const quickReplies = Array.isArray(cfg.quick_replies) ? (cfg.quick_replies as string[]) : [];

    return (
      <div className="flex flex-col gap-2.5">
        <div className="p-2.5 rounded-xl bg-amber-50/50 dark:bg-amber-950/20 border border-amber-200/60 dark:border-amber-900/40 text-xs text-zinc-800 dark:text-zinc-200 font-medium break-words">
          {question || 'Pergunta não configurada'}
        </div>

        {/* Options list */}
        <div className="flex flex-col gap-1.5 mt-1">
          {quickReplies.length > 0 ? (
            quickReplies.map((qr, idx) => (
              <div
                key={idx}
                className="relative flex items-center justify-between px-3 py-1.5 rounded-xl bg-zinc-50 dark:bg-zinc-800/80 border border-zinc-200/80 dark:border-zinc-700/60 text-xs font-semibold text-zinc-800 dark:text-zinc-200"
              >
                <span className="truncate pr-4">{qr}</span>
                <Handle
                  type="source"
                  id={`option-${idx}`}
                  position={Position.Right}
                  className="!w-3.5 !h-3.5 !-right-[18px] !bg-amber-500 !border-2 !border-white dark:!border-zinc-900 hover:!scale-125 !transition-all !shadow-sm !rounded-full"
                />
              </div>
            ))
          ) : (
            <div className="relative flex items-center justify-between px-3 py-1.5 rounded-xl bg-zinc-50 dark:bg-zinc-800/80 border border-zinc-200/80 dark:border-zinc-700/60 text-xs font-semibold text-zinc-800 dark:text-zinc-200">
              <span>Resposta livre do usuário</span>
              <Handle
                type="source"
                id="resposta"
                position={Position.Right}
                className="!w-3.5 !h-3.5 !-right-[18px] !bg-amber-500 !border-2 !border-white dark:!border-zinc-900 hover:!scale-125 !transition-all !shadow-sm !rounded-full"
              />
            </div>
          )}

          {/* Timeout Fallback */}
          <div className="relative flex items-center justify-between text-xs py-1 border-t border-zinc-100 dark:border-zinc-800/80 pt-2 mt-1">
            <span className="text-zinc-400">Timeout / Sem resposta</span>
            <Handle
              type="source"
              id="timeout"
              position={Position.Right}
              className="!w-3.5 !h-3.5 !-right-[18px] !bg-rose-500 !border-2 !border-white dark:!border-zinc-900 hover:!scale-125 !transition-all !shadow-sm !rounded-full"
            />
          </div>
        </div>
      </div>
    );
  }

  // 5. CONDIÇÃO & ROTEAMENTO (CONDICAO / AB_SPLIT)
  if (type === 'condicao' || type === 'ab_split') {
    const rules = (cfg.rules as any[]) || [];
    const conditionText = (cfg.condition as string) || (rules[0]?.field ? `${rules[0].field} ${rules[0].operator || '=='} ${rules[0].value || ''}` : 'Verificar condição');

    return (
      <div className="flex flex-col gap-2.5">
        <div className="p-2.5 rounded-xl bg-sky-50/50 dark:bg-sky-950/20 border border-sky-200/60 dark:border-sky-900/40 text-xs text-zinc-700 dark:text-zinc-300 font-mono break-words">
          {conditionText}
        </div>

        {/* True / False branches */}
        <div className="flex flex-col gap-1.5 mt-1">
          <div className="relative flex items-center justify-between px-3 py-2 rounded-xl bg-emerald-50/60 dark:bg-emerald-950/30 border border-emerald-200/60 dark:border-emerald-800/40 text-xs font-semibold text-emerald-700 dark:text-emerald-300">
            <span>Sim / Condição Verdadeira</span>
            <Handle
              type="source"
              id="true"
              position={Position.Right}
              className="!w-3.5 !h-3.5 !-right-[18px] !bg-emerald-500 !border-2 !border-white dark:!border-zinc-900 hover:!scale-125 !transition-all !shadow-sm !rounded-full"
            />
          </div>

          <div className="relative flex items-center justify-between px-3 py-2 rounded-xl bg-zinc-50 dark:bg-zinc-800/80 border border-zinc-200/80 dark:border-zinc-700/60 text-xs font-semibold text-zinc-600 dark:text-zinc-400">
            <span>Não / Senão</span>
            <Handle
              type="source"
              id="false"
              position={Position.Right}
              className="!w-3.5 !h-3.5 !-right-[18px] !bg-zinc-500 !border-2 !border-white dark:!border-zinc-900 hover:!scale-125 !transition-all !shadow-sm !rounded-full"
            />
          </div>
        </div>
      </div>
    );
  }

  // 6. AÇÕES & CRM (ACAO)
  if (type === 'acao') {
    const actionType = (cfg.action as string) || (cfg.action_type as string) || 'add_tag';
    const tag = (cfg.tag as string) || '';

    return (
      <div className="flex flex-col gap-2">
        <div className="flex items-center gap-2 p-2 rounded-xl bg-blue-50/50 dark:bg-blue-950/30 border border-blue-200/60 dark:border-blue-900/40 text-xs text-blue-700 dark:text-blue-300 font-medium">
          <Tag className="w-3.5 h-3.5 shrink-0" />
          <span className="truncate">
            {actionType === 'add_tag' && tag
              ? `Adicionar Tag: ${tag}`
              : actionType === 'remove_tag'
              ? `Remover Tag: ${tag}`
              : 'Executar Ação CRM'}
          </span>
        </div>
      </div>
    );
  }

  // 7. SMART DELAY (DELAY)
  if (type === 'delay') {
    const seconds = (cfg.seconds as number) || (cfg.duration as number) || 60;
    const minutes = Math.round(seconds / 60);

    return (
      <div className="flex items-center gap-2.5 p-2.5 rounded-xl bg-orange-50/50 dark:bg-orange-950/30 border border-orange-200/60 dark:border-orange-900/40">
        <Clock className="w-4 h-4 text-orange-500 shrink-0" />
        <span className="text-xs font-semibold text-orange-700 dark:text-orange-300">
          Aguardar {minutes > 0 ? `${minutes} minuto(s)` : `${seconds} segundo(s)`}
        </span>
      </div>
    );
  }

  // 8. VOZ E ÁUDIO IA (VOICE_STUDIO)
  if (type === 'voice_studio') {
    const voice = (cfg.voice as string) || 'Alloy';
    return (
      <div className="flex flex-col gap-2">
        <div className="flex items-center justify-between text-xs">
          <span className="flex items-center gap-1.5 font-medium text-zinc-700 dark:text-zinc-300">
            <Volume2 className="w-3.5 h-3.5 text-rose-500" />
            Voz IA: {voice}
          </span>
          <span className="text-[10px] bg-rose-50 text-rose-600 dark:bg-rose-950/40 dark:text-rose-400 px-2 py-0.5 rounded-full font-semibold">
            Humanizada
          </span>
        </div>
        <div className="flex flex-col gap-1.5 mt-1 border-t border-zinc-100 dark:border-zinc-800/80 pt-2">
          <div className="relative flex items-center justify-between text-xs py-1">
            <span className="text-zinc-700 dark:text-zinc-300 font-medium">Continuar</span>
            <Handle
              type="source"
              id="sucesso"
              position={Position.Right}
              className="!w-3.5 !h-3.5 !-right-[18px] !bg-rose-500 !border-2 !border-white dark:!border-zinc-900 hover:!scale-125 !transition-all !shadow-sm !rounded-full"
            />
          </div>
          <div className="relative flex items-center justify-between text-xs py-1">
            <span className="text-zinc-400 font-medium">Erro / Falha</span>
            <Handle
              type="source"
              id="erro"
              position={Position.Right}
              className="!w-3.5 !h-3.5 !-right-[18px] !bg-zinc-400 !border-2 !border-white dark:!border-zinc-900 hover:!scale-125 !transition-all !shadow-sm !rounded-full"
            />
          </div>
        </div>
      </div>
    );
  }

  // 9. API / WEBHOOK (API / INTEGRATION)
  if (type === 'api' || type === 'integration') {
    const url = (cfg.url as string) || (cfg.endpoint as string) || 'https://api.crm.com/webhook';
    return (
      <div className="flex flex-col gap-2">
        <div className="flex items-center gap-1.5 text-xs text-zinc-600 dark:text-zinc-300 font-mono truncate p-2 rounded-xl bg-zinc-50 dark:bg-zinc-800/80 border border-zinc-200/80 dark:border-zinc-700/60">
          <Globe className="w-3.5 h-3.5 text-cyan-500 shrink-0" />
          <span className="truncate">{url}</span>
        </div>
        <div className="flex flex-col gap-1.5 mt-1 border-t border-zinc-100 dark:border-zinc-800/80 pt-2">
          <div className="relative flex items-center justify-between text-xs py-1">
            <span className="text-zinc-700 dark:text-zinc-300 font-medium">Sucesso</span>
            <Handle
              type="source"
              id="sucesso"
              position={Position.Right}
              className="!w-3.5 !h-3.5 !-right-[18px] !bg-cyan-500 !border-2 !border-white dark:!border-zinc-900 hover:!scale-125 !transition-all !shadow-sm !rounded-full"
            />
          </div>
          <div className="relative flex items-center justify-between text-xs py-1">
            <span className="text-rose-500 font-medium">Erro HTTP</span>
            <Handle
              type="source"
              id="erro"
              position={Position.Right}
              className="!w-3.5 !h-3.5 !-right-[18px] !bg-rose-500 !border-2 !border-white dark:!border-zinc-900 hover:!scale-125 !transition-all !shadow-sm !rounded-full"
            />
          </div>
        </div>
      </div>
    );
  }

  // 10. FIM (END)
  if (type === 'end') {
    return (
      <div className="p-2.5 rounded-xl bg-zinc-100 dark:bg-zinc-800/80 border border-zinc-200 dark:border-zinc-700 text-center text-xs font-semibold text-zinc-600 dark:text-zinc-400">
        🏁 Encerramento da Conversa
      </div>
    );
  }

  // DEFAULT FALLBACK
  return (
    <div className="p-2 text-xs text-zinc-500 dark:text-zinc-400 italic">
      Clique duas vezes para configurar este nó.
    </div>
  );
}
