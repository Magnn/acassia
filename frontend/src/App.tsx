import { Link, Route, Routes } from 'react-router-dom';
import BlueprintsList from './routes/BlueprintsList';

export default function App() {
  return (
    <div className="min-h-full flex flex-col">
      <header className="border-b border-cigana-border bg-cigana-surface px-6 py-3 flex items-center gap-4">
        <Link to="/" className="font-semibold text-cigana-purple">
          Cigana · Flow Builder
        </Link>
        <span className="text-xs text-slate-400">Fase 0 — andaime</span>
      </header>
      <main className="flex-1">
        <Routes>
          <Route path="/" element={<BlueprintsList />} />
        </Routes>
      </main>
    </div>
  );
}
