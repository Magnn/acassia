import { lazy, Suspense } from 'react';
import { Navigate, Route, Routes } from 'react-router-dom';
import Layout from './components/Layout';
import SettingsLayout from './components/SettingsLayout';
import Toaster from './components/Toaster';
import BlueprintsList from './routes/BlueprintsList';

// Telas SaaS — lazy.
const Dashboard = lazy(() => import('./routes/Dashboard'));
const Inbox = lazy(() => import('./routes/Inbox'));
const Contacts = lazy(() => import('./routes/Contacts'));
const Builder = lazy(() => import('./routes/Builder'));
const Runs = lazy(() => import('./routes/Runs'));
const TenantConfig = lazy(() => import('./routes/TenantConfig'));
const Integrations = lazy(() => import('./routes/Integrations'));
const AgentStudio = lazy(() => import('./routes/AgentStudio'));

// Settings sub-rotas
const SettingsDevices = lazy(() => import('./routes/settings/Devices'));
const SettingsRecovery = lazy(() => import('./routes/settings/Recovery'));
const SettingsPlaceholder = lazy(() => import('./routes/settings/Placeholder'));

function PageFallback() {
  return (
    <div className="p-8 text-sibila-fog text-sm animate-pulse">Carregando…</div>
  );
}

export default function App() {
  return (
    <>
      <Suspense fallback={<PageFallback />}>
        <Routes>
          <Route element={<Layout />}>
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/inbox" element={<Inbox />} />
            <Route path="/contacts" element={<Contacts />} />
            <Route path="/blueprints" element={<BlueprintsList />} />
            <Route path="/agents" element={<AgentStudio />} />
            <Route path="/runs" element={<Runs />} />
            <Route path="/integrations" element={<Integrations />} />
            <Route path="/tenant-config" element={<TenantConfig />} />

            {/* Configurações com submenu lateral próprio */}
            <Route path="/settings" element={<SettingsLayout />}>
              <Route index element={<Navigate to="/settings/devices" replace />} />
              <Route path="devices" element={<SettingsDevices />} />
              <Route path="recovery" element={<SettingsRecovery />} />
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
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
        </Routes>
      </Suspense>
      <Toaster />
    </>
  );
}
