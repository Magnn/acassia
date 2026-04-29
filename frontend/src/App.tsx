import { lazy, Suspense } from 'react';
import { Navigate, Route, Routes } from 'react-router-dom';
import Layout from './components/Layout';
import Toaster from './components/Toaster';
import BlueprintsList from './routes/BlueprintsList';

// Telas SaaS — lazy pra que cada uma vire chunk separado.
// O bundle inicial fica fino; recharts (Dashboard) e React Flow (Builder)
// só carregam quando o usuário navega pra elas.
const Dashboard = lazy(() => import('./routes/Dashboard'));
const Inbox = lazy(() => import('./routes/Inbox'));
const Contacts = lazy(() => import('./routes/Contacts'));
const Settings = lazy(() => import('./routes/Settings'));
const Builder = lazy(() => import('./routes/Builder'));
const Runs = lazy(() => import('./routes/Runs'));
const TenantConfig = lazy(() => import('./routes/TenantConfig'));
const Integrations = lazy(() => import('./routes/Integrations'));
const AgentStudio = lazy(() => import('./routes/AgentStudio'));
const WhatsAppConnect = lazy(() => import('./routes/WhatsAppConnect'));

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
            <Route path="/whatsapp" element={<WhatsAppConnect />} />
            <Route path="/integrations" element={<Integrations />} />
            <Route path="/tenant-config" element={<TenantConfig />} />
            <Route path="/settings" element={<Settings />} />
          </Route>
          <Route path="/flows/:id" element={<Builder />} />
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
        </Routes>
      </Suspense>
      <Toaster />
    </>
  );
}
