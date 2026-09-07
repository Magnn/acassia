/**
 * hooks/useInboxRealtime.ts — SSE hook para real-time inbox updates
 *
 * Conecta ao endpoint /saas/inbox/stream via EventSource e dispara
 * invalidações do React Query automaticamente quando eventos chegam.
 *
 * Eventos suportados:
 *   - message_created → invalida conversa + lista
 *   - lead_updated → invalida lista + contexto
 *   - typing → seta estado de typing indicator
 *   - heartbeat → mantém conexão viva
 */

import { useEffect, useRef, useCallback, useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';

interface RealtimeEvent {
  type: string;
  lead_id?: number;
  tenant_id?: string;
  timestamp?: string;
  [key: string]: unknown;
}

interface UseInboxRealtimeOptions {
  /** Lead ID atualmente selecionado — para focar invalidações */
  selectedLeadId: number | null;
  /** Callback quando nova mensagem chega (para tocar som, etc.) */
  onNewMessage?: (event: RealtimeEvent) => void;
  /** Habilitar/desabilitar */
  enabled?: boolean;
}

interface RealtimeState {
  connected: boolean;
  typingLeadIds: Set<number>;
  lastEventAt: number | null;
  unreadMap: Map<number, number>;
}

export function useInboxRealtime({
  selectedLeadId,
  onNewMessage,
  enabled = true,
}: UseInboxRealtimeOptions) {
  const queryClient = useQueryClient();
  const eventSourceRef = useRef<EventSource | null>(null);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const reconnectAttemptRef = useRef(0);

  const [state, setState] = useState<RealtimeState>({
    connected: false,
    typingLeadIds: new Set(),
    lastEventAt: null,
    unreadMap: new Map(),
  });

  // Referência estável do selectedLeadId para uso em callbacks
  const selectedLeadIdRef = useRef(selectedLeadId);
  selectedLeadIdRef.current = selectedLeadId;

  const onNewMessageRef = useRef(onNewMessage);
  onNewMessageRef.current = onNewMessage;

  const connect = useCallback(() => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
    }

    const es = new EventSource('/saas/inbox/stream', { withCredentials: true });
    eventSourceRef.current = es;

    // ── Conexão estabelecida ──
    es.addEventListener('connected', () => {
      setState(s => ({ ...s, connected: true }));
      reconnectAttemptRef.current = 0;
    });

    // ── Nova mensagem ──
    es.addEventListener('message_created', (e) => {
      try {
        const data: RealtimeEvent = JSON.parse(e.data);
        const leadId = data.lead_id;

        // Atualizar unread count se a mensagem não é da conversa aberta
        if (leadId && leadId !== selectedLeadIdRef.current) {
          setState(s => {
            const newUnread = new Map(s.unreadMap);
            newUnread.set(leadId, (newUnread.get(leadId) || 0) + 1);
            return { ...s, unreadMap: newUnread, lastEventAt: Date.now() };
          });
        }

        // Invalidar queries
        queryClient.invalidateQueries({ queryKey: ['leads-list'] });
        if (leadId && leadId === selectedLeadIdRef.current) {
          queryClient.invalidateQueries({ queryKey: ['leads-conversation', leadId] });
        }

        // Callback
        onNewMessageRef.current?.(data);
      } catch {
        // silêncio
      }
    });

    // ── Lead atualizado (status, score, etc.) ──
    es.addEventListener('lead_updated', (e) => {
      try {
        const data = JSON.parse(e.data);
        queryClient.invalidateQueries({ queryKey: ['leads-list'] });
        if (data.lead_id === selectedLeadIdRef.current) {
          queryClient.invalidateQueries({ queryKey: ['lead-context', data.lead_id] });
        }
      } catch {
        // silêncio
      }
    });

    // ── Typing indicator ──
    es.addEventListener('typing', (e) => {
      try {
        const data = JSON.parse(e.data);
        const leadId = data.lead_id;
        if (!leadId) return;

        setState(s => {
          const newTyping = new Set(s.typingLeadIds);
          newTyping.add(leadId);
          return { ...s, typingLeadIds: newTyping };
        });

        // Auto-limpar typing após 4s
        setTimeout(() => {
          setState(s => {
            const newTyping = new Set(s.typingLeadIds);
            newTyping.delete(leadId);
            return { ...s, typingLeadIds: newTyping };
          });
        }, 4000);
      } catch {
        // silêncio
      }
    });

    // ── Heartbeat ──
    es.addEventListener('heartbeat', () => {
      setState(s => ({ ...s, lastEventAt: Date.now() }));
    });

    // ── Erro / reconexão ──
    es.onerror = () => {
      setState(s => ({ ...s, connected: false }));
      es.close();
      eventSourceRef.current = null;

      // Reconexão exponencial (1s, 2s, 4s, 8s, max 30s)
      const delay = Math.min(30000, 1000 * Math.pow(2, reconnectAttemptRef.current));
      reconnectAttemptRef.current += 1;

      reconnectTimerRef.current = setTimeout(() => {
        if (enabled) connect();
      }, delay);
    };
  }, [enabled, queryClient]);

  // Conectar/desconectar
  useEffect(() => {
    if (!enabled) return;

    connect();

    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
        eventSourceRef.current = null;
      }
      if (reconnectTimerRef.current) {
        clearTimeout(reconnectTimerRef.current);
      }
    };
  }, [enabled, connect]);

  // Limpar unread do lead selecionado
  useEffect(() => {
    if (selectedLeadId == null) return;
    setState(s => {
      if (!s.unreadMap.has(selectedLeadId)) return s;
      const newUnread = new Map(s.unreadMap);
      newUnread.delete(selectedLeadId);
      return { ...s, unreadMap: newUnread };
    });
  }, [selectedLeadId]);

  const markRead = useCallback((leadId: number) => {
    setState(s => {
      const newUnread = new Map(s.unreadMap);
      newUnread.delete(leadId);
      return { ...s, unreadMap: newUnread };
    });
  }, []);

  return {
    connected: state.connected,
    typingLeadIds: state.typingLeadIds,
    unreadMap: state.unreadMap,
    lastEventAt: state.lastEventAt,
    markRead,
    totalUnread: Array.from(state.unreadMap.values()).reduce((a, b) => a + b, 0),
  };
}
