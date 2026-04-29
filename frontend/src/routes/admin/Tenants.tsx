import { useState, useMemo } from 'react';
import { useQuery, keepPreviousData } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import {
  Search,
  ChevronRight,
  Mail,
  CheckCircle2,
  AlertCircle,
  Trash2,
  Pause,
  Crown,
} from 'lucide-react';
import { adminApi, type ListTenantsFilters, type AdminTenantRow } from '../../api/admin';

const PAGE_SIZE = 50;

const PLAN_COLORS: Record<string, string> = {
  free: 'bg-zinc-800 text-zinc-400 border-zinc-700',
  starter: 'bg-blue-950 text-blue-300 border-blue-900',
  pro: 'bg-purple-950 text-purple-300 border-purple-900',
  enterprise: 'bg-amber-950 text-amber-300 border-amber-900',
};

function formatRelative(iso: string | null): string {
  if (!iso) return '—';
  const d = new Date(iso);
  const diffMs = Date.now() - d.getTime();
  const diffMin = Math.floor(diffMs / 60000);
  if (diffMin < 1) return 'agora';
  if (diffMin < 60) return `${diffMin}m`;
  const diffH = Math.floor(diffMin / 60);
  if (diffH < 24) return `${diffH}h`;
  const diffD = Math.floor(diffH / 24);
  if (diffD < 30) return `${diffD}d`;
  return d.toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit' });
}

function formatDate(iso: string | null): string {
  if (!iso) return '—';
  return new Date(iso).toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit', year: '2-digit' });
}

