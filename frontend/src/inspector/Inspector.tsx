import type { Node } from '@xyflow/react';
import { X } from 'lucide-react';
import type { FlowNodeData } from '../lib/adapt';
import { visualForType } from '../builder/nodeStyles';
import {
  AbSplitInspector,
  AnotacaoInspector,
  ApiInspector,
  CommonHeader,
  CondicaoInspector,
  ConteudoInspector,
  DelayInspector,
  EndInspector,
  GptInspector,
  MotorRefInspector,
  TriggerInspector,
} from './inspectors';
import type { InspectorProps } from './helpers';

interface Props {
  node: Node<FlowNodeData>;
  onUpdate: (patch: Partial<FlowNodeData>) => void;
  onClose: () => void;
}

export default function Inspector({ node, onUpdate, onClose }: Props) {
  const v = visualForType(node.data.acassiaType);
  const inspectorProps: InspectorProps = { node, onUpdate };

  return (
    <aside className="w-80 flex-shrink-0 border-l border-sibila-mist bg-sibila-obsidian flex flex-col h-full animate-slide-in-right shadow-xl">
      <header className="flex items-center justify-between px-3 py-2 border-b border-sibila-mist flex-shrink-0">
        <div className="flex items-center gap-2 text-[11px] uppercase tracking-wide text-sibila-fog">
          <v.Icon className={`w-3.5 h-3.5 ${v.accent}`} strokeWidth={2.25} />
          <span>{v.label}</span>
        </div>
        <button
          onClick={onClose}
          className="text-sibila-fog hover:text-sibila-moonlight p-1 rounded hover:bg-sibila-onyx"
          title="Fechar inspetor (deselecionar)"
        >
          <X className="w-4 h-4" />
        </button>
      </header>

      <div className="flex-1 overflow-y-auto px-3 py-3 space-y-4">
        <CommonHeader {...inspectorProps} />
        <div className="border-t border-sibila-mist pt-4">
          {renderTypeBody(inspectorProps)}
        </div>
      </div>

      <footer className="px-3 py-2 border-t border-sibila-mist text-[10px] text-sibila-smoke font-mono flex-shrink-0">
        id: {node.id}
      </footer>
    </aside>
  );
}

function renderTypeBody(p: InspectorProps) {
  switch (p.node.data.acassiaType) {
    case 'trigger':
      return <TriggerInspector {...p} />;
    case 'conteudo':
      return <ConteudoInspector {...p} />;
    case 'delay':
      return <DelayInspector {...p} />;
    case 'condicao':
      return <CondicaoInspector {...p} />;
    case 'gpt':
      return <GptInspector {...p} />;
    case 'api':
      return <ApiInspector {...p} />;
    case 'ab_split':
      return <AbSplitInspector {...p} />;
    case 'motor_ref':
      return <MotorRefInspector {...p} />;
    case 'anotacao':
      return <AnotacaoInspector {...p} />;
    case 'end':
      return <EndInspector />;
    default:
      return (
        <p className="text-[11px] text-sibila-smoke">
          Tipo "{p.node.data.acassiaType}" sem inspetor dedicado ainda.
        </p>
      );
  }
}
