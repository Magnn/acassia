import React, { useState, useRef } from 'react';
import { useEffect } from 'react';
import { ChevronDown, Trash2, Send, Info, X, Check, Terminal, Copy, Download, Eye } from 'lucide-react';
import { Field, NumberInput, Select, TextArea, TextInput } from './fields';
import { patchConfig, readNum, readStr, type InspectorProps } from './helpers';
import CardList from './conteudo/CardList';
import { type Card, cardId } from './conteudo/types';
import RuleBuilder, { type Logic, type Rule } from './condicao/RuleBuilder';
import { blueprintsApi, type BlueprintSummary } from '../api/blueprints';

// ─── Header comum ─────────────────────────────────────────────────────

export function CommonHeader({ node, onUpdate }: InspectorProps) {
  return (
    <div className="space-y-3">
      <Field label="Rótulo">
        <TextInput
          value={node.data.label}
          onChange={(v) => onUpdate({ label: v })}
          placeholder="Ex.: Mensagem de boas-vindas"
        />
      </Field>
      <Field label="Step name" hint="usado nos logs do motor">
        <TextInput
          value={readStr(node.data.config, 'step_name')}
          onChange={(v) => onUpdate(patchConfig(node, { step_name: v }))}
          placeholder="Ex.: B1 — entrada"
        />
      </Field>
    </div>
  );
}

// ─── Inspetores por tipo ──────────────────────────────────────────────

export function TriggerInspector({ node, onUpdate }: InspectorProps) {
  const cfg = node.data.config;
  const integration = readStr(cfg, 'integration') || 'whatsapp';
  const isWhatsApp = integration === 'whatsapp';
  const rawEvent = readStr(cfg, 'event') || 'keyword';
  const event = rawEvent === 'palavra_chave'
    ? 'keyword'
    : rawEvent === 'mensagem_recebida'
      ? 'message_received'
      : rawEvent;
  return (
    <div className="space-y-3">
      <Field label="Integração">
        <Select
          value={integration}
          onChange={(v) => onUpdate(patchConfig(node, {
            integration: v,
            event: v === 'whatsapp' ? 'keyword' : 'purchase',
          }))}
          options={[
            { value: 'whatsapp', label: 'WhatsApp' },
            { value: 'hotmart', label: 'Hotmart' },
            { value: 'kiwify', label: 'Kiwify' },
            { value: 'asaas', label: 'Asaas' },
            { value: 'stripe', label: 'Stripe' },
          ]}
        />
      </Field>
      <Field label="Evento">
        <Select
          value={event}
          onChange={(v) => onUpdate(patchConfig(node, { event: v }))}
          options={isWhatsApp
            ? [
                { value: 'keyword', label: 'Palavra-chave' },
                { value: 'message_received', label: 'Mensagem recebida' },
                { value: 'inicio_conversa', label: 'Início de conversa' },
              ]
            : [
                { value: 'purchase', label: 'Compra aprovada' },
                { value: 'abandon', label: 'Carrinho abandonado' },
              ]}
        />
      </Field>
      {isWhatsApp && event === 'keyword' && (
        <Field label="Palavra-chave" hint="ativa o gatilho ao receber">
          <TextInput
            value={readStr(cfg, 'keyword')}
            onChange={(v) => onUpdate(patchConfig(node, { keyword: v }))}
            placeholder='Ex.: "QUERO_PROPOSTA" ou "COMPRAR"'
          />
        </Field>
      )}
    </div>
  );
}

export function ConteudoInspector({ node, onUpdate }: InspectorProps) {
  const cards = readCards(node.data.config);
  return (
    <div className="space-y-3">
      <CardList
        cards={cards}
        onChange={(next) => onUpdate(patchConfig(node, { contents: next }))}
      />
    </div>
  );
}

function readCards(cfg: Record<string, unknown>): Card[] {
  const raw = cfg.contents;
  if (!Array.isArray(raw)) {
    // Compat: campos antigos do inspector simplificado da Fase 3 viram um TextCard.
    const legacyText = readStr(cfg, 'text') || readStr(cfg, 'body') || readStr(cfg, 'message');
    return legacyText ? [{ _id: cardId(), type: 'text', value: legacyText }] : [];
  }
  // Ensure every card has a stable _id for React keys
  return raw.filter(isCard).map((c) => (c._id ? c : { ...c, _id: cardId() }));
}

function isCard(x: unknown): x is Card {
  if (!x || typeof x !== 'object') return false;
  const t = (x as { type?: unknown }).type;
  return (
    t === 'text' || t === 'delay' || t === 'image' || t === 'audio' || t === 'video' || t === 'document'
  );
}

function numberOrDefault(value: number | '', fallback: number): number {
  return typeof value === 'number' ? value : fallback;
}

export function DelayInspector({ node, onUpdate }: InspectorProps) {
  const cfg = node.data.config;
  const mode = readStr(cfg, 'mode') || 'fixo';
  const val = numberOrDefault(readNum(cfg, 'seconds'), 6);
  const maxInt = numberOrDefault(readNum(cfg, 'seconds_max'), 15);

  const ToggleSwitch = ({ checked, onChange, label }: any) => (
    <div className="flex flex-col gap-1 py-1">
      <span className="text-[12px] font-medium text-slate-700">{label}</span>
      <button
        type="button"
        onClick={() => onChange(!checked)}
        className={`relative inline-flex h-[22px] w-10 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none ${checked ? 'bg-[#9333ea]' : 'bg-slate-200'}`}
      >
        <span className={`pointer-events-none inline-block h-[18px] w-[18px] transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out ${checked ? 'translate-x-5' : 'translate-x-0'}`} />
      </button>
    </div>
  );

  return (
    <div className="space-y-5">
      <p className="text-[10px] text-slate-500 leading-relaxed">
        O bloco de delay irá fazer com que o fluxo fique em espera pela quantidade de segundos definido acima antes de continuar para o próximo bloco.
      </p>

      <div className="flex items-center gap-3">
        <div className="h-px flex-1 bg-slate-200" />
        <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">Configurar</span>
        <div className="h-px flex-1 bg-slate-200" />
      </div>

      <div className="flex justify-center">
        <div className="flex bg-slate-100 rounded-full p-1 border border-slate-200 shadow-inner">
          <button
            onClick={() => onUpdate(patchConfig(node, { mode: 'fixo' }))}
            className={`px-4 py-1 text-[11px] font-bold rounded-full transition-all ${mode === 'fixo' ? 'bg-[#06b6d4] text-white shadow-sm' : 'text-slate-500 hover:text-slate-700'}`}
          >
            Fixo
          </button>
          <button
            onClick={() => onUpdate(patchConfig(node, { mode: 'inteligente' }))}
            className={`px-4 py-1 text-[11px] font-bold rounded-full transition-all ${mode === 'inteligente' ? 'bg-[#06b6d4] text-white shadow-sm' : 'text-slate-500 hover:text-slate-700'}`}
          >
            Inteligente
          </button>
        </div>
      </div>

      <div className="flex flex-col gap-1.5">
        <label className="text-[12px] font-semibold text-slate-800">
          {mode === 'fixo' ? `Delay de ${val} Segundos` : `Delay entre ${val} a ${maxInt} Segundos`}
        </label>
        <span className="text-[10px] text-slate-400">Limite operacional: 120 segundos por bloco.</span>
        
        {mode === 'fixo' ? (
          <div className="flex items-center gap-2">
            <div className="flex rounded border border-slate-200 bg-white shadow-sm overflow-hidden flex-1">
              <input
                type="number"
                min="1"
                max="120"
                value={val}
                onChange={(e) => onUpdate(patchConfig(node, { seconds: Math.min(120, parseInt(e.target.value) || 1) }))}
                className="w-full px-3 py-2 text-[13px] outline-none text-slate-700"
              />
              <div className="flex flex-col border-l border-slate-200">
                <button 
                  onClick={() => onUpdate(patchConfig(node, { seconds: Math.min(120, val + 1) }))}
                  className="bg-[#a855f7] hover:bg-[#9333ea] text-white flex-1 px-3 flex items-center justify-center text-[12px] font-bold transition-colors"
                >
                  +
                </button>
                <button 
                  onClick={() => onUpdate(patchConfig(node, { seconds: Math.max(1, val - 1) }))}
                  className="bg-[#a855f7] hover:bg-[#9333ea] text-white flex-1 px-3 flex items-center justify-center text-[12px] font-bold transition-colors border-t border-white/20"
                >
                  -
                </button>
              </div>
            </div>
            <span className="rounded border border-slate-200 bg-slate-50 px-3 py-2 text-[13px] text-slate-600">Seg.</span>
          </div>
        ) : (
          <div className="flex items-center gap-2">
            <input
              type="number"
              min="1"
              max="120"
              value={val}
              onChange={(e) => onUpdate(patchConfig(node, { seconds: Math.min(120, parseInt(e.target.value) || 1) }))}
              className="w-full rounded border border-slate-200 px-3 py-2 text-[13px] outline-none text-slate-700 flex-1"
              placeholder="Mínimo"
            />
            <span className="text-slate-400 font-bold">a</span>
            <input
              type="number"
              min="1"
              max="120"
              value={maxInt}
              onChange={(e) => onUpdate(patchConfig(node, { seconds_max: Math.min(120, parseInt(e.target.value) || 1) }))}
              className="w-full rounded border border-slate-200 px-3 py-2 text-[13px] outline-none text-slate-700 flex-1"
              placeholder="Máximo"
            />
            <span className="rounded border border-slate-200 bg-slate-50 px-2 py-2 text-[13px] text-slate-600">Seg.</span>
          </div>
        )}
      </div>

      <div className="space-y-3 pt-2">
        <ToggleSwitch 
          label="Envia status (Digitando...)" 
          checked={(readStr(cfg, 'status_typing') || 'false') === 'true'} 
          onChange={(v: boolean) => onUpdate(patchConfig(node, { status_typing: v ? 'true' : 'false' }))} 
        />
        <ToggleSwitch 
          label="Envia status (Gravando...)" 
          checked={(readStr(cfg, 'status_recording') || 'false') === 'true'} 
          onChange={(v: boolean) => onUpdate(patchConfig(node, { status_recording: v ? 'true' : 'false' }))} 
        />
      </div>

    </div>
  );
}

