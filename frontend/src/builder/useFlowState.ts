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
import { toast } from '../lib/toast';
import type { MeuMisterioDocument, MeuMisterioNodeType } from '../lib/types';

export type SaveStatus = 'idle' | 'dirty' | 'saving' | 'saved' | 'error';

const SAVE_DEBOUNCE_MS = 800;
const HISTORY_DEBOUNCE_MS = 350;
const HISTORY_MAX = 50;

interface Snapshot {
  nodes: Node<FlowNodeData>[];
  edges: Edge[];
}

interface UseFlowStateOpts {
  blueprintId: number;
  initialDoc: MeuMisterioDocument;
}

export function useFlowState({ blueprintId, initialDoc }: UseFlowStateOpts) {
  const initial = useMemo(() => documentToReactFlow(initialDoc), [initialDoc]);
  const [nodes, setNodes] = useState<Node<FlowNodeData>[]>(initial.nodes);
  const [edges, setEdges] = useState<Edge[]>(initial.edges);
  const [status, setStatus] = useState<SaveStatus>('idle');
  const [error, setError] = useState<string | null>(null);

  // Histórico para Undo/Redo. Snapshots são referências aos arrays React Flow
  // (imutáveis após a mutação), então não custa memória adicional além do array.
  const [history, setHistory] = useState<{ past: Snapshot[]; future: Snapshot[] }>(
    { past: [], future: [] },
  );
  const lastSnapshotRef = useRef<Snapshot>({
    nodes: initial.nodes,
    edges: initial.edges,
  });
  const isRestoringRef = useRef(false);

  const docRef = useRef(initialDoc);
  const queryClient = useQueryClient();

  const mutation = useMutation({
    mutationFn: (next: MeuMisterioDocument) =>
      blueprintsApi.update(blueprintId, { body: next as Record<string, unknown> }),
    onSuccess: () => {
      setStatus('saved');
      setError(null);
      queryClient.invalidateQueries({ queryKey: ['blueprints'] });
    },
    onError: (e) => {
      setStatus('error');
      setError((e as Error).message);
      toast.error(`Falha ao salvar: ${(e as Error).message}`);
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

  // Captura snapshots do estado anterior 350ms após cada mudança "estabilizada".
  // Estratégia: isRestoring=true durante undo/redo bloqueia push (evita loop).
  useEffect(() => {
    if (isRestoringRef.current) {
      isRestoringRef.current = false;
      lastSnapshotRef.current = { nodes, edges };
      return;
    }
    const handle = window.setTimeout(() => {
      const prev = lastSnapshotRef.current;
      if (prev.nodes === nodes && prev.edges === edges) return;
      setHistory((h) => ({
        past: [...h.past, prev].slice(-HISTORY_MAX),
        future: [],
      }));
      lastSnapshotRef.current = { nodes, edges };
    }, HISTORY_DEBOUNCE_MS);
    return () => window.clearTimeout(handle);
  }, [nodes, edges]);

  const undo = useCallback(() => {
    setHistory((h) => {
      if (h.past.length === 0) return h;
      const target = h.past[h.past.length - 1];
      const newPast = h.past.slice(0, -1);
      isRestoringRef.current = true;
      setNodes(target.nodes);
      setEdges(target.edges);
      markDirty();
      return {
        past: newPast,
        future: [{ nodes, edges }, ...h.future].slice(0, HISTORY_MAX),
      };
    });
  }, [nodes, edges, markDirty]);

  const redo = useCallback(() => {
    setHistory((h) => {
      if (h.future.length === 0) return h;
      const target = h.future[0];
      const newFuture = h.future.slice(1);
      isRestoringRef.current = true;
      setNodes(target.nodes);
      setEdges(target.edges);
      markDirty();
      return {
        past: [...h.past, { nodes, edges }].slice(-HISTORY_MAX),
        future: newFuture,
      };
    });
  }, [nodes, edges, markDirty]);

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
    (type: MeuMisterioNodeType, position: { x: number; y: number }, label?: string) => {
      const node: Node<FlowNodeData> = {
        id: newId('n'),
        type: 'meumisterio',
        position,
        data: { label: label ?? defaultLabel(type), meumisterioType: type, config: {} },
      };
      setNodes((curr) => [...curr, node]);
      markDirty();
      return node.id;
    },
    [markDirty],
  );

  const duplicateNode = useCallback(
    (id: string) => {
      setNodes((curr) => {
        const source = curr.find((n) => n.id === id);
        if (!source) return curr;
        const clone: Node<FlowNodeData> = {
          id: newId('n'),
          type: 'meumisterio',
          position: { x: source.position.x + 40, y: source.position.y + 60 },
          data: {
            ...structuredClone(source.data),
            label: `${source.data.label || defaultLabel(source.data.meumisterioType as MeuMisterioNodeType)} (cópia)`,
          },
        };
        return [...curr, clone];
      });
      markDirty();
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
    duplicateNode,
    updateNode,
    undo,
    redo,
    canUndo: history.past.length > 0,
    canRedo: history.future.length > 0,
  };
}

function defaultLabel(type: MeuMisterioNodeType): string {
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
