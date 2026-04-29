import { Navigate, Route, Routes } from 'react-router-dom';
import Layout from './components/Layout';
import Toaster from './components/Toaster';
import Dashboard from './routes/Dashboard';
import Inbox from './routes/Inbox';
import Contacts from './routes/Contacts';
import Settings from './routes/Settings';
import BlueprintsList from './routes/BlueprintsList';
import Builder from './routes/Builder';
import Runs from './routes/Runs';
import TenantConfig from './routes/TenantConfig';
import Integrations from './routes/Integrations';
import AgentStudio from './routes/AgentStudio';

export default function App() {
  return (
    <>
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
          <Route path="/settings" element={<Settings />} />
        </Route>
        <Route path="/flows/:id" element={<Builder />} />
        <Route path="/" element={<Navigate to="/dashboard" replace />} />
      </Routes>
      <Toaster />
    </>
  );
}
