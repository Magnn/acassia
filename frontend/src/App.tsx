import { lazy, Suspense } from 'react';
import { Navigate, Route, Routes } from 'react-router-dom';
import ErrorBoundary from './components/ErrorBoundary';
import Layout from './components/Layout';
import AdminLayout from './components/AdminLayout';
import SettingsLayout from './components/SettingsLayout';
import Toaster from './components/Toaster';
import ImpersonateBanner from './components/ImpersonateBanner';
import CookieBanner from './components/CookieBanner';
import BlueprintsList from './routes/BlueprintsList';

// Telas SaaS — lazy.
const Dashboard = lazy(() => import('./routes/Dashboard'));
const Leads = lazy(() => import('./routes/Leads'));
const Builder = lazy(() => import('./routes/Builder'));
const Runs = lazy(() => import('./routes/Runs'));
const TenantConfig = lazy(() => import('./routes/TenantConfig'));
const Integrations = lazy(() => import('./routes/Integrations'));
const AgentStudio = lazy(() => import('./routes/AgentStudio'));
const Onboarding = lazy(() => import('./routes/Onboarding'));
const Billing = lazy(() => import('./routes/Billing'));
const BillingUsage = lazy(() => import('./routes/BillingUsage'));

// Settings sub-rotas
const SettingsDevices = lazy(() => import('./routes/settings/Devices'));
const SettingsRecovery = lazy(() => import('./routes/settings/Recovery'));
const SettingsSecurity = lazy(() => import('./routes/settings/Security'));
const SettingsPrivacy = lazy(() => import('./routes/settings/Privacy'));
const SettingsPlaceholder = lazy(() => import('./routes/settings/Placeholder'));

// Admin God-Mode (Frente 1)
const AdminTenants = lazy(() => import('./routes/admin/Tenants'));
const AdminTenantDetail = lazy(() => import('./routes/admin/TenantDetail'));
const AdminMetrics = lazy(() => import('./routes/admin/Metrics'));
const AdminSetup2FA = lazy(() => import('./routes/admin/Setup2FA'));
const AdminRecover = lazy(() => import('./routes/admin/Recover'));

function PageFallback() {
  return (
    <div className="flex flex-col items-center justify-center min-h-[400px] gap-4">
      <div className="w-12 h-12 border-4 border-accent-amethyst/20 border-t-accent-amethyst rounded-full animate-spin" />
      <div className="text-secondary text-[11px] font-black uppercase tracking-[0.2em] animate-pulse">
        Carregando Acássia Studio…
      </div>
    </div>
  );
}

export default function App() {
  return (
    <ErrorBoundary>
      <ImpersonateBanner />
      <CookieBanner />
      <Suspense fallback={<PageFallback />}>
        <Routes>
          <Route path="/onboarding" element={<Onboarding />} />
          <Route element={<Layout />}>
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/leads" element={<Leads />} />
            <Route path="/inbox" element={<Navigate to="/leads" replace />} />
            <Route path="/contacts" element={<Navigate to="/leads" replace />} />
            <Route path="/blueprints" element={<BlueprintsList />} />
            <Route path="/billing" element={<Billing />} />
            <Route path="/billing/usage" element={<BillingUsage />} />
            <Route path="/agents" element={<AgentStudio />} />
            <Route path="/runs" element={<Runs />} />
            <Route path="/integrations" element={<Integrations />} />
            <Route path="/tenant-config" element={<TenantConfig />} />

            {/* Configurações com submenu lateral próprio */}
            <Route path="/settings" element={<SettingsLayout />}>
              <Route index element={<Navigate to="/settings/devices" replace />} />
              <Route path="devices" element={<SettingsDevices />} />
              <Route path="recovery" element={<SettingsRecovery />} />
              <Route path="security" element={<SettingsSecurity />} />
              <Route path="privacy" element={<SettingsPrivacy />} />
              <Route
                path="account"
                element={
                  <SettingsPlaceholder
                    title="Minha Conta"
                    description="Email, senha, nome do tenant. Em breve."
                  />
                }
              />
              <Route
                path="labels"
                element={
                  <SettingsPlaceholder
                    title="Etiquetas"
                    description="Crie etiquetas para classificar conversas e leads."
                  />
                }
              />
              <Route
                path="fields"
                element={
                  <SettingsPlaceholder
                    title="Campos personalizados"
                    description="Defina campos extras para os contatos do seu tenant."
                  />
                }
              />
              <Route
                path="timezone"
                element={
                  <SettingsPlaceholder
                    title="Fuso horário"
                    description="Configure o fuso horário do workspace para horários de envio."
                  />
                }
              />
              <Route
                path="quick-replies"
                element={
                  <SettingsPlaceholder
                    title="Respostas rápidas"
                    description="Atalhos de mensagens para o atendimento humano."
                  />
                }
              />
              <Route
                path="templates"
                element={
                  <SettingsPlaceholder
                    title="Templates WhatsApp"
                    description="Modelos aprovados pela Meta para mensagens transacionais e de marketing."
                  />
                }
              />
              <Route
                path="logs"
                element={
                  <SettingsPlaceholder
                    title="Logs do sistema"
                    description="Auditoria de eventos por tenant. Use Execuções para logs de fluxos."
                  />
                }
              />
            </Route>
          </Route>
          <Route path="/flows/:id" element={<Builder />} />

          {/* Admin God-Mode (Frente 1) — tema escuro/sóbrio distinto */}
          <Route path="/admin/setup-2fa" element={<AdminSetup2FA />} />
          <Route path="/admin/recover" element={<AdminRecover />} />
          <Route path="/admin" element={<AdminLayout />}>
            <Route index element={<Navigate to="/admin/tenants" replace />} />
            <Route path="tenants" element={<AdminTenants />} />
            <Route path="tenants/:tenantId" element={<AdminTenantDetail />} />
            <Route path="metrics" element={<AdminMetrics />} />
          </Route>

          <Route path="/" element={<Navigate to="/dashboard" replace />} />
        </Routes>
      </Suspense>
      <Toaster />
    </ErrorBoundary>
  );
}
