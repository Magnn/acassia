import { Link, Route, Routes } from 'react-router-dom';
import BlueprintsList from './routes/BlueprintsList';
import Builder from './routes/Builder';

export default function App() {
  return (
    <div className="h-full flex flex-col">
      <header className="border-b border-cigana-border bg-cigana-surface px-6 py-3 flex items-center gap-4 flex-shrink-0">
        <Link to="/" className="font-semibold text-cigana-purple">
          Cigana · Flow Builder
        </Link>
        <span className="text-xs text-slate-400">polimento visual — passada 1 (ícones Lucide)</span>
      </header>
      <main className="flex-1 min-h-0">
        <Routes>
          <Route path="/" element={<BlueprintsList />} />
          <Route path="/flows/:id" element={<Builder />} />
        </Routes>
      </main>
    </div>
  );
}
