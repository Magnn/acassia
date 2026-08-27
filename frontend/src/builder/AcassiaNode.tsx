import { Handle, Position, useReactFlow, type Node, type NodeProps } from '@xyflow/react';
import { 
  AlertCircle, AlertTriangle, MoreHorizontal, MessageSquare, 
  HelpCircle, PlayCircle, Clock, Image as ImageIcon, Video, Mic, FileText, Type,
  Copy, SquarePen
} from 'lucide-react';
import type { FlowNodeData } from '../lib/adapt';
import { visualForType } from './nodeStyles';

export type MeuMisterioFlowNode = Node<FlowNodeData, 'meumisterio'>;

export default function MeuMisterioNode({ id, data, selected }: NodeProps<MeuMisterioFlowNode>) {
  const { setNodes } = useReactFlow();
  const d = data;
  const v = visualForType(d.meumisterioType);

  const type = d.meumisterioType;
  const isTrigger = type === 'trigger';
  const isEnd = type === 'end';

  // --- TRIGGER NODE ---
  if (isTrigger) {
    return (
      <div className="flex flex-col gap-0 items-center font-sans w-[176px] relative transition-all">
        {d.lintLevel && (
          <span
            className={[
              'absolute -top-2 -right-2 rounded-full w-6 h-6 flex items-center justify-center border-[1.5px] border-white shadow-sm z-20',
              d.lintLevel === 'error' ? 'bg-red-500 text-white' : 'bg-amber-400 text-slate-900',
            ].join(' ')}
          >
            {d.lintLevel === 'error' ? <AlertCircle className="w-3.5 h-3.5" /> : <AlertTriangle className="w-3.5 h-3.5" />}
          </span>
        )}

        {/* Trigger Main Card */}
        <div className={[
          "border rounded-[10px] bg-white w-full overflow-hidden flex flex-col",
          selected ? "border-green-500 shadow-md ring-1 ring-green-500/30" : "border-slate-300 shadow-sm",
          d.simActive ? "ring-2 ring-emerald-500 animate-pulse" : "",
        ].join(' ')}>
          <div className="grid grid-cols-[42px_1fr] items-center min-h-[39px]">
            <div className="bg-white border-r border-slate-100 flex items-center justify-center h-full">
              <div className="w-[27px] h-[27px] rounded-full bg-[#10b981] flex items-center justify-center">
                <v.Icon className="w-3.5 h-3.5 text-white" />
              </div>
            </div>
            <div className="text-[12.4px] font-semibold text-slate-900 text-center px-2 tracking-tight">
              {d.label || 'WhatsApp'}
            </div>
          </div>
          <div className="min-h-[28px] border-t border-slate-100 bg-slate-50 text-[9px] font-medium text-slate-500 flex items-center justify-center text-center px-1.5 py-1 leading-tight">
            Enviou palavra chave
          </div>
        </div>

        {/* Arrow Down */}
        <div className="flex flex-col items-center justify-center text-emerald-500 -mt-px mb-0.5">
          <div className="w-[10px] h-px bg-white -mt-px block relative z-10" />
          <div className="w-4 h-[18px] bg-emerald-500 flex flex-col items-center justify-center">
             <svg width="8" height="6" viewBox="0 0 8 6" fill="currentColor"><path d="M4 6L0 0H8L4 6Z" /></svg>
          </div>
        </div>

        {/* Keyword Block */}
        <div className="border-[1.3px] border-emerald-500 rounded-lg text-[9.2px] font-semibold text-slate-900 bg-white shadow-sm px-2 py-1.5 text-center w-full max-w-[162px] break-words flex items-center justify-center min-h-[47px] leading-[1.14]">
          {stringField(d.config, 'keyword') || 'Qualquer mensagem'}
        </div>
        
        <Handle type="source" position={Position.Right} className="!w-5 !h-5 !bg-white !border-2 !border-blue-500 !shadow-sm !rounded-full after:content-[''] after:absolute after:left-1/2 after:top-1/2 after:w-0 after:h-0 after:border-solid after:border-[4px_0_4px_7px] after:border-[transparent_transparent_transparent_#fff] after:-translate-x-1/2 after:-translate-y-1/2" />
      </div>
    );
  }

  // --- STANDARD NODES (Conteudo, Pergunta, Acao, etc) ---
    // Define colors based on Meu Mistério Type or fallback to visualForType
  let headerBg = 'bg-[#f8fafc]';
  let headerText = 'text-slate-900';
  let iconColor = v.accent;
  let iconBg = 'bg-white border border-slate-200';
  let bodyBg = 'bg-white';
  let borderColor = 'border-slate-200';
  let headerActionColor = 'text-slate-400 hover:text-slate-600 bg-transparent';
  
  if (type === 'conteudo') {
    headerBg = 'bg-[#7c3aed]';
    headerText = 'text-white';
    iconColor = 'text-[#7c3aed]';
    iconBg = 'bg-white/95';
    borderColor = 'border-[#7c3aed]';
    headerActionColor = 'text-white/90 bg-white/18 hover:bg-white/30';
  } else if (type === 'pergunta') {
    headerBg = 'bg-[#ff5722]';
    headerText = 'text-white';
    iconColor = 'text-[#ff5722]';
    iconBg = 'bg-white';
    borderColor = 'border-[#e8ddd4]';
    headerActionColor = 'text-white/90 bg-black/20 hover:bg-black/30';
  } else if (type === 'acao') {
    headerBg = 'bg-[#3730a3]'; // indigo-800
    headerText = 'text-white';
    iconColor = 'text-[#3730a3]';
    iconBg = 'bg-white';
    borderColor = 'border-[#3730a3]';
    bodyBg = 'bg-white';
    headerActionColor = 'text-white/90 bg-black/20 hover:bg-black/30';
  } else if (type === 'condicao') {
    headerBg = 'bg-[#ef4444]'; // red-500
    headerText = 'text-white';
    iconColor = 'text-[#ef4444]';
    iconBg = 'bg-white';
    borderColor = 'border-[#ef4444]';
    headerActionColor = 'text-white/90 bg-black/20 hover:bg-black/30';
  } else if (type === 'ab_split') {
    headerBg = 'bg-[#ec4899]'; // pink-500
    headerText = 'text-white';
    iconColor = 'text-[#ec4899]';
    iconBg = 'bg-white';
    borderColor = 'border-[#ec4899]';
    headerActionColor = 'text-white/90 bg-black/20 hover:bg-black/30';
  }

  // Simulate a random traffic count for visual parity with the screenshot
  const trafficCount = numberField(d.config, 'stats_count') ?? Math.abs(parseInt(d.label || '0', 36)) % 500;

  return (
    <div
      className={[
        `rounded-[10px] border-2 min-w-[280px] max-w-[320px] shadow-sm relative font-sans transition-all duration-300`,
        borderColor,
        bodyBg,
        d.simActive ? 'ring-2 ring-emerald-500 shadow-glow-emerald animate-pulse' : '',
        !d.simActive && selected ? `ring-2 ring-accent-amethyst shadow-glow-amethyst` : '',
        !d.simActive && d.lintLevel === 'error' ? 'ring-2 ring-red-500' : '',
      ].join(' ')}
    >
      {/* Traffic Stats Pill */}
      <div className="absolute -top-[10px] left-1/2 -translate-x-1/2 z-30">
        <div className="bg-[#9333ea] text-white text-[10px] font-bold px-2 py-0.5 rounded-full shadow-sm leading-none border border-[#7e22ce]">
          {trafficCount}
        </div>
      </div>

      {/* Validation Badge */}
      {d.lintLevel && (
        <span
          className={[
            'absolute -top-2.5 -right-2.5 rounded-full w-6 h-6 flex items-center justify-center border-[1.5px] border-white shadow-sm z-20',
            d.lintLevel === 'error' ? 'bg-red-500 text-white' : 'bg-amber-400 text-slate-900',
          ].join(' ')}
        >
          {d.lintLevel === 'error' ? <AlertCircle className="w-3.5 h-3.5" /> : <AlertTriangle className="w-3.5 h-3.5" />}
        </span>
      )}

      {/* Header — icon + label + Copy + Edit buttons */}
      <div className={[`px-3 py-2.5 rounded-t-[8px] flex items-center justify-between`, headerBg].join(' ')}>
        <div className="flex items-center gap-2.5 overflow-hidden">
          <div className={[`w-[24px] h-[24px] rounded-[6px] flex items-center justify-center shrink-0`, iconBg].join(' ')}>
            <v.Icon className={[`w-4 h-4`, iconColor].join(' ')} strokeWidth={2.5} />
          </div>
          <span className={[`text-[13px] font-bold tracking-tight truncate`, headerText].join(' ')}>
            {d.label || v.label}
          </span>
        </div>
        <div className="flex items-center gap-1.5">
          <div
            className={[`flex items-center justify-center rounded-[6px] w-[28px] h-[28px] shrink-0 transition-colors cursor-pointer`, headerActionColor].join(' ')}
            title="Duplicar"
            onClick={(e) => {
              e.stopPropagation();
              d.onDuplicate?.();
            }}
          >
            <Copy className="w-3.5 h-3.5" />
          </div>
          <div
            className={[`flex items-center justify-center rounded-[6px] w-[28px] h-[28px] shrink-0 transition-colors cursor-pointer`, headerActionColor].join(' ')}
            title="Editar"
            onClick={(e) => {
              e.stopPropagation();
              d.onEdit?.();
            }}
          >
            <SquarePen className="w-3.5 h-3.5" />
          </div>
        </div>
      </div>

      {/* Body */}
      <div className="p-3 flex flex-col gap-2 rounded-b-[8px]">
         {renderPreview(d)}
         {renderConfigHint(d)}
      </div>

      {/* Input Handle — white circle with blue border + ▶ play arrow */}
      {!isTrigger && (
        <Handle
          type="target"
          position={Position.Left}
          className="!w-[22px] !h-[22px] !bg-white !border-2 !border-blue-500 !shadow-sm !rounded-full"
        >
          <svg className="absolute left-1/2 top-1/2 -translate-x-[45%] -translate-y-1/2 pointer-events-none" width="8" height="10" viewBox="0 0 8 10" fill="none">
            <path d="M8 5L0 10V0L8 5Z" fill="#3b82f6" />
          </svg>
        </Handle>
      )}

      {/* Output Handles — filled circle with white ▶ play arrow */}
      {!isEnd && (
        <>
          {type === 'condicao' ? (
            <>
              <Handle type="source" id="true" position={Position.Right} className="!w-[22px] !h-[22px] !bg-blue-500 !border-2 !border-white !shadow-sm !rounded-full !top-[30%]">
                <svg className="absolute left-1/2 top-1/2 -translate-x-[45%] -translate-y-1/2 pointer-events-none" width="8" height="10" viewBox="0 0 8 10" fill="none"><path d="M8 5L0 10V0L8 5Z" fill="white" /></svg>
              </Handle>
              <Handle type="source" id="false" position={Position.Right} className="!w-[22px] !h-[22px] !bg-red-500 !border-2 !border-white !shadow-sm !rounded-full !top-[85%]">
                <svg className="absolute left-1/2 top-1/2 -translate-x-[45%] -translate-y-1/2 pointer-events-none" width="8" height="10" viewBox="0 0 8 10" fill="none"><path d="M8 5L0 10V0L8 5Z" fill="white" /></svg>
              </Handle>
            </>
          ) : type === 'pergunta' ? (
            <>
              <Handle type="source" id="resposta" position={Position.Right} className="!w-[22px] !h-[22px] !bg-blue-500 !border-2 !border-white !shadow-sm !rounded-full !top-[40%]">
                <svg className="absolute left-1/2 top-1/2 -translate-x-[45%] -translate-y-1/2 pointer-events-none" width="8" height="10" viewBox="0 0 8 10" fill="none"><path d="M8 5L0 10V0L8 5Z" fill="white" /></svg>
              </Handle>
              <Handle type="source" id="timeout" position={Position.Right} className="!w-[22px] !h-[22px] !bg-red-500 !border-2 !border-white !shadow-sm !rounded-full !top-[85%]">
                <svg className="absolute left-1/2 top-1/2 -translate-x-[45%] -translate-y-1/2 pointer-events-none" width="8" height="10" viewBox="0 0 8 10" fill="none"><path d="M8 5L0 10V0L8 5Z" fill="white" /></svg>
              </Handle>
            </>
          ) : type === 'ab_split' ? (
            <>
              <Handle type="source" id="a" position={Position.Right} className="!w-[22px] !h-[22px] !bg-[#ec4899] !border-2 !border-white !shadow-sm !rounded-full !top-[30%]">
                <svg className="absolute left-1/2 top-1/2 -translate-x-[45%] -translate-y-1/2 pointer-events-none" width="8" height="10" viewBox="0 0 8 10" fill="none"><path d="M8 5L0 10V0L8 5Z" fill="white" /></svg>
              </Handle>
              <Handle type="source" id="b" position={Position.Right} className="!w-[22px] !h-[22px] !bg-[#ec4899] !border-2 !border-white !shadow-sm !rounded-full !top-[70%]">
                <svg className="absolute left-1/2 top-1/2 -translate-x-[45%] -translate-y-1/2 pointer-events-none" width="8" height="10" viewBox="0 0 8 10" fill="none"><path d="M8 5L0 10V0L8 5Z" fill="white" /></svg>
              </Handle>
            </>
          ) : (
            <Handle type="source" position={Position.Right} className="!w-[22px] !h-[22px] !bg-blue-500 !border-2 !border-white !shadow-sm !rounded-full">
              <svg className="absolute left-1/2 top-1/2 -translate-x-[45%] -translate-y-1/2 pointer-events-none" width="8" height="10" viewBox="0 0 8 10" fill="none"><path d="M8 5L0 10V0L8 5Z" fill="white" /></svg>
            </Handle>
          )}
        </>
      )}
    </div>
  );
}

