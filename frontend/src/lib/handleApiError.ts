import { ApiError } from '../api/client';
import { toast } from './toast';

/**
 * Helper centralizado pra tratar erros de API em mutations.
 *
 * - 402 quota_exceeded → toast com CTA pra upgrade
 * - 401 unauthorized → redirect login
 * - 403 forbidden → toast genérico
 * - default → fallback message
 */
export function handleApiError(fallback: string = 'Erro inesperado') {
  return (e: unknown) => {
    if (e instanceof ApiError) {
      // Quota exceeded: mostra mensagem específica + sugestão de upgrade
      if (e.isQuotaExceeded) {
        const info = e.quotaInfo;
        toast.error(
          info?.message || 'Limite do plano atingido. Faça upgrade pra continuar.',
          6000,
        );
        return;
      }

      if (e.status === 401) {
        // Frontend pode redirect — Layout já trata
        toast.error('Sessão expirada — faça login novamente');
        return;
      }

      if (e.status === 403) {
        const body = e.body as { error?: string; reason?: string } | null;
        toast.error(`Acesso negado${body?.reason ? `: ${body.reason}` : ''}`);
        return;
      }

      if (e.status === 423) {
        toast.error('Conta temporariamente bloqueada — aguarde alguns minutos', 6000);
        return;
      }

      if (e.status === 429) {
        toast.error('Muitas requisições — aguarde 1 minuto', 5000);
        return;
      }

      // Mensagem do backend se disponível
      const body = e.body as { message?: string; error?: string } | null;
      if (body?.message) {
        toast.error(body.message);
        return;
      }
      if (body?.error) {
        toast.error(`${fallback}: ${body.error}`);
        return;
      }
    }

    if (e instanceof Error) {
      toast.error(`${fallback}: ${e.message}`);
      return;
    }

    toast.error(fallback);
  };
}
