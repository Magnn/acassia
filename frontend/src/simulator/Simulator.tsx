import { useCallback, useEffect, useRef, useState } from 'react';
import type { Edge, Node } from '@xyflow/react';
import {
  ArrowRight,
  CheckCircle2,
  Clock,
  HelpCircle,
  Play,
  Square,
  StopCircle,
  X,
  XCircle,
} from 'lucide-react';
import type { FlowNodeData } from '../lib/adapt';
import PersonaPicker from './PersonaPicker';
import { walk, type SimStep, type WalkerControl } from './walker';
import type { Persona } from './vars';

interface Props {
  nodes: Node<FlowNodeData>[];
  edges: Edge[];
  onCurrentNodeChange?: (nodeId: string | null) => void;
  onClose: () => void;
}

interface BubbleEntry {
  id: number;
  step: SimStep;
}

const STORAGE_KEY = 'meumisterio.builder.persona';

export default function Simulator({
  nodes,
  edges,
  onCurrentNodeChange,
  onClose,
}: Props) {
  const [persona, setPersona] = useState<Persona>(() => loadPersona());
  const [bubbles, setBubbles] = useState<BubbleEntry[]>([]);
  const [running, setRunning] = useState(false);
  const [pendingChoice, setPendingChoice] = useState<((v: boolean) => void) | null>(
    null,
  );
  const seqRef = useRef(0);
  const cancelRef = useRef(false);

  // Persistir persona entre sessões.
  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(persona));
    } catch {}
  }, [persona]);

  const append = useCallback((step: SimStep) => {
    seqRef.current += 1;
    setBubbles((b) => [...b, { id: seqRef.current, step }]);
  }, []);

  const reset = useCallback(() => {
    cancelRef.current = true;
    setBubbles([]);
    setPendingChoice(null);
    setRunning(false);
    onCurrentNodeChange?.(null);
  }, [onCurrentNodeChange]);

  const run = useCallback(async () => {
    if (running) return;
    setBubbles([]);
    cancelRef.current = false;
    setRunning(true);

    const control: WalkerControl = {
      awaitChoice: () =>
        new Promise<boolean>((resolve) => {
          if (cancelRef.current) return resolve(false);
          setPendingChoice(() => (v: boolean) => {
            setPendingChoice(null);
            resolve(v);
          });
        }),
    };

    try {
      for await (const step of walk({ nodes, edges, persona, control })) {
        if (cancelRef.current) break;
        append(step);
        if (step.kind === 'enter') {
          onCurrentNodeChange?.(step.nodeId);
        }
        if (step.kind === 'delay' && step.seconds > 0) {
          // Evita esperar minutos no preview — cap em 1.5s simulado.
          await sleep(Math.min(step.seconds * 1000, 1500));
        } else {
          await sleep(220); // ritmo de leitura
        }
      }
    } finally {
      setRunning(false);
      onCurrentNodeChange?.(null);
    }
  }, [nodes, edges, persona, running, append, onCurrentNodeChange]);

  return (
    <aside className="w-96 flex-shrink-0 border-l border-sibila-mist bg-sibila-obsidian flex flex-col h-full animate-slide-in-right shadow-xl">
      <header className="flex items-center justify-between px-3 py-2 border-b border-sibila-mist flex-shrink-0">
        <span className="text-[11px] uppercase tracking-wide text-sibila-fog flex items-center gap-1.5">
          <Play className="w-3.5 h-3.5 text-sibila-amethyst" fill="currentColor" />
          Simulador
        </span>
        <div className="flex items-center gap-2">
          {running ? (
            <button
              type="button"
              onClick={reset}
              className="text-xs px-2 py-0.5 rounded border border-sibila-mist hover:border-red-400 hover:text-red-400 flex items-center gap-1"
            >
              <Square className="w-3 h-3" fill="currentColor" />
              parar
            </button>
          ) : (
            <button
              type="button"
              onClick={run}
              className="text-xs px-2 py-0.5 rounded bg-sibila-amethyst text-white hover:brightness-110 flex items-center gap-1"
            >
              <Play className="w-3 h-3" fill="currentColor" />
              executar
            </button>
          )}
          <button
            type="button"
            onClick={onClose}
            className="text-sibila-fog hover:text-sibila-moonlight p-1 rounded hover:bg-sibila-onyx"
            title="Fechar simulador"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      </header>

      <div className="flex-1 min-h-0 flex flex-col">
        <div
          ref={(el) => {
            if (el) el.scrollTop = el.scrollHeight;
          }}
          className="flex-1 overflow-y-auto bg-gradient-to-b from-[#f8f9fd] to-[#f5f7fc] px-3 py-3 space-y-2"
        >
          {bubbles.length === 0 && (
            <p className="text-xs text-sibila-smoke text-center mt-4">
              Clique em <strong>executar</strong> para simular o fluxo.
              {' '}Conteúdo, Delay, Condição e Fim são interpretados; outros tipos
              aparecem como stubs.
            </p>
          )}
          {bubbles.map((b) => (
            <Bubble key={b.id} step={b.step} />
          ))}
          {pendingChoice && (
            <div className="flex items-center gap-2 mt-2">
              <button
                type="button"
                onClick={() => pendingChoice(true)}
                className="text-xs px-3 py-1 rounded bg-emerald-500/80 text-white hover:bg-emerald-500 flex items-center gap-1"
              >
                <CheckCircle2 className="w-3.5 h-3.5" />
                sim (verdadeiro)
              </button>
              <button
                type="button"
                onClick={() => pendingChoice(false)}
                className="text-xs px-3 py-1 rounded bg-rose-500/80 text-white hover:bg-rose-500 flex items-center gap-1"
              >
                <XCircle className="w-3.5 h-3.5" />
                não (falso)
              </button>
            </div>
          )}
        </div>

        <div className="border-t border-sibila-mist p-3">
          <PersonaPicker persona={persona} onChange={setPersona} />
        </div>
      </div>
    </aside>
  );
}

