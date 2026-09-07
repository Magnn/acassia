interface Props {
  size?: number;
  className?: string;
  variant?: 'default' | 'outline' | 'minimal';
}

/**
 * Acássia — marca visual.
 * Símbolo moderno de nós de automação e inteligência artificial conectada.
 */
export default function Logo({
  size = 24,
  className = '',
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
      aria-label="Acássia"
    >
      <path
        d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"
        strokeWidth="2"
        className="stroke-purple-500"
      />
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
      Acássia
    </span>
  );
}
