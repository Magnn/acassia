/**
 * components/inbox/TypingIndicator.tsx — "Lead está digitando..."
 *
 * Animação de 3 pontos pulsantes no estilo Chatwoot/iMessage.
 */

export default function TypingIndicator({ name }: { name?: string }) {
  return (
    <div className="flex items-center gap-3 px-5 py-3 animate-fade-in">
      <div className="flex items-center gap-1.5 bg-bg-surface border border-border rounded-[28px] rounded-tl-sm px-5 py-3 shadow-sm">
        <div className="flex items-center gap-1">
          <span
            className="w-2 h-2 rounded-full bg-accent-amethyst/60 animate-bounce"
            style={{ animationDelay: '0ms', animationDuration: '1s' }}
          />
          <span
            className="w-2 h-2 rounded-full bg-accent-amethyst/60 animate-bounce"
            style={{ animationDelay: '150ms', animationDuration: '1s' }}
          />
          <span
            className="w-2 h-2 rounded-full bg-accent-amethyst/60 animate-bounce"
            style={{ animationDelay: '300ms', animationDuration: '1s' }}
          />
        </div>
        {name && (
          <span className="text-[10px] text-secondary font-bold ml-2">
            {name} está digitando…
          </span>
        )}
      </div>
    </div>
  );
}
