import { Component, type ReactNode } from 'react';
import { AlertTriangle, RefreshCw } from 'lucide-react';
import { track } from '../lib/analytics';

interface Props {
  children: ReactNode;
}

interface State {
  error: Error | null;
}

export default class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(error: Error, info: { componentStack?: string }) {
    // Log local + telemetria (fire-and-forget). Não enviamos stack pra
    // backend pra evitar PII; só nome+mensagem+componentStack truncado.
    // eslint-disable-next-line no-console
    console.error('[ErrorBoundary]', error, info.componentStack);
    try {
      track('feature_used', {
        kind: 'react_error_boundary',
        name: error.name,
        message: error.message?.slice(0, 200),
        stack: (info.componentStack || '').slice(0, 500),
      });
    } catch {
      // ignora — telemetria nunca quebra a tela de erro
    }
  }

  handleReload = () => {
    window.location.reload();
  };

  handleReset = () => {
    this.setState({ error: null });
  };

  render() {
    if (!this.state.error) return this.props.children;

    return (
      <div className="min-h-screen bg-bg-primary text-primary flex items-center justify-center p-8">
        <div className="max-w-lg w-full bg-bg-surface border border-border rounded-[40px] p-12 text-center space-y-8 shadow-xl">
          <div className="w-20 h-20 mx-auto rounded-3xl bg-red-500/10 border border-red-500/20 flex items-center justify-center">
            <AlertTriangle className="w-10 h-10 text-red-500" strokeWidth={2} />
          </div>
          <div className="space-y-3">
            <h1 className="text-2xl font-black tracking-tight">Algo deu errado</h1>
            <p className="text-sm text-secondary font-medium">
              A interface encontrou um erro inesperado. Recarregue a página
              para continuar — se o problema persistir, conte pra gente.
            </p>
          </div>
          <details className="text-left bg-bg-primary border border-border rounded-2xl p-4 text-[11px] font-mono text-secondary">
            <summary className="cursor-pointer font-black uppercase tracking-widest text-[10px] text-secondary/60">
              Detalhes técnicos
            </summary>
            <pre className="mt-3 whitespace-pre-wrap break-words text-[11px] leading-relaxed">
              {this.state.error.name}: {this.state.error.message}
            </pre>
          </details>
          <div className="flex items-center justify-center gap-3">
            <button
              onClick={this.handleReload}
              className="flex items-center gap-2 px-5 py-3 bg-accent-amethyst text-white rounded-2xl text-xs font-black uppercase tracking-widest shadow-lg shadow-accent-amethyst/20 hover:scale-[1.02] transition-all"
            >
              <RefreshCw className="w-4 h-4" />
              Recarregar página
            </button>
            <button
              onClick={this.handleReset}
              className="px-5 py-3 bg-bg-primary border border-border rounded-2xl text-xs font-black uppercase tracking-widest text-secondary hover:text-primary hover:border-accent-amethyst/30 transition-all"
            >
              Tentar de novo
            </button>
          </div>
        </div>
      </div>
    );
  }
}
