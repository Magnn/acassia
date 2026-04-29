import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  addEdge,
  applyEdgeChanges,
  applyNodeChanges,
  type Connection,
  type Edge,
  type EdgeChange,
  type Node,
  type NodeChange,
} from '@xyflow/react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { blueprintsApi } from '../api/blueprints';
import { documentToReactFlow, type FlowNodeData } from '../lib/adapt';
import { newId, reactFlowToDocument } from '../lib/serialize';
import type { AcassiaDocument, AcassiaNodeType } from '../lib/types';

export type SaveStatus = 'idle' | 'dirty' | 'saving' | 'saved' | 'error';

const SAVE_DEBOUNCE_MS = 800;

interface UseFlowStateOpts {
  blueprintId: number;
  initialDoc: AcassiaDocument;
}

export function useFlowState({ blueprintId, initialDoc }: UseFlowStateOpts) {
  const initial = useMemo(() => documentToReactFlow(initialDoc), [initialDoc]);
  const [nodes, setNodes] = useState<Node<FlowNodeData>[]>(initial.nodes);
  const [edges, setEdges] = useState<Edge[]>(initial.edges);
  const [status, setStatus] = useState<SaveStatus>('idle');
  const [error, setError] = useState<string | null>(null);

  const docRef = useRef(initialDoc);
  const queryClient = useQueryClient();

  const mutation = useMutation({
    mutationFn: (next: AcassiaDocument) =>
      blueprintsApi.update(blueprintId, { body: next as Record<string, unknown> }),
    onSuccess: () => {
      setStatus('saved');
      setError(null);
      queryClient.invalidateQueries({ queryKey: ['blueprints'] });
    },
    onError: (e) => {
      setStatus('error');
      setError((e as Error).message);
    },
  });

  // Debounced save: sempre que entrar em "dirty", agenda PATCH 800ms depois.
  const dirtyAt = useRef<number | null>(null);
  useEffect(() => {
    if (status !== 'dirty') return;
    const handle = window.setTimeout(() => {
      const doc = reactFlowToDocument(docRef.current, nodes, edges);
      docRef.current = doc;
      setStatus('saving');
      mutation.mutate(doc);
    }, SAVE_DEBOUNCE_MS);
    return () => window.clearTimeout(handle);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [status, nodes, edges]);

  const markDirty = useCallback(() => {
    dirtyAt.current = Date.now();
    setStatus('dirty');
  }, []);

  const onNodesChange = useCallback(
    (changes: NodeChange<Node<FlowNodeData>>[]) => {
      setNodes((curr) => applyNodeChanges(changes, curr));
      // Apenas mudanças que alteram o documento marcam dirty.
      // Ignoramos 'select' e 'dimensions' (puramente UI).
      if (changes.some((c) => c.type !== 'select' && c.type !== 'dimensions')) {
        markDirty();
      }
    },
    [markDirty],
  );

  const onEdgesChange = useCallback(
    (changes: EdgeChange[]) => {
      setEdges((curr) => applyEdgeChanges(changes, curr));
      if (changes.some((c) => c.type !== 'select')) markDirty();
    },
    [markDirty],
  );

  const onConnect = useCallback(
    (conn: Connection) => {
      setEdges((curr) =>
        addEdge({ ...conn, id: newId('e'), type: 'default' }, curr),
      );
      markDirty();
    },
    [markDirty],
  );

  const addNode = useCallback(
    (type: AcassiaNodeType, position: { x: number; y: number }, label?: string) => {
      const node: Node<FlowNodeData> = {
        id: newId('n'),
        type: 'acassia',
        position,
        data: { label: label ?? defaultLabel(type), acassiaType: type, config: {} },
      };
      setNodes((curr) => [...curr, node]);
      markDirty();
      return node.id;
    },
    [markDirty],
  );

  const updateNode = useCallback(
    (id: string, patch: Partial<FlowNodeData>) => {
      setNodes((curr) =>
        curr.map((n) =>
          n.id === id ? { ...n, data: { ...n.data, ...patch } } : n,
        ),
      );
      markDirty();
    },
    [markDirty],
  );

  const selectedNodeId = nodes.find((n) => n.selected)?.id ?? null;
  const selectedNode = nodes.find((n) => n.selected) ?? null;

  return {
    nodes,
    edges,
    status,
    error,
    selectedNodeId,
    selectedNode,
    onNodesChange,
    onEdgesChange,
    onConnect,
    addNode,
    updateNode,
  };
}

function defaultLabel(type: AcassiaNodeType): string {
  const map: Record<string, string> = {
    trigger: 'Gatilho',
    conteudo: 'Conteúdo',
    delay: 'Delay',
    condicao: 'Condição',
    gpt: 'IA / GPT',
    api: 'API',
    ab_split: 'Divisão A/B',
    motor_ref: 'Motor Python',
    anotacao: 'Anotação',
    end: 'Fim',
  };
  return map[type] ?? type;
}