function renderPreview(d: FlowNodeData) {
  const type = d.meumisterioType;
  const config = d.config;

  if (type === 'conteudo') {
    const rawCards = config.contents;
    let cards = [];
    if (Array.isArray(rawCards) && rawCards.length > 0) {
      cards = rawCards;
    } else {
      const text = config.text || config.message;
      if (typeof text === 'string' && text) {
        cards = [{ type: 'text', value: text }];
      }
    }

    if (cards.length > 0) {
      /* Color map — filled backgrounds matching original Meu Mistério screenshots */
      const CARD_STYLES: Record<string, { border: string; bg: string; text: string }> = {
        text:     { border: '#93c5fd', bg: 'rgba(219,234,254,0.85)', text: '#1e3a8a' },
        delay:    { border: '#f9a8d4', bg: 'rgba(252,231,243,0.85)', text: '#9d174d' },
        image:    { border: '#7dd3fc', bg: 'rgba(224,242,254,0.85)', text: '#0369a1' },
        video:    { border: '#86efac', bg: 'rgba(220,252,231,0.85)', text: '#166534' },
        audio:    { border: '#c4b5fd', bg: 'rgba(237,233,254,0.85)', text: '#5b21b6' },
        document: { border: '#fdba74', bg: 'rgba(255,237,213,0.85)', text: '#c2410c' },
      };

      return (
        <div className="flex flex-col gap-2 w-full">
          {cards.map((c: any, i: number) => {
            const cs = CARD_STYLES[c.type] || CARD_STYLES.text;
            const iconClass = "w-4 h-4 shrink-0 mt-[1px] opacity-95";

            const cardStyle = {
              display: 'flex', alignItems: 'flex-start', gap: '8px',
              padding: '8px 10px', borderRadius: '10px',
              border: `2px dashed ${cs.border}`, background: cs.bg,
              color: cs.text, fontSize: '11px', fontWeight: 600, lineHeight: '1.4',
            };

            if (c.type === 'text') {
              const parts = (c.value || '').split(/(\{\{[^{}]+\}\})/g);
              return (
                <div key={i} style={{ ...cardStyle, fontWeight: 500 }}>
                  <Type className={iconClass} />
                  <div className="flex-1 min-w-0" style={{ display: '-webkit-box', WebkitLineClamp: 14, WebkitBoxOrient: 'vertical' as const, overflow: 'hidden', wordBreak: 'break-word' }}>
                    {parts.map((part: string, idx: number) => {
                       if (part.startsWith('{{') && part.endsWith('}}')) {
                          return (
                            <span key={idx} className="inline-block bg-[#10b981] text-white px-1.5 py-0 rounded font-bold text-[9px] tracking-wide align-middle leading-tight mt-[1px]">
                               {part}
                            </span>
                          );
                       }
                       return <span key={idx}>{part}</span>;
                    })}
                  </div>
                </div>
              );
            }
            if (c.type === 'delay') {
              return (
                <div key={i} style={cardStyle}>
                  <Clock className={iconClass} />
                  <div>Delay de {c.value || 0} Segundos</div>
                </div>
              );
            }
            if (c.type === 'image') {
              return (
                <div key={i} style={cardStyle}>
                  <ImageIcon className={iconClass} />
                  <div>Enviando uma imagem</div>
                </div>
              );
            }
            if (c.type === 'video') {
              return (
                <div key={i} style={cardStyle}>
                  <Video className={iconClass} />
                  <div>Enviando um vídeo</div>
                </div>
              );
            }
            if (c.type === 'audio') {
              return (
                <div key={i} style={cardStyle}>
                  <Mic className={iconClass} />
                  <div>Enviando um arquivo de áudio</div>
                </div>
              );
            }
            if (c.type === 'document') {
              return (
                <div key={i} style={cardStyle}>
                  <FileText className={iconClass} />
                  <div>Enviando um documento</div>
                </div>
              );
            }
            return null;
          })}
        </div>
      );
    }
    return (
       <div className="flex flex-col items-center justify-center gap-1.5 p-3 rounded-[10px] text-center" style={{ border: '2px dashed #e2e8f0', background: '#f8fafc' }}>
          <span className="text-2xl">😊</span>
          <span className="text-[11px] font-medium text-[#94a3b8]">Aguardando Configuração...</span>
       </div>
    );
  }

  if (type === 'pergunta') {
    const qText = stringField(config, 'question') || stringField(config, 'body') || stringField(config, 'question_text') || '';
    const saveRaw = stringField(config, 'save_to_flow_field') || stringField(config, 'output_var') || '';
    const saveKey = saveRaw.replace(/^\{\{|\}\}$/g, '').trim();
    const tSec = numberField(config, 'question_timeout_seconds');
    const sec = typeof tSec === 'number' && tSec > 0 ? tSec : 3600;
    const exLabel = sec < 3600 ? `${Math.round(sec / 60)} min` : sec < 86400 ? `${Math.round(sec / 3600)}h` : `${Math.round(sec / 86400)} dia${Math.round(sec / 86400) > 1 ? 's' : ''}`;
    
    const replyMode = stringField(config, 'reply_mode') || 'texto_livre';
    const quickReplies = Array.isArray(config.quick_replies) ? config.quick_replies as string[] : [];

    if (!qText.trim()) {
      return (
        <div className="flex flex-col items-center justify-center gap-1.5 p-3 rounded-[10px] text-center" style={{ border: '2px dashed #ff5722', background: '#fff8f5' }}>
          <HelpCircle className="w-5 h-5 text-[#ff5722] opacity-50" />
          <span className="text-[11px] font-medium text-[#94a3b8]">Aguardando Configuração...</span>
        </div>
      );
    }

    // Highlight {{variables}} in question text
    const parts = qText.split(/(\{\{[^}]+\}\})/g);

    return (
      <div className="flex flex-col gap-1 w-full">
         <div className="border border-dashed border-[#ff5722]/40 bg-[#fff8f5] rounded-lg p-2 flex flex-col gap-2 min-h-[30px]">
            <div className="flex items-start gap-1.5">
              <HelpCircle className="w-3.5 h-3.5 text-[#ff5722] shrink-0 mt-[1px]" />
              <div className="text-[10px] font-medium text-slate-600 leading-tight break-words line-clamp-3">
                 {parts.map((p, i) =>
                   /^\{\{.+\}\}$/.test(p)
                     ? <span key={i} className="bg-[#2563eb] text-white px-1 py-0.5 rounded text-[9px] font-mono mx-0.5">{p}</span>
                     : <span key={i}>{p}</span>
                 )}
              </div>
            </div>
            {replyMode === 'botoes' && quickReplies.length > 0 && (
              <div className="flex flex-col gap-1 mt-1">
                {quickReplies.map((r, i) => (
                  <div key={i} className="text-[9px] font-semibold text-[#10b981] bg-[#10b981]/10 border border-[#10b981]/20 rounded py-1 px-2 text-center w-full truncate">
                    {r || `Opção ${i + 1} vazia`}
                  </div>
                ))}
              </div>
            )}
         </div>
         {saveKey && (
           <div className="flex items-center gap-1 text-[9px] text-[#2563eb] font-medium">
              <span className="opacity-60">📦</span> Salvar em: <span className="bg-[#2563eb] text-white px-1 py-0.5 rounded text-[9px] font-mono">{`{{${saveKey}}}`}</span>
           </div>
         )}
         <div className="flex items-center gap-1 mt-0.5 text-red-500 text-[9px] font-semibold">
            <div className="w-1.5 h-1.5 rounded-full bg-red-500" /> Se não responder em {exLabel}
         </div>
      </div>
    );
  }

  if (type === 'acao') {
     const actionKind = stringField(config, 'action_type') || 'tag_add';
     const payload = stringField(config, 'action_payload');
     
     let actionText = 'Executar lógica';
     if (actionKind === 'tag_add') actionText = `Etiqueta ${payload || ''}`;
     else if (actionKind === 'close_chat') actionText = `Finalizar conversa com o contato`;
     else if (actionKind === 'assign_user') actionText = `Atribuir atendente ${payload || ''}`;
     
     return (
        <div className="p-1.5 rounded border border-[#2d336b]/20 text-center flex items-center justify-center min-h-[25px]">
           <div className="flex items-center gap-1 bg-[#10b981] text-white px-2 py-0.5 rounded-full text-[9px] font-bold">
              <PlayCircle className="w-2.5 h-2.5" />
              {actionText}
           </div>
        </div>
     );
  }

  if (type === 'condicao') {
    const rules = Array.isArray(config.rules) ? config.rules : [];
    const logic = config.logic || 'AND';
    const logicText = logic === 'OR' ? 'Pelo menos uma das condições é verdadeira' : 'Todas as condições são verdadeiras';
    
    return (
      <div className="flex flex-col gap-1 w-full">
        <div className="border border-dashed border-green-500 rounded p-1.5 flex flex-col items-center text-center gap-1.5 min-h-[40px] bg-white">
          <div className="text-[9px] font-semibold text-slate-500 leading-tight">
            {logicText}
          </div>
          <div className="w-full flex flex-col gap-1">
            {rules.length > 0 ? rules.slice(0, 2).map((r, i) => (
              <div key={i} className="text-[8.5px] font-medium text-green-700 bg-green-50 border border-green-200 border-dotted rounded px-1 py-0.5 break-words line-clamp-2">
                 O contato {r.op === 'not_equals' ? 'não' : ''} possui a etiqueta <span className="bg-green-600 text-white px-1 py-0.5 rounded font-bold">{r.value || 'vazio'}</span>
              </div>
            )) : (
              <div className="text-[8.5px] text-slate-400 border border-dotted rounded px-1 py-0.5">Sem regras</div>
            )}
          </div>
        </div>
        <div className="flex items-center gap-1 mt-1 text-red-500 text-[9px] font-semibold">
           <div className="w-1.5 h-1.5 rounded-full bg-red-500" /> Condições não foram cumpridas
        </div>
      </div>
    );
  }

  if (type === 'ab_split') {
    const wa = numberField(config, 'weight_a') ?? 50;
    const wb = numberField(config, 'weight_b') ?? 50;
    return (
      <div className="flex items-center w-full h-6 rounded overflow-hidden text-[10px] font-bold text-white shadow-inner">
        <div className="bg-fuchsia-500 h-full flex items-center justify-center transition-all" style={{ width: `${wa}%` }}>A: {wa}%</div>
        <div className="bg-fuchsia-300 text-fuchsia-900 h-full flex items-center justify-center transition-all" style={{ width: `${wb}%` }}>B: {wb}%</div>
      </div>
    );
  }

  if (type === 'api') {
    const method = stringField(config, 'method') || 'GET';
    const url = stringField(config, 'url') || 'URL não configurada';
    return (
      <div className="flex flex-col gap-1 bg-cyan-50 border border-cyan-200 rounded-lg p-2 text-[10px]">
        <div className="font-bold text-cyan-700">{method}</div>
        <div className="text-cyan-600 font-mono truncate">{url}</div>
      </div>
    );
  }

  if (type === 'gpt') {
    const prompt = config.prompt || config.system_prompt;
    if (typeof prompt === 'string' && prompt) {
      return (
        <div className="text-[10px] text-emerald-700 bg-emerald-50 p-2 rounded-lg border border-emerald-200 line-clamp-3 leading-relaxed">
          <span className="opacity-60 font-bold uppercase mr-1">IA:</span>
          {prompt}
        </div>
      );
    }
  }

  if (type === 'motor_ref') {
    const mod = stringField(config, 'module_hint') || '???';
    return (
      <div className="bg-rose-50 border border-rose-200 rounded p-2 text-[10px] font-mono text-rose-700 flex flex-col gap-1">
         <span className="font-bold uppercase text-[9px] opacity-70">Executar Módulo:</span>
         <span className="truncate">{mod}</span>
      </div>
    );
  }

  if (type === 'anotacao') {
    const note = stringField(config, 'note');
    return (
      <div className="bg-yellow-50 text-yellow-800 p-2 rounded-lg text-[11px] font-medium italic border border-yellow-200 line-clamp-4 leading-relaxed whitespace-pre-wrap">
        {note || 'Clique para adicionar nota...'}
      </div>
    );
  }

  return null;
}

function renderConfigHint(d: FlowNodeData) {
  // Ignora hint visual de delay/module_hint pois já temos previews completos acima para motor_ref e delay (dentro de conteudo).
  // Mostramos apenas hints pequenos genéricos se precisar.
  return null;
}

function stringField(o: Record<string, unknown>, k: string): string | null {
  const v = o[k];
  if (typeof v === 'string' && v.trim()) return v;
  return null;
}

function numberField(o: Record<string, unknown>, k: string): number | null {
  const v = o[k];
  if (typeof v === 'number' && Number.isFinite(v)) return v;
  return null;
}