export default function AdminTenants() {
  const [search, setSearch] = useState('');
  const [planFilter, setPlanFilter] = useState<string>('');
  const [statusFilter, setStatusFilter] = useState<'active' | 'suspended' | 'deleted' | 'all'>('active');
  const [sort, setSort] = useState('criado_em:desc');
  const [cursor, setCursor] = useState(0);

  const filters: ListTenantsFilters = useMemo(() => ({
    cursor,
    limit: PAGE_SIZE,
    search: search.trim() || undefined,
    plan: planFilter || undefined,
    status: statusFilter,
    sort,
  }), [cursor, search, planFilter, statusFilter, sort]);

  const { data, isLoading, isFetching } = useQuery({
    queryKey: ['admin-tenants', filters],
    queryFn: () => adminApi.listTenants(filters),
    placeholderData: keepPreviousData,
  });

  const tenants = data?.tenants ?? [];

  const handleSort = (field: string) => {
    const [curField, curDir] = sort.split(':');
    if (curField === field) {
      setSort(`${field}:${curDir === 'asc' ? 'desc' : 'asc'}`);
    } else {
      setSort(`${field}:desc`);
    }
    setCursor(0);
  };

  const sortIndicator = (field: string) => {
    const [curField, curDir] = sort.split(':');
    if (curField !== field) return null;
    return curDir === 'asc' ? '↑' : '↓';
  };

  return (
    <div className="p-8 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-black tracking-tight">Tenants</h1>
          <p className="text-zinc-500 text-sm font-medium mt-1">
            {data?.total_count ?? 0} contas registradas
          </p>
        </div>
      </div>

      {/* Filters bar */}
      <div className="bg-zinc-900/50 border border-zinc-800 rounded-2xl p-4 flex items-center gap-3 flex-wrap">
        {/* Search */}
        <div className="relative flex-1 min-w-[240px]">
          <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-zinc-600" />
          <input
            type="text"
            placeholder="Buscar email, nome, tenant_id..."
            value={search}
            onChange={(e) => { setSearch(e.target.value); setCursor(0); }}
            className="w-full pl-10 pr-4 py-2.5 bg-zinc-950 border border-zinc-800 rounded-xl text-sm text-white placeholder:text-zinc-600 focus:border-red-500/50 focus:outline-none"
          />
        </div>

        {/* Plan filter */}
        <select
          value={planFilter}
          onChange={(e) => { setPlanFilter(e.target.value); setCursor(0); }}
          className="px-3 py-2.5 bg-zinc-950 border border-zinc-800 rounded-xl text-xs font-bold text-white focus:outline-none focus:border-red-500/50"
        >
          <option value="">Todos os planos</option>
          <option value="free">Free</option>
          <option value="starter">Starter</option>
          <option value="pro">Pro</option>
          <option value="enterprise">Enterprise</option>
        </select>

        {/* Status filter */}
        <select
          value={statusFilter}
          onChange={(e) => { setStatusFilter(e.target.value as 'active' | 'suspended' | 'deleted' | 'all'); setCursor(0); }}
          className="px-3 py-2.5 bg-zinc-950 border border-zinc-800 rounded-xl text-xs font-bold text-white focus:outline-none focus:border-red-500/50"
        >
          <option value="active">Ativos</option>
          <option value="suspended">Suspensos</option>
          <option value="deleted">Deletados</option>
          <option value="all">Todos</option>
        </select>

        {isFetching && (
          <div className="w-4 h-4 border-2 border-red-500/30 border-t-red-500 rounded-full animate-spin" />
        )}
      </div>

      {/* Table */}
      <div className="bg-zinc-900/50 border border-zinc-800 rounded-2xl overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-zinc-950/60 border-b border-zinc-800">
              <tr className="text-left text-[10px] font-black uppercase tracking-widest text-zinc-500">
                <Th onClick={() => handleSort('email')}>Tenant {sortIndicator('email')}</Th>
                <Th>Plano</Th>
                <Th>MRR</Th>
                <Th onClick={() => handleSort('criado_em')}>Signup {sortIndicator('criado_em')}</Th>
                <Th onClick={() => handleSort('last_login_at')}>Último login {sortIndicator('last_login_at')}</Th>
                <Th>Leads 30d</Th>
                <Th>Msgs 30d</Th>
                <Th>Status</Th>
                <Th></Th>
              </tr>
            </thead>
            <tbody>
              {isLoading ? (
                <SkeletonRows count={10} />
              ) : tenants.length === 0 ? (
                <tr>
                  <td colSpan={9} className="py-16 text-center text-zinc-600 text-sm">
                    Nenhum tenant encontrado com esses filtros
                  </td>
                </tr>
              ) : (
                tenants.map((t) => <TenantRow key={t.tenant_id} tenant={t} />)
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        {data && (data.cursor_next !== null || cursor > 0) && (
          <div className="border-t border-zinc-800 px-4 py-3 flex items-center justify-between">
            <div className="text-xs text-zinc-500">
              Mostrando {cursor + 1}–{cursor + tenants.length} de {data.total_count}
            </div>
            <div className="flex gap-2">
              <button
                onClick={() => setCursor(Math.max(0, cursor - PAGE_SIZE))}
                disabled={cursor === 0}
                className="px-3 py-1.5 bg-zinc-900 hover:bg-zinc-800 disabled:opacity-30 disabled:cursor-not-allowed rounded-lg text-[11px] font-black uppercase tracking-widest"
              >
                Anterior
              </button>
              <button
                onClick={() => data.cursor_next !== null && setCursor(data.cursor_next)}
                disabled={data.cursor_next === null}
                className="px-3 py-1.5 bg-zinc-900 hover:bg-zinc-800 disabled:opacity-30 disabled:cursor-not-allowed rounded-lg text-[11px] font-black uppercase tracking-widest"
              >
                Próxima
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function Th({ children, onClick }: { children?: React.ReactNode; onClick?: () => void }) {
  return (
    <th
      onClick={onClick}
      className={`px-4 py-3 ${onClick ? 'cursor-pointer hover:text-white select-none' : ''}`}
    >
      {children}
    </th>
  );
}

function TenantRow({ tenant }: { tenant: AdminTenantRow }) {
  const planColor = PLAN_COLORS[tenant.plan] || PLAN_COLORS.free;
  const isAdmin = tenant.role === 'admin';

  return (
    <tr className="border-b border-zinc-900/50 hover:bg-zinc-900/30 transition-colors group">
      <td className="px-4 py-3">
        <div className="flex items-center gap-2">
          {isAdmin && (
            <span title="Admin"><Crown className="w-3.5 h-3.5 text-amber-500" /></span>
          )}
          <div>
            <div className="font-bold text-white truncate max-w-[200px]">{tenant.email}</div>
            <div className="text-[10px] text-zinc-600 truncate max-w-[200px] font-mono">
              {tenant.tenant_id}
            </div>
          </div>
        </div>
      </td>
      <td className="px-4 py-3">
        <span className={`inline-block px-2 py-0.5 rounded-md text-[10px] font-black uppercase tracking-widest border ${planColor}`}>
          {tenant.plan_label}
        </span>
        {tenant.plan_source !== 'free' && tenant.plan_source !== 'stripe' && (
          <div className="text-[9px] text-zinc-600 mt-0.5">{tenant.plan_source}</div>
        )}
      </td>
      <td className="px-4 py-3 text-zinc-400 font-mono">
        {tenant.plan_price_brl > 0 ? `R$${tenant.plan_price_brl}` : '—'}
      </td>
      <td className="px-4 py-3 text-zinc-400 text-xs">{formatDate(tenant.signup_at)}</td>
      <td className="px-4 py-3 text-zinc-400 text-xs">{formatRelative(tenant.last_login_at)}</td>
      <td className="px-4 py-3 text-zinc-300 font-mono">{tenant.leads_30d}</td>
      <td className="px-4 py-3 text-zinc-300 font-mono">{tenant.msgs_30d}</td>
      <td className="px-4 py-3">
        <StatusBadge tenant={tenant} />
      </td>
      <td className="px-4 py-3">
        <Link
          to={`/admin/tenants/${tenant.tenant_id}`}
          className="opacity-0 group-hover:opacity-100 inline-flex items-center gap-1 text-zinc-500 hover:text-white transition-all"
        >
          <ChevronRight className="w-4 h-4" />
        </Link>
      </td>
    </tr>
  );
}

function StatusBadge({ tenant }: { tenant: AdminTenantRow }) {
  if (tenant.is_deleted) {
    return (
      <span className="inline-flex items-center gap-1 text-[10px] text-red-500 font-black">
        <Trash2 className="w-3 h-3" /> deletado
      </span>
    );
  }
  if (tenant.is_suspended) {
    return (
      <span className="inline-flex items-center gap-1 text-[10px] text-amber-500 font-black" title={tenant.suspension_reason || ''}>
        <Pause className="w-3 h-3" /> suspenso
      </span>
    );
  }
  if (!tenant.is_verified) {
    return (
      <span className="inline-flex items-center gap-1 text-[10px] text-zinc-500 font-bold">
        <Mail className="w-3 h-3" /> não verificado
      </span>
    );
  }
  if (tenant.trial_ends_at && new Date(tenant.trial_ends_at) > new Date()) {
    return (
      <span className="inline-flex items-center gap-1 text-[10px] text-blue-400 font-bold">
        <AlertCircle className="w-3 h-3" /> trial
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1 text-[10px] text-emerald-500 font-bold">
      <CheckCircle2 className="w-3 h-3" /> ativo
    </span>
  );
}

function SkeletonRows({ count }: { count: number }) {
  return (
    <>
      {Array.from({ length: count }).map((_, i) => (
        <tr key={i} className="border-b border-zinc-900/50 animate-pulse">
          {Array.from({ length: 9 }).map((__, j) => (
            <td key={j} className="px-4 py-3">
              <div className="h-3 bg-zinc-800 rounded w-3/4" />
            </td>
          ))}
        </tr>
      ))}
    </>
  );
}
