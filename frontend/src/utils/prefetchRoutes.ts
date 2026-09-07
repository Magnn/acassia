/**
 * Route prefetching — pré-carrega chunks de rotas prováveis.
 *
 * Vite faz code-splitting automático com lazy(). Este módulo adiciona
 * prefetching inteligente: quando o user está no Dashboard, pré-carrega
 * Leads e Builder (os destinos mais prováveis).
 *
 * Uso em Layout.tsx:
 *   useEffect(() => { prefetchRoutes('dashboard'); }, []);
 */

type RouteGroup = 'dashboard' | 'leads' | 'builder' | 'settings';

const PREFETCH_MAP: Record<RouteGroup, (() => Promise<unknown>)[]> = {
  dashboard: [
    () => import('../routes/Leads'),
    () => import('../routes/Builder'),
    () => import('../routes/Pipeline'),
  ],
  leads: [
    () => import('../routes/Builder'),
    () => import('../routes/Funnel'),
  ],
  builder: [
    () => import('../routes/Runs'),
    () => import('../routes/Catalog'),
  ],
  settings: [
    () => import('../routes/settings/Devices'),
    () => import('../routes/settings/Security'),
  ],
};

let _prefetched = new Set<RouteGroup>();

/**
 * Pré-carrega chunks de rotas prováveis a partir do contexto atual.
 * Usa requestIdleCallback para não bloquear a thread principal.
 * Cada grupo é prefetched no máximo uma vez por sessão.
 */
export function prefetchRoutes(group: RouteGroup): void {
  if (_prefetched.has(group)) return;
  _prefetched.add(group);

  const imports = PREFETCH_MAP[group];
  if (!imports?.length) return;

  const schedule = typeof requestIdleCallback === 'function'
    ? requestIdleCallback
    : (fn: () => void) => setTimeout(fn, 200);

  schedule(() => {
    imports.forEach((load) => {
      load().catch(() => {
        // Silencioso — prefetch é best-effort
      });
    });
  });
}