function Bubble({ step }: { step: SimStep }) {
  if (step.kind === 'text') {
    return (
      <div className="rounded-lg rounded-bl-sm bg-[#f1edff] border border-[#ddd2ff] px-3 py-2 text-[13px] text-[#3a2f75] max-w-[85%] whitespace-pre-wrap break-words shadow-sm">
        {step.text || '(mensagem vazia)'}
      </div>
    );
  }
  if (step.kind === 'media') {
    return (
      <div className="rounded-lg rounded-bl-sm bg-[#f1edff] border border-[#ddd2ff] px-3 py-2 max-w-[85%] space-y-1 shadow-sm">
        <div className="text-[10px] uppercase tracking-wide text-[#7c5af5]">
          {step.mediaType}
        </div>
        {step.mediaType === 'image' && step.url ? (
          <img src={step.url} alt="" className="max-h-32 rounded" />
        ) : step.mediaType === 'audio' && step.url ? (
          <audio src={step.url} controls className="w-full" />
        ) : step.mediaType === 'video' && step.url ? (
          <video src={step.url} controls className="max-h-32 w-full rounded" />
        ) : (
          <a
            href={step.url}
            target="_blank"
            rel="noreferrer"
            className="text-xs text-[#7c5af5] underline break-all"
          >
            {step.url || '(sem URL)'}
          </a>
        )}
        {step.caption && (
          <div className="text-[13px] text-[#3a2f75]">{step.caption}</div>
        )}
      </div>
    );
  }
  if (step.kind === 'delay') {
    return (
      <div className="text-[10px] text-sibila-smoke italic flex items-center gap-1">
        <Clock className="w-3 h-3 animate-pulse" />
        <span>aguardando {step.seconds}s</span>
      </div>
    );
  }
  if (step.kind === 'choice') {
    return (
      <div className="rounded border border-amber-500/40 bg-amber-900/20 px-3 py-2 text-xs text-amber-200 flex items-center gap-1.5">
        <HelpCircle className="w-3.5 h-3.5 flex-shrink-0" />
        <span>{step.question}</span>
      </div>
    );
  }
  if (step.kind === 'enter') {
    return (
      <div className="text-[10px] text-sibila-smoke font-mono flex items-center gap-1">
        <ArrowRight className="w-3 h-3" />
        <span>
          entra em <span className="text-sibila-fog">{step.label}</span>{' '}
          <span className="text-sibila-smoke/70">[{step.type}]</span>
        </span>
      </div>
    );
  }
  if (step.kind === 'stub') {
    return (
      <div className="rounded border border-sibila-mist bg-sibila-obsidian px-3 py-2 text-xs text-sibila-fog">
        <div className="text-[10px] uppercase tracking-wide text-sibila-smoke">
          {step.label}
        </div>
        <div className="mt-0.5 break-words">{step.detail}</div>
      </div>
    );
  }
  if (step.kind === 'end') {
    return (
      <div className="text-xs text-emerald-400 font-medium flex items-center gap-1">
        <StopCircle className="w-3.5 h-3.5" />
        <span>fim — {step.label}</span>
      </div>
    );
  }
  return (
    <div className="text-xs text-red-400 flex items-center gap-1">
      <XCircle className="w-3.5 h-3.5" />
      <span>{step.reason}</span>
    </div>
  );
}

function sleep(ms: number) {
  return new Promise<void>((r) => setTimeout(r, ms));
}

function loadPersona(): Persona {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return { 'lead.nome': 'Maria' };
    const parsed = JSON.parse(raw);
    return parsed && typeof parsed === 'object' ? parsed : {};
  } catch {
    return {};
  }
}
