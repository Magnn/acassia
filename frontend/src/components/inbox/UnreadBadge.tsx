/**
 * components/inbox/UnreadBadge.tsx — Badge de mensagens não lidas
 *
 * Pill compacta com animação de entrada.
 */

export default function UnreadBadge({ count }: { count: number }) {
  if (count <= 0) return null;

  return (
    <span className="inline-flex items-center justify-center min-w-[18px] h-[18px] px-1 rounded-full bg-accent-amethyst text-white text-[9px] font-black tabular-nums animate-scale-in shadow-lg shadow-accent-amethyst/30">
      {count > 99 ? '99+' : count}
    </span>
  );
}
