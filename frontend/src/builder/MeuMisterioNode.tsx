import { Handle, Position, useReactFlow, type Node, type NodeProps } from '@xyflow/react';
import { 
  AlertCircle, AlertTriangle, MoreHorizontal, MessageSquare, 
  HelpCircle, PlayCircle, Clock, Image as ImageIcon, Video, Mic, FileText, Type,
  Copy, SquarePen, Smile
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
    const triggerEvent = stringField(d.config, 'event') || 'keyword';
    const triggerDescription =
      triggerEvent === 'purchase'
        ? 'Compra aprovada'
        : triggerEvent === 'abandon'
          ? 'Carrinho abandonado'
          : triggerEvent === 'message_received' || triggerEvent === 'mensagem_recebida'
            ? 'Mensagem recebida'
            : triggerEvent === 'inicio_conversa'
              ? 'Início de conversa'
              : 'Enviou palavra-chave';
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
            {triggerDescription}
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
          {triggerEvent === 'keyword' || triggerEvent === 'palavra_chave'
            ? stringField(d.config, 'keyword') || 'Qualquer mensagem'
            : triggerDescription}
        </div>
        
        <Handle type="source" position={Position.Right} className="!w-5 !h-5 !bg-white !border-2 !border-blue-500 !shadow-sm !rounded-full after:content-[''] after:absolute after:left-1/2 after:top-1/2 after:w-0 after:h-0 after:border-solid after:border-[4px_0_4px_7px] after:border-[transparent_transparent_transparent_#fff] after:-translate-x-1/2 after:-translate-y-1/2" />
      </div>
    );
  }

  // --- STANDARD NODES (Conteudo, Pergunta, Acao, etc) ---
  const TYPE_COLORS: Record<string, { bg: string, text: string, border: string }> = {
    conteudo: { bg: 'bg-[#7c3aed]', text: 'text-[#7c3aed]', border: 'border-[#7c3aed]' },
    pergunta: { bg: 'bg-[#ea580c]', text: 'text-[#ea580c]', border: 'border-[#ea580c]' },
    acao: { bg: 'bg-[#3730a3]', text: 'text-[#3730a3]', border: 'border-[#3730a3]' },
    condicao: { bg: 'bg-[#dc2626]', text: 'text-[#dc2626]', border: 'border-[#dc2626]' },
    ab_split: { bg: 'bg-[#db2777]', text: 'text-[#db2777]', border: 'border-[#db2777]' },
    menu: { bg: 'bg-[#0f766e]', text: 'text-[#0f766e]', border: 'border-[#0f766e]' },
    expediente: { bg: 'bg-[#c4b53f]', text: 'text-[#c4b53f]', border: 'border-[#c4b53f]' },
    notificar_atendente: { bg: 'bg-[#2563eb]', text: 'text-[#2563eb]', border: 'border-[#2563eb]' },
    api: { bg: 'bg-[#0891b2]', text: 'text-[#0891b2]', border: 'border-[#0891b2]' },
    gpt: { bg: 'bg-[#16a34a]', text: 'text-[#16a34a]', border: 'border-[#16a34a]' },
    agente_ia: { bg: 'bg-[#7e22ce]', text: 'text-[#7e22ce]', border: 'border-[#7e22ce]' },
    voice_studio: { bg: 'bg-[#e11d48]', text: 'text-[#e11d48]', border: 'border-[#e11d48]' },
    divisao: { bg: 'bg-[#db2777]', text: 'text-[#db2777]', border: 'border-[#db2777]' },
    delay: { bg: 'bg-[#475569]', text: 'text-[#475569]', border: 'border-[#475569]' },
    integration: { bg: 'bg-[#0891b2]', text: 'text-[#0891b2]', border: 'border-[#0891b2]' },
    anotacao: { bg: 'bg-[#ca8a04]', text: 'text-[#ca8a04]', border: 'border-[#ca8a04]' },
    motor_ref: { bg: 'bg-[#be123c]', text: 'text-[#be123c]', border: 'border-[#be123c]' },
  };

  const nodeColors = TYPE_COLORS[type] || { bg: 'bg-[#475569]', text: 'text-[#475569]', border: 'border-[#475569]' };
  
  const headerBg = nodeColors.bg;
  const headerText = 'text-white';
  const iconColor = nodeColors.text;
  const iconBg = 'bg-white';
  const bodyBg = 'bg-white';
  const borderColor = nodeColors.border;

  // Simulate a random traffic count for visual parity with the screenshot
  const trafficCount = numberField(d.config, 'stats_count');

  return (
    <div
      className={[
        `rounded-[10px] border-[1.5px] min-w-[280px] max-w-[320px] shadow-sm relative font-sans transition-all duration-300`,
        'border-slate-500',
        bodyBg,
        d.simActive ? 'ring-2 ring-emerald-500 shadow-glow-emerald animate-pulse' : '',
        !d.simActive && selected ? `ring-2 ring-accent-amethyst shadow-glow-amethyst` : '',
        !d.simActive && d.lintLevel === 'error' ? 'ring-2 ring-red-500' : '',
      ].join(' ')}
    >
      {/* Traffic Stats Pill - Só renderiza se a stat for explícita e maior que 0 */}
      {trafficCount !== null && trafficCount > 0 && (
        <div className="absolute -top-[10px] left-1/2 -translate-x-1/2 z-30">
          <div className="bg-[#9333ea] text-white text-[10px] font-bold px-2 py-0.5 rounded-full shadow-sm leading-none border border-[#7e22ce]">
            {trafficCount}
          </div>
        </div>
      )}

      {/* Validation badge removed to strictly match the clean design */}

      {/* Header — icon + label + Copy + Edit buttons */}
      <div className={[`flex items-stretch justify-between rounded-t-[8px] overflow-hidden`, headerBg].join(' ')}>
        <div className="flex items-center gap-2.5 px-3 py-2.5 overflow-hidden">
          <div className="flex items-center justify-center shrink-0">
            <v.Icon className="w-4 h-4 text-white" strokeWidth={2.5} />
          </div>
          <span className={[`text-[13px] font-bold tracking-tight truncate capitalize`, headerText].join(' ')}>
            {d.label || v.label}
          </span>
        </div>
        <div className="flex items-stretch bg-black/10">
          <div
            className="flex items-center justify-center w-[36px] hover:bg-black/20 transition-colors cursor-pointer border-r border-black/10"
            title="Duplicar"
            onClick={(e) => {
              e.stopPropagation();
              d.onDuplicate?.();
            }}
          >
            <Copy className="w-4 h-4 text-white" />
          </div>
          <div
            className="flex items-center justify-center w-[36px] hover:bg-black/20 transition-colors cursor-pointer"
            title="Editar"
            onClick={(e) => {
              e.stopPropagation();
              d.onEdit?.();
            }}
          >
            <SquarePen className="w-4 h-4 text-white" />
          </div>
        </div>
      </div>

      {/* Body */}
      <div className="p-3 flex flex-col gap-2 rounded-b-[8px]">
         {renderPreview(d)}
         {renderConfigHint(d)}
      </div>

      {/* Input Handle — white circle with purple border + ▶ play arrow */}
      {!isTrigger && (
        <Handle
          type="target"
          position={Position.Left}
          className="!w-[16px] !h-[16px] !bg-white !shadow-sm !rounded-full"
          style={{ border: '2px solid #7e22ce' }}
        >
          <svg className="absolute left-1/2 top-1/2 -translate-x-[45%] -translate-y-1/2 pointer-events-none" width="6" height="8" viewBox="0 0 8 10" fill="none">
            <path d="M8 5L0 10V0L8 5Z" fill="#7e22ce" />
          </svg>
        </Handle>
      )}

      {/* Output Handles — filled circle with white ▶ play arrow */}
      {!isEnd && (
        <>
          {type === 'condicao' ? (
            <></> /* Handles renderizados inline no renderPreview */
          ) : type === 'pergunta' ? (
            <></> /* Handles renderizados inline no renderPreview */
          ) : type === 'ab_split' ? (
            <></> /* Handles renderizados inline no renderPreview */
          ) : type === 'gpt' || type === 'api' || type === 'integration' ? (
            <>
              <Handle type="source" id="sucesso" position={Position.Right} className="!w-[16px] !h-[16px] !bg-blue-500 !border-2 !border-white !shadow-sm !rounded-full !top-[40%]">
                <svg className="absolute left-1/2 top-1/2 -translate-x-[45%] -translate-y-1/2 pointer-events-none" width="6" height="8" viewBox="0 0 8 10" fill="none"><path d="M8 5L0 10V0L8 5Z" fill="white" /></svg>
              </Handle>
              <Handle type="source" id="erro" position={Position.Right} className="!w-[16px] !h-[16px] !bg-red-500 !border-2 !border-white !shadow-sm !rounded-full !top-[85%]">
                <svg className="absolute left-1/2 top-1/2 -translate-x-[45%] -translate-y-1/2 pointer-events-none" width="6" height="8" viewBox="0 0 8 10" fill="none"><path d="M8 5L0 10V0L8 5Z" fill="white" /></svg>
              </Handle>
            </>
          ) : type === 'agente_ia' ? (
            <></> // Handles renderizados inline no renderPreview
          ) : type === 'voice_studio' ? (
            <>
              <Handle type="source" id="sucesso" position={Position.Right} className="!w-[16px] !h-[16px] !bg-blue-500 !border-2 !border-white !shadow-sm !rounded-full !top-[50%]">
                <svg className="absolute left-1/2 top-1/2 -translate-x-[45%] -translate-y-1/2 pointer-events-none" width="6" height="8" viewBox="0 0 8 10" fill="none"><path d="M8 5L0 10V0L8 5Z" fill="white" /></svg>
              </Handle>
              <Handle type="source" id="erro" position={Position.Right} className="!w-[16px] !h-[16px] !bg-red-500 !border-2 !border-white !shadow-sm !rounded-full !top-[85%]">
                <svg className="absolute left-1/2 top-1/2 -translate-x-[45%] -translate-y-1/2 pointer-events-none" width="6" height="8" viewBox="0 0 8 10" fill="none"><path d="M8 5L0 10V0L8 5Z" fill="white" /></svg>
              </Handle>
            </>
          ) : type === 'menu' || type === 'expediente' ? (
            <></> // Handles renderizados inline no renderPreview
          ) : (
            <Handle type="source" position={Position.Right} className="!w-[16px] !h-[16px] !bg-blue-500 !border-2 !border-white !shadow-sm !rounded-full">
              <svg className="absolute left-1/2 top-1/2 -translate-x-[45%] -translate-y-1/2 pointer-events-none" width="6" height="8" viewBox="0 0 8 10" fill="none">
                <path d="M8 5L0 10V0L8 5Z" fill="white" />
              </svg>
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
    return <EmptyPlaceholder />;
  }

  if (type === 'expediente') {
    const tz = stringField(config, 'timezone') || 'America/Sao_Paulo';
    
    const defaultDays = [
      { name: 'Domingo', active: false, intervals: [{ start: '', end: '' }] },
      { name: 'Segunda-feira', active: false, intervals: [{ start: '', end: '' }] },
      { name: 'Terça-feira', active: false, intervals: [{ start: '', end: '' }] },
      { name: 'Quarta-feira', active: false, intervals: [{ start: '', end: '' }] },
      { name: 'Quinta-feira', active: false, intervals: [{ start: '', end: '' }] },
      { name: 'Sexta-feira', active: false, intervals: [{ start: '', end: '' }] },
      { name: 'Sábado', active: false, intervals: [{ start: '', end: '' }] },
    ];
    const days = Array.isArray(config.days) && config.days.length === 7 ? config.days : defaultDays;
    
    return (
      <div className="flex flex-col w-full relative">
        {/* Fuso Horário Block - Top Handle (Sucesso) */}
        <div className="relative flex items-center justify-between px-3 py-2 border border-slate-200 rounded-lg bg-white mb-2 shadow-sm">
           <div className="flex items-start gap-2.5">
              <div className="mt-0.5 text-slate-400">
                 <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"></circle><line x1="2" y1="12" x2="22" y2="12"></line><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"></path></svg>
              </div>
              <div className="flex flex-col">
                 <span className="text-[11px] text-slate-500 font-medium">Fuso Horário:</span>
                 <span className="text-[12px] text-slate-700 font-bold leading-tight">{tz}</span>
              </div>
           </div>
           <span className="text-[10px] text-blue-500 font-semibold self-end">Alterar</span>
           
           <Handle type="source" id="sucesso" position={Position.Right} className="!absolute !w-[16px] !h-[16px] !bg-[#6366f1] !border-2 !border-white !shadow-sm !rounded-full !top-1/2 !-translate-y-1/2 !-right-[20px] z-10">
             <svg className="absolute left-1/2 top-1/2 -translate-x-[40%] -translate-y-1/2 pointer-events-none" width="6" height="8" viewBox="0 0 8 10" fill="none"><path d="M8 5L0 10V0L8 5Z" fill="white" /></svg>
           </Handle>
        </div>

        {/* Listagem de Dias */}
        <div className="flex flex-col gap-1.5 mb-2">
           {days.map((day: any, i: number) => {
              const active = day.active;
              return (
                 <div key={i} className={`flex items-center justify-between px-3 py-2 border ${active ? 'border-dashed border-blue-300' : 'border-dashed border-slate-300'} rounded-lg bg-white`}>
                    <div className="flex items-center gap-2">
                       <div className={active ? "text-blue-500" : "text-slate-400"}>
                          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="3" y="4" width="18" height="18" rx="2" ry="2"></rect><line x1="16" y1="2" x2="16" y2="6"></line><line x1="8" y1="2" x2="8" y2="6"></line><line x1="3" y1="10" x2="21" y2="10"></line><path d="m9 16 2 2 4-4"></path></svg>
                       </div>
                       <span className="text-[12px] font-medium text-slate-700">{day.name}</span>
                    </div>
                    {active ? (
                       <div className="px-3 py-0.5 bg-blue-50 text-blue-600 text-[11px] font-bold rounded-full">
                          {day.intervals?.[0]?.start || '00:00'} - {day.intervals?.[0]?.end || '23:59'}
                       </div>
                    ) : (
                       <div className="px-3 py-0.5 bg-slate-100 text-slate-500 text-[11px] font-bold rounded-full">
                          Inativo
                       </div>
                    )}
                 </div>
              );
           })}
        </div>

        {/* Footer Block - Bottom Handle (Erro) */}
        <div className="relative flex items-center gap-2 px-3 py-2 border border-slate-100 rounded-lg bg-slate-50 mt-1 shadow-sm">
           <div className="text-blue-500">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="16" x2="12" y2="12"></line><line x1="12" y1="8" x2="12.01" y2="8"></line></svg>
           </div>
           <span className="text-[11px] text-slate-600 font-bold">Caminho alternativo fora do horário.</span>
           
           <Handle type="source" id="erro" position={Position.Right} className="!absolute !w-[16px] !h-[16px] !bg-red-500 !border-2 !border-white !shadow-sm !rounded-full !top-1/2 !-translate-y-1/2 !-right-[20px] z-10">
             <svg className="absolute left-1/2 top-1/2 -translate-x-[40%] -translate-y-1/2 pointer-events-none" width="6" height="8" viewBox="0 0 8 10" fill="none"><path d="M8 5L0 10V0L8 5Z" fill="white" /></svg>
           </Handle>
        </div>
      </div>
    );
  }

  if (type === 'pergunta') {
    const qText = stringField(config, 'question') || stringField(config, 'body') || stringField(config, 'question_text') || '';
    if (!qText.trim()) return <EmptyPlaceholder />;

    const saveRaw = stringField(config, 'save_to_flow_field') || stringField(config, 'output_var') || '';
    const saveKey = saveRaw.replace(/^\{\{|\}\}$/g, '').trim();
    const tSec = numberField(config, 'question_timeout_seconds');
    const sec = typeof tSec === 'number' && tSec > 0 ? tSec : 3600;
    const exLabel = sec < 3600 ? `${Math.round(sec / 60)} min` : sec < 86400 ? `${Math.round(sec / 3600)}h` : `${Math.round(sec / 86400)} dia${Math.round(sec / 86400) > 1 ? 's' : ''}`;
    
    const replyMode = stringField(config, 'reply_mode') || 'texto_livre';
    const quickReplies = Array.isArray(config.quick_replies) ? config.quick_replies as string[] : [];

    // Se for só espaços ou vazia, ainda renderiza a base do node para suportar o caso de "apenas pause"
    const isEmpty = !qText.trim();
    const parts = isEmpty ? [] : qText.split(/(\{\{[^}]+\}\})/g);

    return (
      <div className="flex flex-col gap-1 w-full bg-white rounded-lg p-1.5 border border-slate-100">
         <div className="border border-dashed border-[#ff5722]/40 bg-[#fff8f5] rounded-lg p-2 flex flex-col gap-2 min-h-[30px]">
            <div className="flex items-start gap-1.5">
              <span className="text-[#ff5722] font-bold text-[11px] shrink-0 mt-[1px]">?</span>
              <div className="text-[10px] font-medium text-slate-600 leading-tight break-words line-clamp-3">
                 {isEmpty && !saveKey && (
                    <span className="text-slate-400 italic">Pausa ativada (sem texto)</span>
                 )}
                 {!isEmpty && parts.map((p, i) =>
                   /^\{\{.+\}\}$/.test(p)
                     ? <span key={i} className="bg-[#4c1d95] text-white px-1 py-0.5 rounded text-[9px] font-mono mx-0.5">{p}</span>
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
            
            {saveKey && (
              <div className="flex items-center gap-1 text-[9px] text-slate-600 font-medium mt-1">
                 Salvar em: <span className="bg-[#4c1d95] text-white px-1 py-0.5 rounded text-[9px] font-mono">{`{{${saveKey}}}`}</span>
              </div>
            )}
            <Handle type="source" id="resposta" position={Position.Right} className="!absolute !w-[16px] !h-[16px] !bg-blue-500 !border-2 !border-white !shadow-sm !rounded-full !top-1/2 !-translate-y-1/2 !-right-2">
               <svg className="absolute left-1/2 top-1/2 -translate-x-[40%] -translate-y-1/2 pointer-events-none" width="6" height="8" viewBox="0 0 8 10" fill="none"><path d="M8 5L0 10V0L8 5Z" fill="white" /></svg>
            </Handle>
         </div>
         <div className="flex items-center gap-1 mt-0.5 text-red-500 text-[9px] font-semibold pt-1 border-t border-slate-100 relative">
            <div className="w-1.5 h-1.5 rounded-full bg-red-500" /> Resposta após {exLabel}: expirada
            <Handle type="source" id="timeout" position={Position.Right} className="!absolute !w-[16px] !h-[16px] !bg-red-500 !border-2 !border-white !shadow-sm !rounded-full !top-1/2 !-translate-y-1/2 !-right-2">
               <svg className="absolute left-1/2 top-1/2 -translate-x-[40%] -translate-y-1/2 pointer-events-none" width="6" height="8" viewBox="0 0 8 10" fill="none"><path d="M8 5L0 10V0L8 5Z" fill="white" /></svg>
            </Handle>
         </div>
      </div>
    );
  }

  if (type === 'acao') {
     const actionKind = stringField(config, 'action_type');
     if (!actionKind && Object.keys(config).length === 0) return <EmptyPlaceholder />;

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
    if (rules.length === 0 && Object.keys(config).length === 0) return <EmptyPlaceholder />;

    const logic = config.logic || 'AND';
    const logicText = logic === 'OR' ? 'Qualquer condição é verdadeira:' : 'Todas as condições são verdadeiras:';
    
    return (
      <div className="flex flex-col gap-1 w-full bg-white rounded-lg p-1.5 border border-slate-100">
        <div className="border border-dashed border-[#ef4444]/40 bg-[#fff1f2] rounded p-2 flex flex-col items-center text-center gap-2 min-h-[40px]">
          <div className="text-[10px] font-semibold text-slate-600 leading-tight w-full flex items-center justify-between">
            {logicText}
            <Handle type="source" id="true" position={Position.Right} className="!absolute !w-[16px] !h-[16px] !bg-blue-600 !border-2 !border-white !shadow-sm !rounded-full !top-5 !-right-2 z-10">
               <svg className="absolute left-1/2 top-1/2 -translate-x-[40%] -translate-y-1/2 pointer-events-none" width="6" height="8" viewBox="0 0 8 10" fill="none"><path d="M8 5L0 10V0L8 5Z" fill="white" /></svg>
            </Handle>
          </div>
          <div className="w-full flex flex-col gap-1">
            {rules.length > 0 ? rules.slice(0, 2).map((r, i) => (
              <div key={i} className="flex flex-col gap-1 items-center justify-center">
                 <div className="text-[9px] font-medium text-slate-500 bg-white border border-slate-200 border-dashed rounded px-2 py-1">
                    Validar se o campo de fluxo <span className="font-bold">{r.var || '?'}</span> é igual a
                 </div>
                 <div className="bg-[#10b981] text-white px-3 py-0.5 rounded-full text-[10px] font-bold shadow-sm">
                    {r.value || 'vazio'}
                 </div>
              </div>
            )) : (
              <div className="text-[9px] text-slate-400 border border-dotted rounded px-1 py-0.5">Sem condições</div>
            )}
          </div>
        </div>
        <div className="flex items-center gap-1 mt-0.5 text-red-500 text-[9px] font-semibold relative pt-1 border-t border-slate-100">
           <div className="w-1.5 h-1.5 rounded-full bg-red-500" /> Condições não foram cumpridas
           <Handle type="source" id="false" position={Position.Right} className="!absolute !w-[16px] !h-[16px] !bg-red-500 !border-2 !border-white !shadow-sm !rounded-full !top-1/2 !-translate-y-1/2 !-right-2 z-10">
               <svg className="absolute left-1/2 top-1/2 -translate-x-[40%] -translate-y-1/2 pointer-events-none" width="6" height="8" viewBox="0 0 8 10" fill="none"><path d="M8 5L0 10V0L8 5Z" fill="white" /></svg>
           </Handle>
        </div>
      </div>
    );
  }

  if (type === 'ab_split') {
    if (Object.keys(config).length === 0) return <EmptyPlaceholder />;
    
    let weights: number[] = [];
    if (Array.isArray(config.weights)) {
      weights = config.weights as number[];
    } else if (config.weight_a !== undefined && config.weight_b !== undefined) {
      weights = [Number(config.weight_a), Number(config.weight_b)];
    } else {
      weights = [50, 50];
    }
    const stats = config.ab_stats as any;

    return (
      <div className="flex flex-col gap-1.5 w-full">
        {weights.map((w, i) => {
          const variantId = String.fromCharCode(97 + i); // a, b, c...
          const variantLabel = String.fromCharCode(65 + i); // A, B, C...
          
          return (
            <div key={variantId} className="relative flex items-center justify-between px-3 py-2.5 border border-dashed border-slate-300 rounded-lg bg-white">
              <span className="text-[12px] font-medium text-slate-600">T{i + 1}</span>
              <div className="px-3 py-0.5 bg-slate-50 text-blue-500 text-[11px] font-bold rounded-full">
                {w % 1 === 0 ? w : w.toFixed(1)}%
              </div>
              
              <Handle type="source" id={variantId} position={Position.Right} className="!absolute !w-[16px] !h-[16px] !bg-[#6366f1] !border-2 !border-white !shadow-sm !rounded-full !top-1/2 !-translate-y-1/2 !-right-[20px] z-10">
                <svg className="absolute left-1/2 top-1/2 -translate-x-[40%] -translate-y-1/2 pointer-events-none" width="6" height="8" viewBox="0 0 8 10" fill="none"><path d="M8 5L0 10V0L8 5Z" fill="white" /></svg>
              </Handle>
              
              {/* Typebot-style Winner & Revenue insight */}
              {stats && stats[variantLabel] && (
                <div className="absolute left-full ml-6 top-1/2 -translate-y-1/2 whitespace-nowrap bg-white border border-slate-200 rounded px-1.5 py-0.5 text-[9px] font-bold text-slate-600 shadow-sm flex flex-col gap-0 animate-fade-in pointer-events-none z-50">
                   <div className="flex items-center gap-1">
                     <span className="text-slate-400">👁️</span> {stats[variantLabel].impressions}
                   </div>
                   <div className="text-emerald-600 flex items-center gap-1">
                     <span className="text-emerald-500">💰</span> {stats[variantLabel].conversions} ({stats[variantLabel].rate}%)
                   </div>
                </div>
              )}
            </div>
          );
        })}
        
        {stats && stats.winner && (
          <div className="flex flex-col gap-1.5 mt-1 border-t border-slate-100 pt-2">
            <div className="flex items-center justify-center gap-1.5 bg-emerald-50 text-emerald-700 text-[10px] font-bold py-1.5 rounded-lg border border-emerald-200 shadow-sm animate-pulse">
              <span>🏆</span> Variante {stats.winner} está Vencendo!
            </div>
            
            {stats.total_revenue > 0 && (
              <div className="flex justify-between items-center text-[10px] font-bold px-1">
                <span className="text-slate-400 uppercase tracking-wider text-[8px]">Receita do Teste</span>
                <span className="text-emerald-600 bg-emerald-100/50 px-1.5 py-0.5 rounded">
                  R$ {stats.total_revenue?.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}
                </span>
              </div>
            )}
          </div>
        )}
      </div>
    );
  }

  if (type === 'api') {
    const url = stringField(config, 'url');
    if (!url && Object.keys(config).length === 0) return <EmptyPlaceholder />;

    const method = stringField(config, 'method') || 'GET';
    return (
      <div className="flex flex-col gap-1 bg-cyan-50 border border-cyan-200 rounded-lg p-2 text-[10px]">
        <div className="font-bold text-cyan-700">{method}</div>
        <div className="text-cyan-600 font-mono truncate">{url}</div>
      </div>
    );
  }

  if (type === 'gpt') {
    const prompt = stringField(config, 'prompt') || stringField(config, 'system_prompt');
    if (!prompt && Object.keys(config).length === 0) return <EmptyPlaceholder />;

    const finalPrompt = prompt || 'Analise a conversa, nela a cliente disse seu nome, retorne apenas o primeiro nome, em uma palavra. Ex: Joao, Maria, Pedro, etc.';
    const configuredModel = stringField(config, 'model');
    const model = configuredModel?.startsWith('gemini-')
      ? configuredModel
      : 'gemini-2.5-flash';
    const temp = numberField(config, 'temperature') || 0.1;
    const maxTokens = numberField(config, 'max_tokens') || 10;
    const saveAs = stringField(config, 'save_as') || 'GPT_NomeLead';

    return (
      <div className="flex flex-col gap-1 w-full bg-white rounded-lg p-2 border border-slate-100">
        <div className="text-[9px] text-slate-500 mb-0.5">Prompt a ser executado:</div>
        <div className="text-[10px] text-slate-700 bg-slate-100 p-2 rounded-lg border border-slate-200 line-clamp-4 leading-relaxed mb-1">
          {finalPrompt}
        </div>
        
        <div className="flex flex-wrap items-center justify-center gap-1.5 mt-1">
           <span className="bg-[#22c55e] text-white px-2 py-0.5 rounded-full text-[8.5px] font-bold">Modelo: {model}</span>
           <span className="bg-[#22c55e] text-white px-2 py-0.5 rounded-full text-[8.5px] font-bold">Temperatura: {temp}</span>
        </div>
        <div className="flex flex-wrap items-center justify-center gap-1.5 mt-0.5">
           <span className="bg-[#22c55e] text-white px-2 py-0.5 rounded-full text-[8.5px] font-bold">Max. Tokens: {maxTokens}</span>
           <span className="bg-[#22c55e] text-white px-2 py-0.5 rounded-full text-[8.5px] font-bold">Contexto</span>
        </div>

        <div className="mt-1.5 flex justify-center">
           <span className="bg-slate-800 text-white px-2 py-0.5 rounded-full text-[9px] font-bold shadow-sm">
             Salvar em: {`{{${saveAs}}}`}
           </span>
        </div>

        <div className="flex items-center gap-1 mt-2 text-red-500 text-[9px] font-semibold border-t border-slate-100 pt-1.5">
           <div className="w-1.5 h-1.5 rounded-full bg-red-500" /> Erro ao gerar mensagem
        </div>
      </div>
    );
  }

  if (type === 'delay') {
    const mode = stringField(config, 'mode') || 'fixo';
    const val = numberField(config, 'seconds') ?? 6;
    const maxInt = numberField(config, 'seconds_max') ?? 15;
    
    return (
      <div className="flex flex-col gap-1 w-full bg-white rounded-lg p-1.5 border border-slate-100">
         <div className="border border-slate-200 bg-slate-50 rounded p-2 flex flex-col gap-2 min-h-[40px]">
            <div className="flex items-center gap-1.5 text-[10px] font-bold text-slate-600">
               <Clock className="w-3.5 h-3.5 text-slate-500" />
               Aguardar o prazo de {mode === 'fixo' ? `${val} segundos` : `${val} a ${maxInt} segundos`}
            </div>
            
            <div className="flex items-center gap-1.5 border-t border-slate-200 pt-1.5 pl-1 text-[9px] font-medium text-slate-500">
               <div className="w-1 h-3 rounded-full bg-blue-500" />
               Após esse tempo o fluxo prosseguirá.
            </div>
         </div>
      </div>
    );
  }

  if (type === 'menu') {
    const options = Array.isArray(config.options) ? config.options as string[] : [];
    if (options.length === 0) return <EmptyPlaceholder />;

    return (
      <div className="flex flex-col gap-1 w-full bg-white rounded-lg p-1.5 border border-slate-100">
        <div className="border border-slate-200 bg-slate-50 rounded p-1.5 flex flex-col gap-1 relative">
          {options.map((opt, i) => (
            <div key={i} className="relative flex items-center justify-center p-1.5 bg-white border border-slate-200 rounded text-[10px] font-semibold text-slate-700 shadow-sm min-h-[28px]">
              <span className="truncate max-w-[90%]">{opt || `Opção ${i + 1}`}</span>
              <Handle 
                type="source" 
                id={`opt_${i}`} 
                position={Position.Right} 
                className="!absolute !w-[16px] !h-[16px] !bg-blue-500 !border-2 !border-white !shadow-sm !rounded-full !-right-4 !top-1/2 !-translate-y-1/2 !transform-none"
              >
                <svg className="absolute left-1/2 top-1/2 -translate-x-[45%] -translate-y-1/2 pointer-events-none" width="6" height="8" viewBox="0 0 8 10" fill="none"><path d="M8 5L0 10V0L8 5Z" fill="white" /></svg>
              </Handle>
            </div>
          ))}
        </div>
      </div>
    );
  }

  if (type === 'agente_ia') {
    if (Object.keys(config).length === 0) return <EmptyPlaceholder />;

    return (
      <div className="flex flex-col gap-1 w-full bg-white rounded-lg p-1.5 border border-slate-100">
        <div className="relative border border-dashed border-[#8b5cf6] text-[#8b5cf6] font-bold text-[10px] text-center py-1.5 rounded-lg bg-[#8b5cf6]/5">
          AVANÇAR
          <Handle type="source" id="avancar" position={Position.Right} className="!absolute !w-[16px] !h-[16px] !bg-blue-500 !border-2 !border-white !shadow-sm !rounded-full !top-1/2 !-translate-y-1/2 !-right-2.5">
            <svg className="absolute left-1/2 top-1/2 -translate-x-[40%] -translate-y-1/2 pointer-events-none" width="6" height="8" viewBox="0 0 8 10" fill="none"><path d="M8 5L0 10V0L8 5Z" fill="white" /></svg>
          </Handle>
        </div>
        <div className="flex flex-col gap-1 text-red-500 text-[9px] font-semibold border-t border-slate-100 pt-1.5 px-0.5 mt-1.5">
           <div className="relative flex items-center gap-1">
             <div className="w-1.5 h-1.5 rounded-full bg-red-500" /> Erro ao gerar mensagem
             <Handle type="source" id="erro" position={Position.Right} className="!absolute !w-[16px] !h-[16px] !bg-red-500 !border-2 !border-white !shadow-sm !rounded-full !top-1/2 !-translate-y-1/2 !-right-2">
               <svg className="absolute left-1/2 top-1/2 -translate-x-[40%] -translate-y-1/2 pointer-events-none" width="6" height="8" viewBox="0 0 8 10" fill="none"><path d="M8 5L0 10V0L8 5Z" fill="white" /></svg>
             </Handle>
           </div>
        </div>
      </div>
    );
  }

  if (type === 'voice_studio') {
    if (!stringField(config, 'script') && Object.keys(config).length === 0) return <EmptyPlaceholder />;
    
    return (
       <div className="flex flex-col gap-1 w-full relative">
         <div className="flex flex-col items-start gap-1.5 p-2 rounded-lg border border-slate-200 bg-slate-50 mt-1">
            <span className="text-[10px] font-bold text-slate-500">Texto do Áudio:</span>
            <div className="text-[10px] text-slate-600 line-clamp-3 leading-relaxed">
              {stringField(config, 'script')}
            </div>
         </div>
         <div className="flex items-center gap-1 mt-0.5 text-red-500 text-[9px] font-semibold pt-1">
            <div className="w-1.5 h-1.5 rounded-full bg-red-500" /> Erro ao gerar mensagem
         </div>
       </div>
    );
  }

  if (type === 'expediente') {
    if (Object.keys(config).length === 0) return <EmptyPlaceholder />;
  }

  if (type === 'notificar_atendente') {
    if (Object.keys(config).length === 0) return <EmptyPlaceholder />;
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

function EmptyPlaceholder() {
  return (
    <div className="flex flex-col items-center justify-center gap-2 py-6 min-h-[110px]">
      <Smile className="w-10 h-10 text-slate-500" strokeWidth={1.5} />
      <span className="text-[13px] font-medium text-slate-500">Aguardando Configuração...</span>
    </div>
  );
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