export function VoiceStudioInspector({ node, onUpdate }: InspectorProps) {
  const cfg = node.data.config;
  const [showVars, setShowVars] = useState(false);
  const textAreaRef = useRef<HTMLTextAreaElement>(null);

  const customVars = ['{{nome-completo}}', '{{primeiro-nome}}', '{{sobrenome}}', '{{telefone}}', '{{email}}'];
  const flowVars = [
    '{{saudacao}}', '{{duvida}}', 
    '{{Resposta_GPT}}', '{{lead_potes}}', 
    '{{GPT_potes}}', '{{confirmacaopote}}', 
    '{{GPT_POTE_Confir}}', '{{texto_com_nome}}', 
    '{{GPT_NomeLead}}', '{{PesoAltura_Lead}}', 
    '{{pausa_fluxo}}', '{{GPT_IMC}}', 
    '{{Assistiu_video}}', '{{GPT_AssistiuVide}}', 
    '{{explicar_plano}}', '{{pausa_um}}', 
    '{{GPT_IMC_Dado}}', '{{Nomelead}}', 
    '{{nome}}'
  ];

  const handleInsertVar = (v: string) => {
    const current = readStr(cfg, 'script') || '';
    if (textAreaRef.current) {
      const start = textAreaRef.current.selectionStart;
      const end = textAreaRef.current.selectionEnd;
      const next = current.substring(0, start) + v + current.substring(end);
      onUpdate(patchConfig(node, { script: next }));
      setTimeout(() => {
        if (textAreaRef.current) {
          textAreaRef.current.focus();
          textAreaRef.current.setSelectionRange(start + v.length, start + v.length);
        }
      }, 0);
    } else {
      onUpdate(patchConfig(node, { script: current + v }));
    }
  };

  const SliderInput = ({ value, onChange, min, max, step, label, unit = '' }: any) => (
    <div className="flex items-center gap-3">
      <div className="text-[12px] font-medium text-slate-700 w-24 shrink-0">{label}</div>
      <input 
        type="range" 
        min={min} max={max} step={step} 
        value={value} 
        onChange={(e) => onChange(parseFloat(e.target.value))} 
        className="flex-1 accent-[#9333ea] h-1.5 bg-slate-200 rounded-lg appearance-none cursor-pointer"
      />
      <div className="w-10 text-right">
        <span className="text-[10px] font-semibold text-blue-500 bg-blue-50 px-1.5 py-0.5 rounded border border-blue-100">
          {value}{unit}
        </span>
      </div>
    </div>
  );

  const ToggleSwitch = ({ checked, onChange, label }: any) => (
    <div className="flex items-center justify-between py-1">
      <span className="text-[12px] font-medium text-slate-700">{label}</span>
      <button
        type="button"
        onClick={() => onChange(!checked)}
        className={`relative inline-flex h-[22px] w-10 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none ${checked ? 'bg-[#9333ea]' : 'bg-slate-200'}`}
      >
        <span className={`pointer-events-none inline-block h-[18px] w-[18px] transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out ${checked ? 'translate-x-5' : 'translate-x-0'}`} />
      </button>
    </div>
  );

  const VOICES = [
    { id: 'Leda', label: 'Leda', desc: 'Gemini TTS' },
    { id: 'Kore', label: 'Kore', desc: 'Gemini TTS' },
    { id: 'Aoede', label: 'Aoede', desc: 'Gemini TTS' },
  ];

  const configuredVoice = readStr(cfg, 'voice_id');
  const currentVoice = VOICES.some((voice) => voice.id === configuredVoice) ? configuredVoice : 'Leda';

  return (
    <div className="space-y-5">
      <div className="flex flex-col gap-1.5">
        <div className="flex justify-between items-center">
          <label className="text-[13px] font-semibold text-slate-800">Texto</label>
          <button 
            onClick={() => setShowVars(!showVars)}
            className="text-[11px] font-bold text-blue-500 flex items-center gap-1.5 hover:text-blue-600 transition-colors"
          >
            <Eye className="w-3.5 h-3.5" /> Campos Personalizados
          </button>
        </div>
        <textarea
          ref={textAreaRef}
          value={readStr(cfg, 'script') || ''}
          onChange={(e) => onUpdate(patchConfig(node, { script: e.target.value }))}
          placeholder="Digite aqui o texto desejado para virar um áudio."
          rows={5}
          className="w-full px-3 py-2 border border-slate-200 rounded-md text-[13px] text-slate-700 focus:outline-none focus:border-[#9333ea] shadow-sm resize-none"
        />
      </div>

      <div className="border border-slate-200 rounded-lg p-3 bg-slate-50 flex flex-col gap-3 relative">
        <div className="absolute -top-2.5 left-1/2 -translate-x-1/2 bg-slate-50 px-2 text-[10px] text-slate-400 font-semibold uppercase tracking-wider">
          Configurações de voz
        </div>
        <div className="absolute -top-2.5 right-2 text-blue-500 cursor-pointer">
           <Info className="w-4 h-4 bg-white rounded-full" />
        </div>
        
        <div className="flex flex-col gap-3 mt-1">
          <SliderInput 
            label="Expressividade" 
            value={readNum(cfg, 'style') ?? 0.5} 
            onChange={(v: number) => onUpdate(patchConfig(node, { style: v }))} 
            min={0} max={1} step={0.1} 
          />
          <SliderInput 
            label="Velocidade" 
            value={readNum(cfg, 'speed') ?? 1.0} 
            onChange={(v: number) => onUpdate(patchConfig(node, { speed: v }))} 
            min={0.5} max={2.0} step={0.1} unit="x"
          />
        </div>
      </div>

      {showVars && (
        <div className="flex flex-col gap-4 animate-in slide-in-from-top-2 fade-in duration-200 mb-2">
          <div className="relative">
            <div className="absolute inset-0 flex items-center"><div className="w-full border-t border-slate-200"></div></div>
            <div className="relative flex justify-center"><span className="bg-white px-2 text-[10px] text-slate-400 font-semibold uppercase tracking-wider">Campos Personalizados</span></div>
          </div>
          <div className="grid grid-cols-2 gap-2">
            {customVars.map(v => (
              <button 
                key={v} 
                onClick={() => handleInsertVar(v)} 
                className="px-2 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-600 text-[11px] font-mono font-semibold rounded border border-slate-200 transition-colors text-left truncate"
              >
                {v}
              </button>
            ))}
          </div>

          <div className="relative mt-2">
            <div className="absolute inset-0 flex items-center"><div className="w-full border-t border-slate-200"></div></div>
            <div className="relative flex justify-center"><span className="bg-white px-2 text-[10px] text-slate-400 font-semibold uppercase tracking-wider">Campos do fluxo</span></div>
          </div>
          <div className="grid grid-cols-2 gap-2">
            {flowVars.map(v => (
              <button 
                key={v} 
                onClick={() => handleInsertVar(v)} 
                className="px-2 py-1.5 bg-[#16a34a] hover:bg-[#15803d] text-white text-[11px] font-mono font-bold rounded shadow-sm text-left truncate transition-colors"
              >
                {v}
              </button>
            ))}
          </div>
        </div>
      )}

      <div className="flex flex-col pt-1">
        <ToggleSwitch 
          label="Enviar como áudio gravado?" 
          checked={(readStr(cfg, 'send_as_voice') || 'true') === 'true'} 
          onChange={(v: boolean) => onUpdate(patchConfig(node, { send_as_voice: v ? 'true' : 'false' }))} 
        />
      </div>

      <div className="relative border-t border-slate-200 pt-4 mt-2">
         <div className="absolute -top-2.5 left-1/2 -translate-x-1/2 bg-white px-2 text-[10px] text-slate-400 font-semibold uppercase tracking-wider">
           Modelo de áudio
         </div>
         <div className="grid grid-cols-2 gap-2">
           {VOICES.map((v) => {
             const isSel = currentVoice === v.id;
             return (
               <div 
                 key={v.id} 
                 onClick={() => onUpdate(patchConfig(node, { voice_id: v.id }))}
                 className={`flex items-center justify-between p-2 rounded-lg cursor-pointer border transition-all ${isSel ? 'border-[#9333ea] bg-purple-50 ring-1 ring-[#9333ea]/30' : 'border-slate-200 hover:border-slate-300 bg-white'}`}
               >
                 <div className="flex flex-col">
                   <span className="text-[11px] font-bold text-slate-800">{v.label}</span>
                   <span className="text-[9px] font-medium text-slate-400">{v.desc}</span>
                 </div>
                 <button 
                   className="w-6 h-6 rounded-full border-2 border-slate-300 flex items-center justify-center text-slate-500 hover:bg-slate-100 hover:text-slate-700 hover:border-slate-400"
                   onClick={(e) => { e.stopPropagation(); /* simulate play demo */ }}
                 >
                   <svg width="10" height="10" viewBox="0 0 24 24" fill="currentColor"><path d="M5 3v18l15-9L5 3z"/></svg>
                 </button>
               </div>
             );
           })}
         </div>
      </div>
    </div>
  );
}

