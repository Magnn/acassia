import { Field, NumberInput, Select, TextArea, TextInput } from './fields';
import { patchConfig, readNum, readStr, type InspectorProps } from './helpers';
import CardList from './conteudo/CardList';
import { type Card } from './conteudo/types';
import RuleBuilder, { type Logic, type Rule } from './condicao/RuleBuilder';

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
  return (
    <div className="space-y-3">
      <Field label="Integração">
        <Select
          value={readStr(cfg, 'integration') || 'whatsapp'}
          onChange={(v) => onUpdate(patchConfig(node, { integration: v }))}
          options={[
            { value: 'whatsapp', label: 'WhatsApp' },
            { value: 'instagram', label: 'Instagram' },
            { value: 'webhook', label: 'Webhook genérico' },
          ]}
        />
      </Field>
      <Field label="Evento">
        <Select
          value={readStr(cfg, 'event') || 'palavra_chave'}
          onChange={(v) => onUpdate(patchConfig(node, { event: v }))}
          options={[
            { value: 'palavra_chave', label: 'Palavra-chave' },
            { value: 'mensagem_recebida', label: 'Mensagem recebida' },
            { value: 'inicio_conversa', label: 'Início de conversa' },
            { value: 'webhook', label: 'Webhook' },
          ]}
        />
      </Field>
      <Field label="Palavra-chave" hint="ativa o gatilho ao receber">
        <TextInput
          value={readStr(cfg, 'keyword')}
          onChange={(v) => onUpdate(patchConfig(node, { keyword: v }))}
          placeholder='Ex.: "quero minha consulta"'
        />
      </Field>
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
    return legacyText ? [{ type: 'text', value: legacyText }] : [];
  }
  return raw.filter(isCard);
}

function isCard(x: unknown): x is Card {
  if (!x || typeof x !== 'object') return false;
  const t = (x as { type?: unknown }).type;
  return (
    t === 'text' || t === 'delay' || t === 'image' || t === 'audio' || t === 'video' || t === 'document'
  );
}

export function DelayInspector({ node, onUpdate }: InspectorProps) {
  return (
    <div className="space-y-3">
      <Field label="Segundos">
        <NumberInput
          value={readNum(node.data.config, 'seconds')}
          min={0}
          max={86400}
          onChange={(v) => onUpdate(patchConfig(node, { seconds: v === '' ? 0 : v }))}
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

export function GptInspector({ node, onUpdate }: InspectorProps) {
  const cfg = node.data.config;
  return (
    <div className="space-y-3">
      <Field label="System prompt">
        <TextArea
          value={readStr(cfg, 'system_prompt')}
          onChange={(v) => onUpdate(patchConfig(node, { system_prompt: v }))}
          rows={6}
          placeholder="Você é uma cigana experiente que…"
        />
      </Field>
      <div className="grid grid-cols-2 gap-2">
        <Field label="Modelo">
          <Select
            value={readStr(cfg, 'model') || 'gemini-2.5-flash'}
            onChange={(v) => onUpdate(patchConfig(node, { model: v }))}
            options={[
              { value: 'gemini-2.5-flash', label: 'Gemini 2.5 Flash' },
              { value: 'gemini-2.5-pro', label: 'Gemini 2.5 Pro' },
              { value: 'gpt-4o', label: 'GPT-4o' },
              { value: 'gpt-4o-mini', label: 'GPT-4o mini' },
            ]}
          />
        </Field>
        <Field label="Temperatura">
          <NumberInput
            value={readNum(cfg, 'temperature')}
            min={0}
            max={2}
            onChange={(v) => onUpdate(patchConfig(node, { temperature: v === '' ? 0.7 : v }))}
          />
        </Field>
      </div>
      <Field label="Variável de saída" hint="onde guardar a resposta">
        <TextInput
          value={readStr(cfg, 'output_var') || 'gpt_resposta'}
          onChange={(v) => onUpdate(patchConfig(node, { output_var: v }))}
        />
      </Field>
    </div>
  );
}

export function ApiInspector({ node, onUpdate }: InspectorProps) {
  const cfg = node.data.config;
  return (
    <div className="space-y-3">
      <div className="grid grid-cols-[110px,1fr] gap-2">
        <Field label="Método">
          <Select
            value={readStr(cfg, 'method') || 'GET'}
            onChange={(v) => onUpdate(patchConfig(node, { method: v }))}
            options={[
              { value: 'GET', label: 'GET' },
              { value: 'POST', label: 'POST' },
              { value: 'PUT', label: 'PUT' },
              { value: 'PATCH', label: 'PATCH' },
              { value: 'DELETE', label: 'DELETE' },
            ]}
          />
        </Field>
        <Field label="URL">
          <TextInput
            value={readStr(cfg, 'url')}
            onChange={(v) => onUpdate(patchConfig(node, { url: v }))}
            placeholder="https://api.exemplo.com/path"
          />
        </Field>
      </div>
      <Field label="Headers (JSON)">
        <TextArea
          value={readStr(cfg, 'headers_json')}
          onChange={(v) => onUpdate(patchConfig(node, { headers_json: v }))}
          rows={3}
          placeholder='{"Authorization": "Bearer ..."}'
        />
      </Field>
      <Field label="Body (JSON)">
        <TextArea
          value={readStr(cfg, 'body_json')}
          onChange={(v) => onUpdate(patchConfig(node, { body_json: v }))}
          rows={4}
        />
      </Field>
      <Field label="Variável de saída">
        <TextInput
          value={readStr(cfg, 'output_var') || 'api_resposta'}
          onChange={(v) => onUpdate(patchConfig(node, { output_var: v }))}
        />
      </Field>
    </div>
  );
}

export function AbSplitInspector({ node, onUpdate }: InspectorProps) {
  const cfg = node.data.config;
  return (
    <div className="space-y-3">
      <div className="grid grid-cols-2 gap-2">
        <Field label="Peso A (%)">
          <NumberInput
            value={readNum(cfg, 'weight_a')}
            min={0}
            max={100}
            onChange={(v) => onUpdate(patchConfig(node, { weight_a: v === '' ? 50 : v }))}
          />
        </Field>
        <Field label="Peso B (%)">
          <NumberInput
            value={readNum(cfg, 'weight_b')}
            min={0}
            max={100}
            onChange={(v) => onUpdate(patchConfig(node, { weight_b: v === '' ? 50 : v }))}
          />
        </Field>
      </div>
      <p className="text-[11px] text-slate-500">
        Conecte 2 arestas saindo deste node — A pega a primeira, B pega a segunda
        (ordem dos handles do React Flow).
      </p>
    </div>
  );
}

export function MotorRefInspector({ node }: InspectorProps) {
  const moduleHint = readStr(node.data.config, 'module_hint');
  return (
    <div className="space-y-3">
      <Field label="Módulo Python" hint="referência (read-only)">
        <div className="rounded border border-cigana-border bg-cigana-bg px-2 py-1.5 text-sm text-slate-300 font-mono">
          {moduleHint || '— sem referência —'}
        </div>
      </Field>
      <p className="text-[11px] text-slate-500 leading-relaxed">
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

export function EndInspector() {
  return (
    <p className="text-[11px] text-slate-500 leading-relaxed">
      Bloco terminal. Marca o fim de um caminho do funil.
    </p>
  );
}
