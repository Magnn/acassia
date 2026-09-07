import { Construction } from 'lucide-react';

interface Props {
  title: string;
  description: string;
}

export default function Placeholder({ title, description }: Props) {
  return (
    <div className="px-8 py-12 max-w-3xl mx-auto">
      <div className="bg-sibila-obsidian border border-sibila-mist rounded-xl p-10 text-center">
        <Construction className="w-10 h-10 mx-auto text-sibila-amethyst opacity-50 mb-4" strokeWidth={1.5} />
        <h2 className="font-display text-xl text-sibila-moonlight mb-2">{title}</h2>
        <p className="text-sm text-sibila-smoke max-w-md mx-auto">{description}</p>
      </div>
    </div>
  );
}