export function AgenteIaInspector({ node, onUpdate }: InspectorProps) {
  const cfg = node.data.config;
  return (
    <div className="space-y-3">
      <p className="text-[12px] text-slate-500 mb-2">
        Este nó passa o controle para o Agente IA (Studio Persona). O bot responderá usando as diretrizes definidas no Studio.
      </p>
      <Field label="Instrução adicional (Opcional)">
        <TextArea
          value={readStr(cfg, 'context_prompt')}
          onChange={(v) => onUpdate(patchConfig(node, { context_prompt: v }))}
          placeholder="Ex: Foque apenas em vender o produto X nesta etapa."
          rows={4}
        />
      </Field>
      <Field label="Tempo de Controle">
        <Select
          value={readStr(cfg, 'control_mode') || 'until_converted'}
          onChange={(v) => onUpdate(patchConfig(node, { control_mode: v }))}
          options={[
            { value: 'single_response', label: 'Responder apenas uma vez' },
            { value: 'until_converted', label: 'Assumir controle até conversão' },
          ]}
        />
      </Field>
    </div>
  );
}

export function CondicaoInspector({ node, onUpdate }: InspectorProps) {
  const cfg = node.data.config;
  const rules = readRules(cfg);
  const logic = readLogic(cfg);

  return (
    <div className="space-y-3">
      <RuleBuilder
        rules={rules}
        logic={logic}
        onRulesChange={(next) => onUpdate(patchConfig(node, { rules: next }))}
        onLogicChange={(next) => onUpdate(patchConfig(node, { logic: next }))}
      />
    </div>
  );
}

function readRules(cfg: Record<string, unknown>): Rule[] {
  const raw = cfg.rules;
  if (Array.isArray(raw)) return raw.filter(isRule);
  // Compat: regra única da Fase 3 vira um item no array.
  const v = readStr(cfg, 'variable');
  if (v) {
    return [
      {
        var: v,
        op: readStr(cfg, 'operator') || 'equals',
        value: readStr(cfg, 'value'),
      },
    ];
  }
  return [];
}

function isRule(x: unknown): x is Rule {
  return !!x && typeof x === 'object' && 'var' in x && 'op' in x;
}

function readLogic(cfg: Record<string, unknown>): Logic {
  return String(cfg.logic ?? 'AND').toUpperCase() === 'OR' ? 'OR' : 'AND';
}

export function MenuInspector({ node, onUpdate }: InspectorProps) {
  const cfg = node.data.config;
  const options = Array.isArray(cfg.options) ? cfg.options as string[] : [];
  
  return (
    <div className="space-y-4">
      <p className="text-[10px] text-slate-500 leading-relaxed">
        É possível criar um menu de opções para que o cliente escolha o que deseja fazer. Isso pode ser usado para criar um menu de atendimento, onde o cliente escolhe o que deseja fazer.
      </p>

      <div className="flex items-center gap-3">
        <div className="h-px flex-1 bg-slate-200" />
        <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">Configurar Título</span>
        <div className="h-px flex-1 bg-slate-200" />
      </div>

      <div className="flex flex-col gap-1.5">
        <label className="text-[12px] font-semibold text-slate-800">Mensagem de texto</label>
        <input 
          type="text" 
          value={readStr(cfg, 'message') || 'Selecione uma das opções:'}
          onChange={(e) => onUpdate(patchConfig(node, { message: e.target.value }))}
          className="w-full px-3 py-2 text-[12px] border border-slate-200 rounded-md focus:outline-none focus:ring-1 focus:ring-blue-500 text-slate-700 shadow-sm" 
        />
      </div>

      <div className="flex flex-col gap-1.5">
        <label className="text-[12px] font-semibold text-slate-800">Salvar escolha no campo</label>
        <input
          type="text"
          value={readStr(cfg, 'save_to_flow_field')}
          onChange={(e) => onUpdate(patchConfig(node, { save_to_flow_field: e.target.value }))}
          placeholder="Ex.: setor_escolhido"
          className="w-full px-3 py-2 text-[12px] border border-slate-200 rounded-md focus:outline-none focus:ring-1 focus:ring-blue-500 text-slate-700 shadow-sm"
        />
      </div>

      <div className="flex justify-center pt-1">
        <button 
           onClick={() => onUpdate(patchConfig(node, { options: [...options, 'Nova opção'] }))}
           className="border border-slate-200 rounded-full px-4 py-1.5 text-[11px] font-semibold text-slate-600 hover:bg-slate-50 flex items-center gap-1.5 shadow-sm transition-colors"
        >
          <span className="text-slate-400 font-light">+</span> Adicionar Opção
        </button>
      </div>

      {options.length > 0 && (
        <div className="flex flex-col gap-3 p-3 border border-slate-200 rounded-lg shadow-sm bg-white">
           {options.map((opt, i) => (
             <div key={i} className="flex flex-col gap-2">
               <input
                 value={opt}
                 onChange={(e) => {
                   const newOps = [...options];
                   newOps[i] = e.target.value;
                   onUpdate(patchConfig(node, { options: newOps }));
                 }}
                 className="w-full px-3 py-2 text-[12px] border border-slate-200 rounded-md focus:outline-none focus:ring-1 focus:ring-blue-500 text-slate-700"
               />
               <div className="text-[11px] font-medium text-blue-500 pl-1">
                 Opção {i + 1}
               </div>
               {i < options.length - 1 && <div className="h-px bg-slate-100 mt-1" />}
             </div>
           ))}
        </div>
      )}
    </div>
  );
}

export function GptInspector({ node, onUpdate }: InspectorProps) {
  const cfg = node.data.config;

  const SliderInput = ({ value, onChange, min, max, step, label }: any) => (
    <div className="flex flex-col gap-2">
      <div className="text-[12px] font-medium text-slate-700">{label} ({value})</div>
      <input 
        type="range" 
        min={min} max={max} step={step} 
        value={value} 
        onChange={(e) => onChange(parseFloat(e.target.value))} 
        className="w-full accent-[#7c3aed] h-1.5 bg-slate-200 rounded-lg appearance-none cursor-pointer"
      />
    </div>
  );

  const ToggleSwitch = ({ checked, onChange, label }: any) => (
    <div className="flex items-center justify-between py-2 border-b border-slate-100 last:border-0">
      <span className="text-[12px] font-medium text-slate-700">{label}</span>
      <button
        type="button"
        onClick={() => onChange(!checked)}
        className={`relative inline-flex h-[22px] w-10 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none ${checked ? 'bg-[#9333ea]' : 'bg-slate-200'}`}
      >
        <span className={`pointer-events-none inline-block h-[18px] w-[18px] transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out ${checked ? 'translate-x-5' : 'translate-x-0'}`} />
      </button>
    </div>
  );

  return (
    <div className="space-y-4">
      <div className="flex flex-col gap-1.5">
        <label className="text-[13px] font-semibold text-slate-800">Prompt de comando</label>
        <TextArea
          value={readStr(cfg, 'prompt') || readStr(cfg, 'system_prompt')}
          onChange={(v) => onUpdate(patchConfig(node, { prompt: v }))}
          rows={5}
          placeholder="Analise a conversa..."
        />
      </div>

      <Field label="Modelo de IA">
        <Select
          value={readStr(cfg, 'model').startsWith('gemini-') ? readStr(cfg, 'model') : 'gemini-2.5-flash'}
          onChange={(v) => onUpdate(patchConfig(node, { model: v }))}
          options={[
            { value: 'gemini-2.5-pro', label: 'Gemini 2.5 Pro' },
            { value: 'gemini-2.5-flash', label: 'Gemini 2.5 Flash' },
          ]}
        />
      </Field>

      <div className="grid grid-cols-2 gap-4 pb-2 border-b border-slate-100">
        <SliderInput 
          label="Max Tokens" 
          value={readNum(cfg, 'max_tokens') || 256} 
          onChange={(v: number) => onUpdate(patchConfig(node, { max_tokens: v }))} 
          min={10} max={4000} step={10} 
        />
        <SliderInput 
          label="Temperature" 
          value={readNum(cfg, 'temperature') ?? 0.7} 
          onChange={(v: number) => onUpdate(patchConfig(node, { temperature: v }))} 
          min={0} max={2} step={0.1} 
        />
      </div>

      <div className="flex flex-col border-b border-slate-100 pb-2">
        <ToggleSwitch 
          label="Enviar resultado como texto?" 
          checked={(readStr(cfg, 'send_as_text') || 'true') === 'true'} 
          onChange={(v: boolean) => onUpdate(patchConfig(node, { send_as_text: v ? 'true' : 'false' }))} 
        />
      </div>

      <Field label="Deseja salvar o retorno do GPT em um campo de fluxo?">
        <TextInput
          value={readStr(cfg, 'save_as') || readStr(cfg, 'output_var')}
          onChange={(v) => onUpdate(patchConfig(node, { save_as: v, output_var: v }))}
          placeholder="GPT_NomeLead"
        />
      </Field>
    </div>
  );
}

