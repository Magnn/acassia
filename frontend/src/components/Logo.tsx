interface Props {
  size?: number;
  className?: string;
  /** Sólido (padrão), só contorno (outline), ou monograma sem ornamentos. */
  variant?: 'default' | 'outline' | 'minimal';
}

/**
 * Sibila — marca visual.
 *
 * Composição: lua crescente partida por um eixo vertical (axis mundi)
 * + ponto astral no canto superior direito. Single-color (currentColor)
 * pra herdar de qualquer contexto.
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
      aria-label="Sibila"
    >
      {/* Lua crescente — half-arc fechado */}
      <path
        d="M12 3 A9 9 0 0 1 12 21"
        strokeWidth="1.6"
        fill="currentColor"
        fillOpacity={variant === 'outline' ? 0 : 0.1}
      />
      {/* Eixo vertical — divide a lua */}
      <line x1="12" y1="3" x2="12" y2="21" strokeWidth="1.6" />
      {/* Ponto astral (omitido em minimal) */}
      {variant !== 'minimal' && (
        <circle cx="20" cy="5" r="1.4" fill="currentColor" stroke="none" />
      )}
    </svg>
  );
}

/**
 * Wordmark "Sibila" em Fraunces — combina com Logo em horizontal.
 */
export function Wordmark({
  className = '',
}: {
  className?: string;
}) {
  return (
    <span
      className={`font-display font-medium tracking-wide ${className}`}
      style={{ letterSpacing: '0.02em' }}
    >
      Sibila
    </span>
  );
}
