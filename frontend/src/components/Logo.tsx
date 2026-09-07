interface Props {
  size?: number;
  className?: string;
  /** Sólido (padrão), só contorno (outline), ou monograma sem ornamentos. */
  variant?: 'default' | 'outline' | 'minimal';
}

/**
 * Meu Mistério — marca visual.
 *
 * Composição: lua crescente partida por um eixo vertical (axis mundi)
 * + ponto astral no canto superior direito. Single-color (currentColor)
 * pra herdar de qualquer contexto.
 *
 * Tokens internos da paleta usam prefix `sibila-*` — nomenclatura interna.
 */
export default function Logo({
  size = 24,
  className = '',
  variant = 'default',
}: Props) {
  return (
    <svg
      viewBox="0 0 24 24"
      width={size}
      height={size}
      fill="none"
      stroke="currentColor"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      aria-label="Meu Mistério"
    >
      {/* Lua crescente — design mais refinado */}
      <path
        d="M12 2 A10 10 0 0 1 12 22"
        strokeWidth="2"
        fill="currentColor"
        fillOpacity={variant === 'outline' ? 0 : 0.15}
      />
      {/* Eixo vertical */}
      <line x1="12" y1="2" x2="12" y2="22" strokeWidth="2" />
      {/* Ponto astral */}
      {variant !== 'minimal' && (
        <circle cx="19" cy="6" r="1.5" fill="var(--accent-amethyst)" stroke="none" />
      )}
    </svg>
  );
}

/**
 * Wordmark "Meu Mistério" — Marca principal do sistema.
 */
export function Wordmark({
  className = '',
}: {
  className?: string;
}) {
  return (
    <span
      className={`font-black tracking-tight ${className}`}
      style={{ letterSpacing: '-0.02em' }}
    >
      Meu Mistério
    </span>
  );
}