export function ApiInspector({ node, onUpdate }: InspectorProps) {
  const cfg = node.data.config;
  const [modalOpen, setModalOpen] = useState(false);
  const [activeTab, setActiveTab] = useState('headers');
  const [showTooltipCheck, setShowTooltipCheck] = useState(false);
  const [showTooltipTerm, setShowTooltipTerm] = useState(false);
  const [showTestError, setShowTestError] = useState(false);
  const [showCurlView, setShowCurlView] = useState(false);
  const [curlImportStr, setCurlImportStr] = useState('');

  // Modal states
  const [method, setMethod] = useState(readStr(cfg, 'method') || 'GET');
  const [url, setUrl] = useState(readStr(cfg, 'url') || '');
  const [headers, setHeaders] = useState<{key: string, value: string}[]>(() => {
    try {
      const h = JSON.parse(readStr(cfg, 'headers') || '{}');
      return Object.entries(h).map(([k, v]) => ({ key: k, value: String(v) }));
    } catch {
      return [];
    }
  });
  const [bodyStr, setBodyStr] = useState(readStr(cfg, 'body') || '');

  const handleSaveModal = () => {
    const headersObj = headers.reduce((acc, h) => {
      if (h.key.trim()) acc[h.key] = h.value;
      return acc;
    }, {} as Record<string, string>);
    
    onUpdate(patchConfig(node, { 
      method, 
      url, 
      headers: JSON.stringify(headersObj, null, 2),
      body: bodyStr
    }));
    setModalOpen(false);
  };

  const addHeader = () => setHeaders([...headers, { key: '', value: '' }]);
  const updateHeader = (i: number, field: 'key'|'value', val: string) => {
    const n = [...headers];
    n[i][field] = val;
    setHeaders(n);
  };
  const removeHeader = (i: number) => {
    setHeaders(headers.filter((_, idx) => idx !== i));
  };

  const generateCurl = () => {
    let curl = `curl -X ${method} '${url || 'https://...'}'`;
    headers.forEach(h => {
      if (h.key.trim() && h.value.trim()) {
        curl += ` \\\n  -H '${h.key}: ${h.value}'`;
      }
    });
    if (bodyStr.trim() && method !== 'GET') {
      curl += ` \\\n  -d '${bodyStr.replace(/'/g, "'\\''")}'`;
    }
    return curl;
  };

  const handleApplyCurl = () => {
    if (!curlImportStr) return;
    let m = 'GET';
    let u = '';
    let hs: {key: string, value: string}[] = [];
    let b = '';

    const methodMatch = curlImportStr.match(/-X\s+([A-Z]+)/);
    if (methodMatch) m = methodMatch[1];
    else if (curlImportStr.includes('-d') || curlImportStr.includes('--data')) m = 'POST';

    const urlMatch = curlImportStr.match(/curl\s+(?:-X\s+[A-Z]+\s+)?['"]?([^'"\s\\]+)['"]?/);
    if (urlMatch && !urlMatch[1].startsWith('-')) u = urlMatch[1];
    else {
      // fallback matching URL
      const fallbackUrlMatch = curlImportStr.match(/['"](https?:\/\/[^'"]+)['"]/);
      if (fallbackUrlMatch) u = fallbackUrlMatch[1];
    }

    const headerRegex = /-H\s+['"]([^:]+):\s*(.*?)['"]/g;
    let hMatch;
    while ((hMatch = headerRegex.exec(curlImportStr)) !== null) {
      hs.push({ key: hMatch[1], value: hMatch[2] });
    }

    const dataMatch = curlImportStr.match(/--data-raw\s+['"](.*?)['"]/s) || curlImportStr.match(/-d\s+['"](.*?)['"]/s);
    if (dataMatch) b = dataMatch[1];

    setMethod(m);
    setUrl(u);
    if (hs.length > 0) setHeaders(hs);
    if (b) setBodyStr(b);
    
    setCurlImportStr('');
    setShowCurlView(false);
  };

  return (
    <div className="space-y-4">
      <p className="text-[11px] text-slate-500 leading-relaxed text-justify">
        O bloco API Request permite integrar a Laila a sistemas e ferramentas externas por meio de requisições via API
      </p>

      <div className="flex items-center gap-3 mt-4">
        <div className="h-px flex-1 bg-slate-200" />
        <span className="text-[10px] font-semibold text-slate-400">Requisição configurada</span>
        <div className="h-px flex-1 bg-slate-200" />
      </div>

      <button
        onClick={() => setModalOpen(true)}
        className="flex items-center justify-center gap-3 w-full p-3 border border-[#9333ea] rounded-lg bg-white hover:bg-purple-50 transition-colors shadow-sm"
      >
        <div className="text-[#9333ea]">
          <Send className="w-4 h-4 -rotate-45 -mt-1" />
        </div>
        <span className="text-[12px] font-bold text-[#9333ea]">Adicionar uma nova requisição</span>
      </button>

      <div className="p-3 bg-orange-50 rounded-lg flex items-start gap-2">
        <div className="mt-0.5 text-orange-500 shrink-0">
          <Info className="w-4 h-4" />
        </div>
        <p className="text-[11px] text-orange-600 font-medium leading-relaxed">
          Em caso de falha na API de destino, o fluxo seguirá pela saída de erro sem enviar detalhes técnicos ao contato.
        </p>
      </div>

      <Field label="Salvar resposta em" hint="campo de fluxo">
        <TextInput
          value={readStr(cfg, 'save_as') || readStr(cfg, 'output_var')}
          onChange={(value) => onUpdate(patchConfig(node, { save_as: value, output_var: value }))}
          placeholder="api_resultado"
        />
      </Field>

      {modalOpen && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/40 backdrop-blur-sm">
          <div className="bg-white rounded-xl shadow-2xl w-[650px] max-w-[90vw] overflow-hidden flex flex-col relative">
            <div className="flex items-center justify-between px-5 py-3 bg-[#9333ea]">
              <h2 className="text-white font-bold text-[14px]">Configurar Requisição</h2>
              <button onClick={() => setModalOpen(false)} className="w-6 h-6 flex items-center justify-center bg-white rounded-full text-[#9333ea] hover:bg-slate-100 transition-colors">
                <X className="w-4 h-4" />
              </button>
            </div>
            
            <div className="p-5 flex flex-col gap-6">
              <div className="flex items-end gap-3">
                <div className="flex flex-col gap-1.5 w-[140px]">
                  <label className="text-[11px] font-bold text-slate-700">Tipo de Requisição</label>
                  <div className="relative">
                    <select
                      value={method}
                      onChange={(e) => setMethod(e.target.value)}
                      className="w-full appearance-none px-3 py-2 border border-slate-200 rounded-md text-[13px] text-slate-700 focus:outline-none focus:border-[#9333ea] shadow-sm bg-white"
                    >
                      <option value="GET">GET</option>
                      <option value="POST">POST</option>
                      <option value="PUT">PUT</option>
                      <option value="PATCH">PATCH</option>
                      <option value="DELETE">DELETE</option>
                    </select>
                    <ChevronDown className="absolute right-2 top-2.5 w-4 h-4 text-slate-400 pointer-events-none" />
                  </div>
                </div>

                <div className="flex flex-col gap-1.5 flex-1 relative">
                  <label className="text-[11px] font-bold text-slate-700">URL da Requisição (Somente links https)</label>
                  <div className="flex items-center gap-2">
                    <input
                      type="text"
                      value={url}
                      onChange={(e) => setUrl(e.target.value)}
                      placeholder="Url da requisição"
                      className="flex-1 px-3 py-2 border border-slate-200 rounded-md text-[13px] text-slate-700 focus:outline-none focus:border-[#9333ea] shadow-sm"
                    />
                    <div className="relative" onMouseEnter={() => setShowTooltipCheck(true)} onMouseLeave={() => setShowTooltipCheck(false)}>
                      <button 
                        onClick={() => setShowTestError(true)}
                        className="w-9 h-9 flex items-center justify-center rounded-md border border-slate-200 bg-slate-50 text-slate-400 hover:bg-slate-100 transition-colors shrink-0"
                      >
                        <Check className="w-4 h-4" />
                      </button>
                      {showTooltipCheck && (
                        <div className="absolute bottom-[110%] left-1/2 -translate-x-1/2 px-2 py-1 bg-slate-800 text-white text-[11px] rounded whitespace-nowrap z-10 shadow-lg">
                          Testar Requisição
                          <div className="absolute left-1/2 bottom-[-4px] -translate-x-1/2 w-2 h-2 bg-slate-800 rotate-45" />
                        </div>
                      )}
                    </div>
                    <div className="relative" onMouseEnter={() => setShowTooltipTerm(true)} onMouseLeave={() => setShowTooltipTerm(false)}>
                      <button 
                        onClick={() => setShowCurlView(!showCurlView)}
                        className={`w-9 h-9 flex items-center justify-center rounded-md border transition-colors shrink-0 ${showCurlView ? 'border-[#9333ea] text-[#9333ea] bg-purple-50' : 'border-slate-200 bg-white text-slate-500 hover:bg-slate-50'}`}
                      >
                        <Terminal className="w-4 h-4" />
                      </button>
                      {showTooltipTerm && !showCurlView && (
                        <div className="absolute bottom-[110%] right-0 px-3 py-1.5 bg-slate-800 text-white text-[11px] rounded whitespace-nowrap z-10 shadow-lg leading-tight">
                          cURL e payload<br/>(exportar / importar)
                          <div className="absolute right-3 bottom-[-4px] w-2 h-2 bg-slate-800 rotate-45" />
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              </div>

              {!showCurlView ? (
                <>
                  <div className="flex items-center gap-4 border-b border-transparent">
                    {[
                      { id: 'headers', label: 'Headers' },
                      { id: 'body', label: 'Parâmetros(Body)' },
                      { id: 'response', label: 'Resposta' },
                      { id: 'mapping', label: 'Mapeamento da resposta' }
                    ].map((t) => (
                      <button
                        key={t.id}
                        onClick={() => setActiveTab(t.id)}
                        className={`px-4 py-1.5 rounded-full text-[11px] font-bold transition-all ${activeTab === t.id ? 'text-[#9333ea] bg-white shadow-sm ring-1 ring-slate-100' : 'text-slate-400 hover:text-slate-600'}`}
                      >
                        {t.label}
                      </button>
                    ))}
                  </div>

                  <div className="min-h-[150px] max-h-[300px] overflow-y-auto">
                    {activeTab === 'headers' && (
                      <div className="flex flex-col gap-3">
                        <button onClick={addHeader} className="text-blue-500 text-[12px] font-bold self-start hover:text-blue-600">
                          Adicionar Header
                        </button>
                        <div className="grid grid-cols-[1fr,1fr,auto] gap-2 mb-1">
                          <span className="text-[10px] font-bold text-slate-800 uppercase">Chave</span>
                          <span className="text-[10px] font-bold text-slate-800 uppercase">Valor</span>
                          <span className="w-8"></span>
                        </div>
                        {headers.map((h, i) => (
                          <div key={i} className="grid grid-cols-[1fr,1fr,auto] gap-2 items-center">
                            <input
                              value={h.key}
                              onChange={(e) => updateHeader(i, 'key', e.target.value)}
                              placeholder="Content-Type"
                              className="w-full px-3 py-1.5 border border-slate-200 rounded text-[12px] text-slate-700 outline-none focus:border-[#9333ea]"
                            />
                            <input
                              value={h.value}
                              onChange={(e) => updateHeader(i, 'value', e.target.value)}
                              placeholder="application/json"
                              className="w-full px-3 py-1.5 border border-slate-200 rounded text-[12px] text-slate-700 outline-none focus:border-[#9333ea]"
                            />
                            <button onClick={() => removeHeader(i)} className="w-8 h-8 flex items-center justify-center text-slate-400 hover:text-red-500 hover:bg-red-50 rounded">
                              <Trash2 className="w-4 h-4" />
                            </button>
                          </div>
                        ))}
                        {headers.length === 0 && (
                          <div className="text-[12px] text-slate-400 italic text-center py-4">Nenhum header configurado</div>
                        )}
                      </div>
                    )}
                    {activeTab === 'body' && (
                      <div className="flex flex-col gap-2">
                        <label className="text-[11px] font-bold text-slate-700">Payload JSON</label>
                        <textarea
                          value={bodyStr}
                          onChange={(e) => setBodyStr(e.target.value)}
                          rows={6}
                          className="w-full px-3 py-2 border border-slate-200 rounded-md text-[12px] text-slate-700 font-mono outline-none focus:border-[#9333ea]"
                          placeholder='{\n  "chave": "valor"\n}'
                        />
                      </div>
                    )}
                    {(activeTab === 'response' || activeTab === 'mapping') && (
                      <div className="flex items-center justify-center h-[100px] text-slate-400 text-[12px]">
                        Em desenvolvimento...
                      </div>
                    )}
                  </div>
                </>
              ) : (
                <div className="flex flex-col gap-5 min-h-[150px] max-h-[400px] overflow-y-auto">
                  <div className="flex flex-col gap-2">
                    <div className="flex items-center justify-between">
                      <label className="text-[12px] font-bold text-slate-700">Exportar requisição</label>
                      <button 
                        onClick={() => navigator.clipboard.writeText(generateCurl())}
                        className="flex items-center gap-1.5 px-3 py-1 border border-slate-200 rounded text-[11px] font-bold text-slate-600 hover:bg-slate-50 transition-colors"
                      >
                        <Copy className="w-3.5 h-3.5" /> Copiar cURL
                      </button>
                    </div>
                    <textarea
                      readOnly
                      value={generateCurl()}
                      rows={3}
                      className="w-full px-3 py-2 border border-slate-200 rounded-md text-[11px] text-slate-600 font-mono outline-none bg-slate-50 resize-none"
                    />
                  </div>

                  <div className="flex flex-col gap-2">
                    <div className="flex flex-col">
                      <label className="text-[12px] font-bold text-slate-700">Importar a partir de cURL</label>
                      <span className="text-[11px] text-slate-500">Cole um comando cURL completo para preencher método, URL, headers e corpo. O mapeamento da resposta não é alterado.</span>
                    </div>
                    <textarea
                      value={curlImportStr}
                      onChange={(e) => setCurlImportStr(e.target.value)}
                      placeholder="curl 'https://...' -X POST -H 'Content-Type: application/json' --data-raw '{...}'"
                      rows={4}
                      className="w-full px-3 py-2 border border-slate-200 rounded-md text-[11px] text-slate-700 font-mono outline-none focus:border-[#9333ea] resize-none"
                    />
                    <button 
                      onClick={handleApplyCurl}
                      className="self-end flex items-center gap-1.5 px-4 py-1.5 border border-[#9333ea] bg-purple-50 text-[#9333ea] hover:bg-purple-100 rounded text-[11px] font-bold transition-colors"
                    >
                      <Download className="w-3.5 h-3.5" /> Aplicar cURL ao formulário
                    </button>
                  </div>
                </div>
              )}
            </div>

            <div className="flex justify-center p-4 bg-white border-t border-slate-100">
              <button
                onClick={handleSaveModal}
                className="px-10 py-2.5 bg-[#84cc16] hover:bg-[#65a30d] text-white text-[13px] font-bold rounded-md transition-colors"
              >
                Salvar
              </button>
            </div>

            {/* Error Overlay */}
            {showTestError && (
              <div className="absolute inset-0 z-50 flex items-center justify-center bg-white/80 backdrop-blur-[2px]">
                <div className="bg-white rounded-xl shadow-[0_8px_30px_rgb(0,0,0,0.12)] p-8 w-[320px] flex flex-col items-center justify-center border border-slate-100">
                  <div className="w-16 h-16 rounded-full border-4 border-orange-500 flex items-center justify-center mb-4">
                    <X className="w-8 h-8 text-orange-500" />
                  </div>
                  <h3 className="text-[18px] font-bold text-slate-800 mb-2">Oops...</h3>
                  <p className="text-[13px] text-slate-500 text-center mb-6">
                    A solicitação retornou um JSON inválido.
                  </p>
                  <button 
                    onClick={() => setShowTestError(false)}
                    className="w-full py-2 bg-orange-500 hover:bg-orange-600 text-white font-bold rounded-md transition-colors"
                  >
                    Fechar
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

export function IntegrationInspector({ node, onUpdate }: InspectorProps) {
  const cfg = node.data.config;
  const service = readStr(cfg, 'service') || 'google_sheets';
  
  return (
    <div className="space-y-3">
      <Field label="Integração (App)">
        <Select
          value={service}
          onChange={(v) => onUpdate(patchConfig(node, { service: v }))}
          options={[
            { value: 'google_sheets', label: 'Google Sheets' },
            { value: 'activecampaign', label: 'ActiveCampaign' },
          ]}
        />
      </Field>

      <Field label="🔒 Cofre de Credencial (ID)" hint="Selecione a credencial segura deste app">
        <TextInput
          value={readStr(cfg, 'credential_id')}
          onChange={(v) => onUpdate(patchConfig(node, { credential_id: v }))}
          placeholder="Ex: 1"
        />
      </Field>

      {service === 'google_sheets' && (
        <>
          <Field label="Ação">
            <Select
              value={readStr(cfg, 'action') || 'append_row'}
              onChange={(v) => onUpdate(patchConfig(node, { action: v }))}
              options={[
                { value: 'append_row', label: 'Adicionar Nova Linha' },
              ]}
            />
          </Field>
          <Field label="ID da Planilha (Spreadsheet ID)" hint="Encontrado na URL da planilha">
            <TextInput
              value={readStr(cfg, 'spreadsheet_id')}
              onChange={(v) => onUpdate(patchConfig(node, { spreadsheet_id: v }))}
              placeholder="1BxiMVs0XRYFgWNalien..."
            />
          </Field>
          <Field label="Nome da Aba" hint="Opcional. Ex: Página1">
            <TextInput
              value={readStr(cfg, 'sheet_name')}
              onChange={(v) => onUpdate(patchConfig(node, { sheet_name: v }))}
              placeholder="Página1"
            />
          </Field>
          <Field label="Dados a inserir (JSON Array ou Object)">
            <TextArea
              value={readStr(cfg, 'payload')}
              onChange={(v) => onUpdate(patchConfig(node, { payload: v }))}
              placeholder='["{{lead.nome}}", "{{lead.telefone}}", "{{lead.score}}"]'
              rows={4}
            />
          </Field>
        </>
      )}

      {service === 'activecampaign' && (
        <>
          <Field label="Ação">
            <Select
              value={readStr(cfg, 'action') || 'create_contact'}
              onChange={(v) => onUpdate(patchConfig(node, { action: v }))}
              options={[
                { value: 'create_contact', label: 'Criar ou Atualizar Contato' },
                { value: 'add_tag', label: 'Adicionar Tag' },
              ]}
            />
          </Field>
          <Field label="Lista (ID)" hint="Opcional">
            <TextInput
              value={readStr(cfg, 'list_id')}
              onChange={(v) => onUpdate(patchConfig(node, { list_id: v }))}
              placeholder="Ex: 1"
            />
          </Field>
          <Field label="Tag (ID)" hint="Caso a ação seja 'Adicionar Tag'">
            <TextInput
              value={readStr(cfg, 'tag_id')}
              onChange={(v) => onUpdate(patchConfig(node, { tag_id: v }))}
              placeholder="Ex: 5"
            />
          </Field>
        </>
      )}

      <Field label="Salvar Resposta Em" hint="Nome da variável">
        <TextInput
          value={readStr(cfg, 'save_as')}
          onChange={(v) => onUpdate(patchConfig(node, { save_as: v }))}
          placeholder="integration_result"
        />
      </Field>
    </div>
  );
}

export function AbSplitInspector({ node, onUpdate }: InspectorProps) {
  const cfg = node.data.config;
  
  // Backwards compatibility with weight_a / weight_b
  let weights: number[] = [];
  if (Array.isArray(cfg.weights)) {
    weights = cfg.weights as number[];
  } else if (cfg.weight_a !== undefined && cfg.weight_b !== undefined) {
    weights = [Number(cfg.weight_a), Number(cfg.weight_b)];
  } else {
    weights = [50, 50];
  }

  const handleAdd = () => {
    const nextCount = weights.length + 1;
    const equalWeight = 100 / nextCount;
    const nextWeights = Array(nextCount).fill(equalWeight);
    onUpdate(patchConfig(node, { weights: nextWeights }));
  };

  const handleRemove = (index: number) => {
    if (weights.length <= 2) return; // Minimum 2 for split
    const nextWeights = weights.filter((_, i) => i !== index);
    const equalWeight = 100 / nextWeights.length;
    onUpdate(patchConfig(node, { weights: nextWeights.map(() => equalWeight) }));
  };

  const handleSliderChange = (index: number, newValue: number) => {
    const nextWeights = [...weights];
    nextWeights[index] = newValue;
    const diff = 100 - newValue;
    const otherCount = weights.length - 1;
    const remainingSum = weights.reduce((acc, w, i) => i !== index ? acc + w : acc, 0);

    for (let i = 0; i < nextWeights.length; i++) {
      if (i !== index) {
        if (remainingSum === 0) {
          nextWeights[i] = diff / otherCount;
        } else {
          nextWeights[i] = (weights[i] / remainingSum) * diff;
        }
      }
    }
    onUpdate(patchConfig(node, { weights: nextWeights }));
  };

  return (
    <div className="space-y-4">
      <p className="text-[11px] text-slate-500 leading-relaxed text-justify">
        É possível segmentar sua audiência para experimentar diversas variações de uma campanha e identificar qual delas apresenta o desempenho mais eficaz.
        Isso envolve apresentar a versão A do conteúdo para uma parcela do seu público e a versão B para outra parcela.
      </p>

      <div className="flex justify-center mt-2">
        <button
          onClick={handleAdd}
          className="flex items-center gap-2 px-4 py-1.5 bg-white border border-slate-200 rounded-full text-[11px] font-semibold text-slate-600 shadow-sm hover:bg-slate-50 transition-colors"
        >
          <span className="text-slate-400">+</span> Adicionar Teste
        </button>
      </div>

      <div className="space-y-3 mt-4">
        {weights.map((w, i) => (
          <div key={i} className="flex flex-col gap-2">
            <div className="flex items-center gap-3">
              <span className="text-[13px] font-bold text-slate-700 w-5">T{i + 1}</span>
              <input
                type="range"
                min="0"
                max="100"
                step="0.01"
                value={w}
                onChange={(e) => handleSliderChange(i, parseFloat(e.target.value))}
                className="flex-1 accent-[#a855f7] h-1.5 bg-slate-200 rounded-lg appearance-none cursor-pointer"
              />
            </div>
            <div className="flex items-center justify-between border border-slate-200 rounded-md bg-white overflow-hidden shadow-sm">
              <div className="px-3 py-2 text-[12px] font-bold text-blue-500 bg-white flex-1">
                {w % 1 === 0 ? w : w.toFixed(2)}% de execução
              </div>
              <button
                onClick={() => handleRemove(i)}
                className={`p-2 transition-colors ${weights.length > 2 ? 'text-red-500 hover:bg-red-50' : 'text-slate-300 cursor-not-allowed'}`}
                disabled={weights.length <= 2}
              >
                <Trash2 className="w-4 h-4" />
              </button>
            </div>
          </div>
        ))}
      </div>

      {/* Validação de soma 100% (Padrão ChatbotX Split Traffic) */}
      {(() => {
        const totalWeight = weights.reduce((acc, curr) => acc + curr, 0);
        const isBalanced = Math.abs(totalWeight - 100) < 0.2;
        return (
          <div className={`flex items-center justify-between p-2.5 rounded-xl border text-xs font-semibold ${
            isBalanced
              ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-600 dark:text-emerald-400'
              : 'bg-amber-500/10 border-amber-500/30 text-amber-600 dark:text-amber-400'
          }`}>
            <span>Total Distribuído:</span>
            <span>
              {totalWeight.toFixed(1)}% {isBalanced ? '✓ 100% Calibrado' : '⚠ Deve somar 100%'}
            </span>
          </div>
        );
      })()}
    </div>
  );
}

export function MotorRefInspector({ node }: InspectorProps) {
  const moduleHint = readStr(node.data.config, 'module_hint');
  return (
    <div className="space-y-3">
      <Field label="Módulo Python" hint="referência (read-only)">
        <div className="rounded border border-sibila-mist bg-sibila-onyx px-2 py-1.5 text-sm text-sibila-fog font-mono">
          {moduleHint || '— sem referência —'}
        </div>
      </Field>
      <p className="text-[11px] text-sibila-smoke leading-relaxed">
        Este bloco delega execução a um módulo Python. Edição do código é fora do
        builder — abra o arquivo no IDE.
      </p>
    </div>
  );
}

export function AnotacaoInspector({ node, onUpdate }: InspectorProps) {
  return (
    <div className="space-y-3">
      <Field label="Anotação" hint="só visível no canvas, não afeta o fluxo">
        <TextArea
          value={readStr(node.data.config, 'note')}
          onChange={(v) => onUpdate(patchConfig(node, { note: v }))}
          rows={6}
          placeholder="Documente decisões, links, contexto…"
        />
      </Field>
    </div>
  );
}




export function AcaoInspector({ node, onUpdate }: InspectorProps) {
  const cfg = node.data.config;
  const legacyAction = cfg.action_kind;
  const actions = Array.isArray(cfg.actions) 
     ? cfg.actions 
     : (legacyAction ? [{ action_kind: legacyAction, payload: cfg.payload }] : []);

  const [menuOpen, setMenuOpen] = useState(false);
  const [newTagModal, setNewTagModal] = useState<{open: boolean, index: number}>({open: false, index: -1});
  const [newTagName, setNewTagName] = useState('');
  const [newTagDesc, setNewTagDesc] = useState('');
  const [newTagBoard, setNewTagBoard] = useState(true);
  const [newTagColor, setNewTagColor] = useState('#22c55e');
  const [availableFlows, setAvailableFlows] = useState<BlueprintSummary[]>([]);

  useEffect(() => {
    let active = true;
    blueprintsApi.list()
      .then((flows) => {
        if (active) setAvailableFlows(flows);
      })
      .catch(() => {
        if (active) setAvailableFlows([]);
      });
    return () => {
      active = false;
    };
  }, []);

  const actionLabels: Record<string, string> = {
    'tag_add': 'Adicionar Etiqueta',
    'tag_remove': 'Remover Etiqueta',
    'assign_user': 'Atribuir Responsável',
    'unassign_user': 'Remover Responsável',
    'start_flow': 'Iniciar Fluxo',
    'end_flow': 'Finalizar Fluxo',
    'close_chat': 'Finalizar Conversa (chat)',
    'open_chat': 'Abrir Conversa (chat)',
    'update_contact': 'Atualizar contato',
  };

  const menuOptions = Object.keys(actionLabels);

  const handleAddAction = (kind: string) => {
    const newActions = [...actions, { action_kind: kind, payload: '' }];
    onUpdate(patchConfig(node, { actions: newActions }));
    setMenuOpen(false);
  };

  const handleUpdateAction = (index: number, payload: string) => {
    const newActions = [...actions];
    newActions[index] = { ...newActions[index], payload };
    onUpdate(patchConfig(node, { actions: newActions }));
  };

  const handleRemoveAction = (index: number) => {
    const newActions = [...actions];
    newActions.splice(index, 1);
    onUpdate(patchConfig(node, { actions: newActions }));
  };

  return (
    <div className="space-y-4">
      {/* Botão Adicionar */}
      <div className="relative">
         <button 
           onClick={() => setMenuOpen(!menuOpen)}
           className="w-full bg-white border border-slate-200 rounded text-[13px] font-bold text-blue-500 py-3 flex items-center justify-center gap-2 hover:bg-slate-50 transition-colors shadow-sm"
         >
           <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect><circle cx="12" cy="12" r="3"></circle></svg>
           Adicionar uma nova ação
         </button>
         
         {menuOpen && (
           <div className="absolute top-full left-0 right-0 mt-2 bg-white border border-slate-200 rounded-lg shadow-xl z-50 py-1 overflow-hidden">
             {menuOptions.map(opt => (
                <button 
                  key={opt}
                  onClick={() => handleAddAction(opt)}
                  className="w-full text-left px-4 py-2.5 text-[12px] font-medium text-slate-700 hover:bg-slate-50 hover:text-blue-600 transition-colors"
                >
                  {actionLabels[opt]}
                </button>
             ))}
           </div>
         )}
      </div>

      <div className="flex items-center gap-3">
        <div className="h-px flex-1 bg-slate-200" />
        <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Ações</span>
        <div className="h-px flex-1 bg-slate-200" />
      </div>

      {actions.length === 0 ? (
         <div className="bg-[#6366f1] text-white text-center py-2.5 text-[11px] font-bold rounded-full shadow-md shadow-indigo-500/20">
           Nenhum conteúdo foi adicionado.
         </div>
      ) : (
         <div className="flex flex-col gap-3">
            {actions.map((act: any, i: number) => (
               <div key={i} className="border border-slate-200 rounded-lg bg-white shadow-sm overflow-hidden flex flex-col">
                  {/* Tipo específico UI */}
                  <div className="p-3 bg-white">
                     {(act.action_kind === 'tag_add' || act.action_kind === 'tag_remove') && (
                       <div className="flex flex-col gap-1.5">
                          <label className="text-[12px] font-bold text-slate-800">Etiqueta</label>
                          <div className="flex items-center gap-2">
                             <select 
                               className="flex-1 px-3 py-2 border border-slate-200 rounded text-[12px] font-medium text-slate-700 outline-none focus:border-blue-500 bg-white"
                               value={act.payload || ''}
                               onChange={(e) => handleUpdateAction(i, e.target.value)}
                             >
                               <option value="">Selecione uma etiqueta</option>
                               <option value="entrou no funil">🟢 entrou no funil</option>
                               <option value="Entrou no funil Cigana Esmeralda">🟢 Entrou no funil Cigana Esmeralda</option>
                               <option value="Compra Aprovada">🟢 Compra Aprovada</option>
                             </select>
                             <button 
                                onClick={() => setNewTagModal({ open: true, index: i })}
                                className="w-9 h-9 flex items-center justify-center border border-slate-200 rounded bg-slate-50 text-slate-500 hover:text-blue-500 hover:bg-blue-50 transition-colors shrink-0"
                             >
                                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><line x1="12" y1="5" x2="12" y2="19"></line><line x1="5" y1="12" x2="19" y2="12"></line></svg>
                             </button>
                          </div>
                       </div>
                     )}

                     {(act.action_kind === 'assign_user' || act.action_kind === 'unassign_user') && (
                       <select 
                         className="w-full px-3 py-2 border border-slate-200 rounded text-[12px] font-medium text-slate-500 outline-none focus:border-blue-500 bg-white"
                         value={act.payload || ''}
                         onChange={(e) => handleUpdateAction(i, e.target.value)}
                       >
                         <option value="">Selecione um responsável</option>
                         <option value="atendente1">Atendente 1</option>
                         <option value="atendente2">Atendente 2</option>
                       </select>
                     )}

                     {act.action_kind === 'start_flow' && (
                       <select 
                         className="w-full px-3 py-2 border border-slate-200 rounded text-[12px] font-medium text-slate-500 outline-none focus:border-blue-500 bg-white"
                         value={act.payload || ''}
                         onChange={(e) => handleUpdateAction(i, e.target.value)}
                       >
                         <option value="">Selecione um fluxo</option>
                         {availableFlows.map((flow) => (
                           <option key={flow.id} value={String(flow.id)}>{flow.title}</option>
                         ))}
                       </select>
                     )}

                     {act.action_kind === 'end_flow' && (
                       <div className="bg-[#ecfdf5] border border-[#d1fae5] rounded-md p-3 flex items-start gap-2.5">
                          <svg className="text-[#059669] mt-0.5 shrink-0" width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-6h2v6zm0-8h-2V7h2v2z"></path></svg>
                          <span className="text-[12px] text-[#059669] font-medium leading-tight">
                             Essa ação irá forçar a finalização do fluxo!
                          </span>
                       </div>
                     )}

                     {act.action_kind === 'open_chat' && (
                       <div className="bg-[#ecfdf5] border border-[#d1fae5] rounded-md p-3 flex items-start gap-2.5">
                          <svg className="text-[#059669] mt-0.5 shrink-0" width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-6h2v6zm0-8h-2V7h2v2z"></path></svg>
                          <span className="text-[12px] text-[#059669] font-medium leading-tight">
                             Essa ação irá marcar a conversa no chat com o contato como aberta!
                          </span>
                       </div>
                     )}

                     {act.action_kind === 'close_chat' && (
                       <div className="bg-[#ecfdf5] border border-[#d1fae5] rounded-md p-3 flex items-start gap-2.5">
                          <svg className="text-[#059669] mt-0.5 shrink-0" width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-6h2v6zm0-8h-2V7h2v2z"></path></svg>
                          <span className="text-[12px] text-[#059669] font-medium leading-tight">
                             Essa ação irá marcar a conversa no chat com o contato como finalizada!
                          </span>
                       </div>
                     )}

                     {act.action_kind === 'update_contact' && (
                       <div className="flex flex-col gap-4">
                          <div className="flex flex-col gap-1.5">
                             <label className="text-[12px] font-bold text-slate-800">Campo a ser atualizado</label>
                             <select 
                               className="w-full px-3 py-2 border border-slate-200 rounded text-[12px] font-medium text-slate-700 outline-none focus:border-blue-500 bg-white"
                               value={act.target_field || ''}
                               onChange={(e) => {
                                 const newActions = [...actions];
                                 newActions[i] = { ...newActions[i], target_field: e.target.value };
                                 onUpdate(patchConfig(node, { actions: newActions }));
                               }}
                             >
                               <option value="">Selecione um campo</option>
                               <option value="name">Nome</option>
                               <option value="email">E-mail</option>
                               <option value="phone">Telefone</option>
                             </select>
                          </div>
                          
                          <div className="flex flex-col items-center gap-3">
                             <span className="text-[12px] font-medium text-slate-700">Atualize o contato utilizando informações salvas em</span>
                             <div className="flex bg-slate-100 rounded-full p-0.5 border border-slate-200 shadow-sm">
                               <button 
                                 onClick={() => {
                                   const newActions = [...actions];
                                   newActions[i] = { ...newActions[i], source_type: 'flow' };
                                   onUpdate(patchConfig(node, { actions: newActions }));
                                 }}
                                 className={`px-4 py-1.5 rounded-full text-[12px] font-medium transition-colors ${act.source_type !== 'webhook' ? 'bg-[#0ea5e9] text-white shadow-sm' : 'text-slate-600 hover:text-slate-800'}`}
                               >
                                 Campo de fluxo
                               </button>
                               <button 
                                 onClick={() => {
                                   const newActions = [...actions];
                                   newActions[i] = { ...newActions[i], source_type: 'webhook' };
                                   onUpdate(patchConfig(node, { actions: newActions }));
                                 }}
                                 className={`px-4 py-1.5 rounded-full text-[12px] font-medium transition-colors ${act.source_type === 'webhook' ? 'bg-[#0ea5e9] text-white shadow-sm' : 'text-slate-600 hover:text-slate-800'}`}
                               >
                                 Caminho de webhook
                               </button>
                             </div>
                          </div>

                          <input 
                            type="text" 
                            className="w-full px-3 py-2.5 border border-slate-200 rounded text-[12px] font-medium text-slate-700 outline-none focus:border-blue-500"
                            value={act.payload || ''}
                            onChange={(e) => handleUpdateAction(i, e.target.value)}
                            placeholder={act.source_type === 'webhook' ? 'Ex: contact.email' : 'Ex: {{resposta_gpt_email}}'}
                          />
                       </div>
                     )}

                     {(!['tag_add', 'tag_remove', 'assign_user', 'unassign_user', 'start_flow', 'end_flow', 'open_chat', 'close_chat', 'update_contact'].includes(act.action_kind)) && (
                       <div className="flex flex-col gap-1.5">
                          <label className="text-[12px] font-bold text-slate-800">Configuração</label>
                          <input 
                            type="text" 
                            className="w-full px-3 py-2 border border-slate-200 rounded text-[12px] font-medium text-slate-700 outline-none focus:border-blue-500"
                            value={act.payload || ''}
                            onChange={(e) => handleUpdateAction(i, e.target.value)}
                            placeholder={`Configuração para ${actionLabels[act.action_kind]}...`}
                          />
                       </div>
                     )}
                  </div>

                  {/* Footer of the action box */}
                  <div className="flex items-center justify-between px-3 py-2 bg-slate-50 border-t border-slate-100">
                     <span className="text-[10px] font-bold text-slate-600">{actionLabels[act.action_kind] || act.action_kind}</span>
                     <div className="flex items-center gap-2">
                        <button className="text-slate-400 hover:text-[#9333ea] cursor-grab transition-colors p-1">
                           <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><circle cx="9" cy="12" r="1.5"></circle><circle cx="9" cy="5" r="1.5"></circle><circle cx="9" cy="19" r="1.5"></circle><circle cx="15" cy="12" r="1.5"></circle><circle cx="15" cy="5" r="1.5"></circle><circle cx="15" cy="19" r="1.5"></circle></svg>
                        </button>
                        <div className="w-px h-4 bg-slate-200 mx-0.5"></div>
                        <button onClick={() => handleRemoveAction(i)} className="text-red-400 hover:text-red-600 hover:bg-red-50 p-1.5 rounded transition-colors">
                           <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path></svg>
                        </button>
                     </div>
                  </div>
               </div>
            ))}
         </div>
      )}

      {/* Modal de Nova Etiqueta */}
      {newTagModal.open && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/40 backdrop-blur-sm p-4">
          <div className="bg-white rounded-lg shadow-2xl w-full max-w-[500px] overflow-hidden flex flex-col">
            <div className="bg-[#a855f7] px-5 py-4 flex items-center justify-between shrink-0">
               <h2 className="text-white font-bold text-[18px]">Adicionar Etiqueta</h2>
               <button onClick={() => setNewTagModal({open: false, index: -1})} className="bg-white text-[#a855f7] hover:bg-slate-100 p-1 rounded-full transition-colors flex items-center justify-center">
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>
               </button>
            </div>
            
            <div className="p-6 flex flex-col gap-5">
               <div className="flex flex-col gap-1.5">
                  <label className="text-[13px] font-bold text-slate-800">Nome da etiqueta</label>
                  <input 
                    type="text" 
                    value={newTagName}
                    onChange={(e) => setNewTagName(e.target.value)}
                    placeholder="Digite um nome"
                    className="w-full px-3 py-2.5 border border-slate-200 rounded-md text-[13px] outline-none focus:border-[#a855f7] text-slate-700"
                  />
               </div>

               <div className="grid grid-cols-2 gap-4">
                  <div className="flex flex-col gap-2">
                     <label className="text-[13px] font-bold text-slate-800">Vira board?</label>
                     <button 
                       onClick={() => setNewTagBoard(!newTagBoard)}
                       className={`w-12 h-6 rounded-full transition-colors relative flex items-center px-1 ${newTagBoard ? 'bg-[#a855f7]' : 'bg-slate-300'}`}
                     >
                       <div className={`w-4 h-4 bg-white rounded-full shadow-sm transition-transform ${newTagBoard ? 'translate-x-6' : 'translate-x-0'}`} />
                     </button>
                  </div>
                  <div className="flex flex-col gap-2">
                     <label className="text-[13px] font-bold text-slate-800">Cor da etiqueta</label>
                     <div className="w-full h-7 rounded-full cursor-pointer border border-black/10 shadow-sm flex items-center justify-center relative overflow-hidden" style={{backgroundColor: newTagColor}}>
                       <input 
                         type="color" 
                         value={newTagColor}
                         onChange={(e) => setNewTagColor(e.target.value)}
                         className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                       />
                     </div>
                  </div>
               </div>

               <div className="flex flex-col gap-1.5">
                  <label className="text-[13px] font-bold text-slate-800">Descrição</label>
                  <textarea 
                    value={newTagDesc}
                    onChange={(e) => setNewTagDesc(e.target.value)}
                    placeholder="Descrição da etiqueta..."
                    rows={4}
                    className="w-full px-3 py-2.5 border border-slate-200 rounded-md text-[13px] outline-none focus:border-[#a855f7] text-slate-700 resize-none"
                  />
               </div>

               <p className="text-[11px] text-slate-400 leading-relaxed -mt-1">
                  O nome e a descrição serão usados para identificar contatos e boards do funil.
               </p>

               <button 
                  disabled={!newTagName.trim()}
                  onClick={() => {
                     if (!newTagName.trim()) return;
                     handleUpdateAction(newTagModal.index, newTagName.trim());
                     setNewTagName('');
                     setNewTagDesc('');
                     setNewTagModal({open: false, index: -1});
                  }}
                  className={`w-full py-3 rounded text-[14px] font-bold transition-colors mt-2 ${newTagName.trim() ? 'bg-[#10b981] hover:bg-[#059669] text-white' : 'bg-slate-300 text-slate-100 cursor-not-allowed'}`}
               >
                  Salvar Etiqueta
               </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export function ExpedienteInspector({ node, onUpdate }: InspectorProps) {
  const cfg = node.data.config || {};
  
  const defaultDays = [
    { name: 'Domingo', active: false, intervals: [{ start: '', end: '' }] },
    { name: 'Segunda-feira', active: false, intervals: [{ start: '', end: '' }] },
    { name: 'Terça-feira', active: false, intervals: [{ start: '', end: '' }] },
    { name: 'Quarta-feira', active: false, intervals: [{ start: '', end: '' }] },
    { name: 'Quinta-feira', active: false, intervals: [{ start: '', end: '' }] },
    { name: 'Sexta-feira', active: false, intervals: [{ start: '', end: '' }] },
    { name: 'Sábado', active: false, intervals: [{ start: '', end: '' }] },
  ];

  const days = Array.isArray(cfg.days) && cfg.days.length === 7 ? cfg.days : defaultDays;
  const scheduleNext = !!cfg.scheduleNext;
  const timezone = typeof cfg.timezone === 'string' ? cfg.timezone : 'America/Sao_Paulo';

  // Força a atualização do config no primeiro carregamento caso esteja vazio,
  // habilitando o botão de Salvar e Fechar no Inspetor.
  useEffect(() => {
    if (Object.keys(cfg).length === 0) {
      onUpdate(patchConfig(node, { days: defaultDays, timezone: 'America/Sao_Paulo' }));
    }
  }, [cfg, node, onUpdate]);

  const handleUpdateDay = (index: number, active: boolean) => {
    const newDays = [...days];
    newDays[index] = { ...newDays[index], active };
    onUpdate(patchConfig(node, { days: newDays }));
  };

  const handleUpdateInterval = (dayIndex: number, intervalIndex: number, field: 'start'|'end', value: string) => {
    const newDays = [...days];
    const newIntervals = [...newDays[dayIndex].intervals];
    newIntervals[intervalIndex] = { ...newIntervals[intervalIndex], [field]: value };
    newDays[dayIndex] = { ...newDays[dayIndex], intervals: newIntervals };
    onUpdate(patchConfig(node, { days: newDays }));
  };

  const handleAddInterval = (dayIndex: number) => {
    const newDays = [...days];
    const newIntervals = [...newDays[dayIndex].intervals, { start: '', end: '' }];
    newDays[dayIndex] = { ...newDays[dayIndex], intervals: newIntervals };
    onUpdate(patchConfig(node, { days: newDays }));
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
         <label className="text-[12px] font-medium text-slate-800">Agendar continuação para o próximo expediente:</label>
         <button 
           onClick={() => onUpdate(patchConfig(node, { scheduleNext: !scheduleNext }))}
           className={`w-10 h-5 rounded-full transition-colors relative flex items-center px-0.5 shrink-0 ${scheduleNext ? 'bg-[#9333ea]' : 'bg-slate-300'}`}
         >
           <div className={`w-4 h-4 bg-white rounded-full shadow-sm transition-transform ${scheduleNext ? 'translate-x-5' : 'translate-x-0'}`} />
         </button>
      </div>

      <div className="flex flex-col gap-1.5 mb-4">
         <label className="text-[12px] font-medium text-slate-800">Fuso Horário</label>
         <select 
           value={timezone}
           onChange={(e) => onUpdate(patchConfig(node, { timezone: e.target.value }))}
           className="w-full px-3 py-2 border border-slate-200 rounded text-[13px] font-medium text-slate-700 outline-none focus:border-[#9333ea]"
         >
           <option value="America/Sao_Paulo">America/Sao_Paulo (Brasília)</option>
           <option value="America/Manaus">America/Manaus</option>
           <option value="America/Belem">America/Belem</option>
           <option value="America/Fortaleza">America/Fortaleza</option>
           <option value="America/Recife">America/Recife</option>
           <option value="America/Rio_Branco">America/Rio_Branco</option>
         </select>
      </div>

      <div className="flex items-center gap-3">
        <div className="h-px flex-1 bg-slate-200" />
        <span className="text-[11px] font-bold text-orange-400 uppercase tracking-widest">Horários de funcionamento</span>
        <div className="h-px flex-1 bg-slate-200" />
      </div>

      <div className="flex flex-col gap-6">
        {days.map((day, i) => (
          <div key={i} className="flex flex-col gap-3">
            <div className="flex items-center justify-between">
              <span className="text-[13px] font-bold text-slate-800">{day.name}</span>
              <div className="flex items-center gap-2">
                <span className="text-[11px] font-medium text-slate-500">Ativo</span>
                <button 
                  onClick={() => handleUpdateDay(i, !day.active)}
                  className={`w-9 h-4 rounded-full transition-colors relative flex items-center px-0.5 ${day.active ? 'bg-[#9333ea]' : 'bg-slate-300'}`}
                >
                  <div className={`w-3 h-3 bg-white rounded-full shadow-sm transition-transform ${day.active ? 'translate-x-5' : 'translate-x-0'}`} />
                </button>
              </div>
            </div>

            <div className="flex flex-col gap-2">
              {day.intervals.map((inv: any, idx: number) => (
                <div key={idx} className="flex items-center gap-3">
                  <div className="flex-1 relative">
                    <input 
                      type="time" 
                      value={inv.start}
                      onChange={(e) => handleUpdateInterval(i, idx, 'start', e.target.value)}
                      className={`w-full px-3 py-2 border rounded text-[13px] outline-none transition-colors ${day.active ? 'border-slate-300 text-slate-700 focus:border-[#9333ea]' : 'border-slate-200 text-slate-400 bg-slate-50'}`}
                      disabled={!day.active}
                    />
                  </div>
                  <div className="flex-1 relative">
                    <input 
                      type="time" 
                      value={inv.end}
                      onChange={(e) => handleUpdateInterval(i, idx, 'end', e.target.value)}
                      className={`w-full px-3 py-2 border rounded text-[13px] outline-none transition-colors ${day.active ? 'border-slate-300 text-slate-700 focus:border-[#9333ea]' : 'border-slate-200 text-slate-400 bg-slate-50'}`}
                      disabled={!day.active}
                    />
                  </div>
                </div>
              ))}
              <button 
                onClick={() => handleAddInterval(i)}
                disabled={!day.active}
                className={`self-start text-[11px] font-medium transition-colors ${day.active ? 'text-blue-500 hover:text-blue-600' : 'text-slate-400 cursor-not-allowed'}`}
              >
                + Adicionar intervalo de tempo
              </button>
            </div>
            
            {i < 6 && <div className="h-px w-full bg-slate-100 mt-2" />}
          </div>
        ))}
      </div>
    </div>
  );
}

export function EndInspector() {
  return (
    <p className="text-[11px] text-sibila-smoke leading-relaxed">
      Bloco terminal. Marca o fim de um caminho do funil.
    </p>
  );
}

export function NotificarAtendenteInspector({ node, onUpdate }: InspectorProps) {
  const cfg = node.data.config;

  const defaultMessage = `_*Enviando dados do contato:*_\n*Nome:* {{primeiro_nome}}\n*Telefone:* {{telefone}}\n*Fluxo:* {{fluxo}}`;

  const message = typeof cfg.message === 'string' ? cfg.message : defaultMessage;

  return (
    <div className="space-y-4">
      <div className="flex flex-col gap-1.5">
        <textarea
          value={message}
          onChange={(e) => onUpdate(patchConfig(node, { message: e.target.value }))}
          rows={5}
          className="w-full px-3 py-2 text-[12px] border border-blue-500 rounded-md focus:outline-none shadow-sm font-mono text-slate-700 resize-none"
        />
      </div>
      <div className="relative mt-2">
        <select
          value={readStr(cfg, 'atendente_id') || ''}
          onChange={(e) => onUpdate(patchConfig(node, { atendente_id: e.target.value }))}
          className="w-full appearance-none rounded border border-slate-200 px-3 py-2 text-[13px] text-slate-500 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 shadow-sm bg-white"
        >
          <option value="" disabled hidden>Selecione um atendente</option>
          <option value="1">Atendente 1</option>
          <option value="2">Atendente 2</option>
        </select>
        <div className="absolute inset-y-0 right-2 flex items-center gap-2 pointer-events-none">
          <ChevronDown className="w-4 h-4 text-slate-400" />
        </div>
      </div>
    </div>
  );
}
