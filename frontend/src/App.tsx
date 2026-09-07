import { lazy, Suspense } from 'react';
import { Navigate, Route, Routes } from 'react-router-dom';
import ErrorBoundary from './components/ErrorBoundary';
import Layout from './components/Layout';
import Toaster from './components/Toaster';
import ImpersonateBanner from './components/ImpersonateBanner';
import CookieBanner from './components/CookieBanner';
import QuotaWarningBanner from './components/QuotaWarningBanner';
import { useCmdK } from './hooks/useCmdK';

// Shell components — lazy (não bloqueiam o first paint)
const AdminLayout = lazy(() => import('./components/AdminLayout'));
const SettingsLayout = lazy(() => import('./components/SettingsLayout'));
const CommandPalette = lazy(() => import('./components/CommandPalette'));
const OnboardingTour = lazy(() => import('./components/OnboardingTour'));
const OnboardingChecklist = lazy(() => import('./components/OnboardingChecklist'));
const BlueprintsList = lazy(() => import('./routes/BlueprintsList'));

// Telas SaaS — lazy.
const Dashboard = lazy(() => import('./routes/Dashboard'));
const Workspaces = lazy(() => import('./routes/Workspaces'));
const Catalog = lazy(() => import('./routes/Catalog'));
const Leads = lazy(() => import('./routes/Leads'));
const Builder = lazy(() => import('./routes/Builder'));
const Runs = lazy(() => import('./routes/Runs'));
const Funnel = lazy(() => import('./routes/Funnel'));
const Recovery = lazy(() => import('./routes/Recovery'));
const Templates = lazy(() => import('./routes/Templates'));
const Tarot = lazy(() => import('./routes/Tarot'));
const Pix = lazy(() => import('./routes/Pix'));
const Voice = lazy(() => import('./routes/Voice'));
const Coach = lazy(() => import('./routes/Coach'));
const Affiliate = lazy(() => import('./routes/Affiliate'));
const Lunar = lazy(() => import('./routes/Lunar'));
const Marketplace = lazy(() => import('./routes/Marketplace'));
const Horoscope = lazy(() => import('./routes/Horoscope'));
const Spiritual = lazy(() => import('./routes/Spiritual'));
const CalendarRoute = lazy(() => import('./routes/Calendar'));
const AudioLibraryRoute = lazy(() => import('./routes/AudioLibrary'));
const TenantConfig = lazy(() => import('./routes/TenantConfig'));
const Integrations = lazy(() => import('./routes/Integrations'));
const AgentStudio = lazy(() => import('./routes/AgentStudio'));
const Onboarding = lazy(() => import('./routes/Onboarding'));
const Billing = lazy(() => import('./routes/Billing'));
const BillingUsage = lazy(() => import('./routes/BillingUsage'));
const BillingCancel = lazy(() => import('./routes/BillingCancel'));

// Novas telas — Sprint Completo
const Scheduling = lazy(() => import('./routes/Scheduling'));
const ProfilePage = lazy(() => import('./routes/Profile'));
const Events = lazy(() => import('./routes/Events'));
const ContentPage = lazy(() => import('./routes/Content'));
const Broadcast = lazy(() => import('./routes/Broadcast'));
const SubscriptionsPage = lazy(() => import('./routes/Subscriptions'));
const JournalPage = lazy(() => import('./routes/Journal'));
const TrailsPage = lazy(() => import('./routes/Trails'));
const RitualsPage = lazy(() => import('./routes/Rituals'));
const DreamsPage = lazy(() => import('./routes/Dreams'));
const VisionBoardPage = lazy(() => import('./routes/VisionBoard'));
const CommunityPage = lazy(() => import('./routes/Community'));
const UnifiedReadingPage = lazy(() => import('./routes/UnifiedReading'));
const SocialContentPage = lazy(() => import('./routes/SocialContent'));
const PricingPage = lazy(() => import('./routes/Pricing'));
const ClientProgressPage = lazy(() => import('./routes/ClientProgress'));
const LandingPageRoute = lazy(() => import('./routes/LandingPage'));
const LaunchManagerPage = lazy(() => import('./routes/LaunchManager'));
const PipelinePage = lazy(() => import('./routes/Pipeline'));
const CheckoutWebhooksPage = lazy(() => import('./routes/CheckoutWebhooks'));
const WAGroupsPage = lazy(() => import('./routes/WAGroups'));
const WAConnectionPage = lazy(() => import('./routes/WAConnection'));
const DepartmentsPage = lazy(() => import('./routes/Departments'));
const ServiceRatingsPage = lazy(() => import('./routes/ServiceRatings'));
const SmartLinksPage = lazy(() => import('./routes/SmartLinks'));
const FiscalPage = lazy(() => import('./routes/Fiscal'));
// Portal do Consumidor (B2C)
const PortalLayout = lazy(() => import('./routes/portal/PortalLayout'));
const PortalExplore = lazy(() => import('./routes/portal/PortalExplore'));
const PortalVault = lazy(() => import('./routes/portal/PortalVault'));
const PortalSchedule = lazy(() => import('./routes/portal/PortalSchedule'));
const PortalRituals = lazy(() => import('./routes/portal/PortalRituals'));
const PortalDreams = lazy(() => import('./routes/portal/PortalDreams'));
const PortalCommunity = lazy(() => import('./routes/portal/PortalCommunity'));
const PortalJournal = lazy(() => import('./routes/portal/PortalJournal'));
const PortalOnboarding = lazy(() => import('./routes/portal/PortalOnboarding'));

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
        Carregando Meu Mistério Studio…
      </div>
    </div>
  );
}

