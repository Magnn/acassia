import { Flame, Snowflake, Sun } from 'lucide-react';

interface ScoreBadgeProps {
  band?: 'hot' | 'warm' | 'cold' | string;
  value?: number;
  size?: 'sm' | 'md';
  showValue?: boolean;
}

const BAND_CONFIG: Record<string, { label: string; color: string; bg: string; Icon: typeof Flame }> = {
  hot: {
    label: 'Hot',
    color: 'text-red-500',
    bg: 'bg-red-500/10 border-red-500/30',
    Icon: Flame,
  },
  warm: {
    label: 'Warm',
    color: 'text-amber-500',
    bg: 'bg-amber-500/10 border-amber-500/30',
    Icon: Sun,
  },
  cold: {
    label: 'Cold',
    color: 'text-blue-400',
    bg: 'bg-blue-500/10 border-blue-500/30',
    Icon: Snowflake,
  },
};

export default function ScoreBadge({
  band = 'cold',
  value,
  size = 'sm',
  showValue = false,
}: ScoreBadgeProps) {
  const cfg = BAND_CONFIG[band] || BAND_CONFIG.cold;
  const Icon = cfg.Icon;
  const sizeClasses = size === 'md'
    ? 'px-2 py-1 text-xs'
    : 'px-1.5 py-0.5 text-[10px]';

  return (
    <span
      className={`inline-flex items-center gap-1 rounded-md border font-black uppercase tracking-widest ${cfg.bg} ${cfg.color} ${sizeClasses}`}
      title={value !== undefined ? `Score: ${value}/100` : `Banda: ${cfg.label}`}
    >
      <Icon className={size === 'md' ? 'w-3.5 h-3.5' : 'w-3 h-3'} />
      {showValue && value !== undefined ? value : cfg.label}
    </span>
  );
}