function AppShell() {
  const { open: cmdkOpen, setOpen: setCmdkOpen } = useCmdK();
  return (
    <Suspense fallback={null}>
      <CommandPalette open={cmdkOpen} onClose={() => setCmdkOpen(false)} />
      <OnboardingTour />
    </Suspense>
  );
}

export default function App() {
  return (
    <ErrorBoundary>
      <ImpersonateBanner />
      <QuotaWarningBanner />
      <CookieBanner />
      {/* <OnboardingChecklist /> */}
      <AppShell />
      <Suspense fallback={<PageFallback />}>
        <Routes>
          <Route path="/onboarding" element={<Onboarding />} />
          <Route path="/workspaces" element={<Workspaces />} />
          <Route element={<Layout />}>
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/catalog" element={<Catalog />} />
            <Route path="/leads" element={<Leads />} />
            <Route path="/inbox" element={<Navigate to="/leads" replace />} />
            <Route path="/contacts" element={<Navigate to="/leads" replace />} />
            <Route path="/blueprints" element={<BlueprintsList />} />
            <Route path="/billing" element={<Billing />} />
            <Route path="/billing/usage" element={<BillingUsage />} />
            <Route path="/billing/cancel-subscription" element={<BillingCancel />} />
            <Route path="/agents" element={<AgentStudio />} />
            <Route path="/runs" element={<Runs />} />
            <Route path="/analytics/funnel" element={<Funnel />} />
            <Route path="/analytics/recovery" element={<Recovery />} />
            <Route path="/templates" element={<Templates />} />
            <Route path="/tarot" element={<Tarot />} />
            <Route path="/pix" element={<Pix />} />
            <Route path="/voice" element={<Voice />} />
            <Route path="/coach" element={<Coach />} />
            <Route path="/affiliate" element={<Affiliate />} />
            <Route path="/lunar" element={<Lunar />} />
            <Route path="/marketplace" element={<Marketplace />} />
            <Route path="/horoscope" element={<Horoscope />} />
            <Route path="/spiritual" element={<Spiritual />} />
            <Route path="/calendar" element={<CalendarRoute />} />
            <Route path="/audio-library" element={<AudioLibraryRoute />} />
            <Route path="/integrations" element={<Integrations />} />
            <Route path="/tenant-config" element={<TenantConfig />} />

            {/* Novas telas — Sprint Completo */}
            <Route path="/scheduling" element={<Scheduling />} />
            <Route path="/profile" element={<ProfilePage />} />
            <Route path="/events" element={<Events />} />
            <Route path="/content" element={<ContentPage />} />
            <Route path="/broadcast" element={<Broadcast />} />
            <Route path="/subscriptions" element={<SubscriptionsPage />} />
            <Route path="/journal" element={<JournalPage />} />
            <Route path="/trails" element={<TrailsPage />} />
            <Route path="/rituals" element={<RitualsPage />} />
            <Route path="/dreams" element={<DreamsPage />} />
            <Route path="/vision-board" element={<VisionBoardPage />} />
            <Route path="/community" element={<CommunityPage />} />
            <Route path="/reading" element={<UnifiedReadingPage />} />
            <Route path="/social-content" element={<SocialContentPage />} />
            <Route path="/client-progress/:leadId" element={<ClientProgressPage />} />
            <Route path="/launches" element={<LaunchManagerPage />} />
            <Route path="/pipeline" element={<PipelinePage />} />
            <Route path="/checkout-webhooks" element={<CheckoutWebhooksPage />} />
            <Route path="/wa-groups" element={<WAGroupsPage />} />
            <Route path="/wa-connection" element={<WAConnectionPage />} />
            <Route path="/departments" element={<DepartmentsPage />} />
            <Route path="/service-ratings" element={<ServiceRatingsPage />} />
            <Route path="/smart-links" element={<SmartLinksPage />} />
            <Route path="/fiscal" element={<FiscalPage />} />

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
          {/* Builder movido para DENTRO do Layout */}
          <Route element={<Layout />}>
            <Route path="/flows/:id" element={<Builder />} />
          </Route>

          {/* Admin God-Mode (Frente 1) — tema escuro/sóbrio distinto */}
          <Route path="/admin/setup-2fa" element={<AdminSetup2FA />} />
          <Route path="/admin/recover" element={<AdminRecover />} />
          <Route path="/admin" element={<AdminLayout />}>
            <Route index element={<Navigate to="/admin/tenants" replace />} />
            <Route path="tenants" element={<AdminTenants />} />
            <Route path="tenants/:tenantId" element={<AdminTenantDetail />} />
            <Route path="metrics" element={<AdminMetrics />} />
          </Route>

          {/* Portal B2C (Consumidor Final) */}
          <Route path="/portal/welcome" element={<PortalOnboarding />} />
          <Route path="/pricing" element={<PricingPage />} />
          <Route path="/home" element={<LandingPageRoute />} />
          <Route path="/portal" element={<PortalLayout />}>
            <Route index element={<Navigate to="/portal/explore" replace />} />
            <Route path="explore" element={<PortalExplore />} />
            <Route path="vault" element={<PortalVault />} />
            <Route path="schedule" element={<PortalSchedule />} />
            <Route path="rituals" element={<PortalRituals />} />
            <Route path="dreams" element={<PortalDreams />} />
            <Route path="community" element={<PortalCommunity />} />
            <Route path="journal" element={<PortalJournal />} />
          </Route>

          {/* Fallback 404 redireciona pro dashboard */}
          <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Routes>
      </Suspense>
      <Toaster />
    </ErrorBoundary>
  );
}
