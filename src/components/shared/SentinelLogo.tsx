import { cn } from '../../lib/utils';
import markUrl from '../../assets/sentinel-mark.svg';

interface SentinelLogoProps {
  className?: string;
  iconClassName?: string;
  textClassName?: string;
  showWordmark?: boolean;
  size?: 'sm' | 'md' | 'lg';
}

export function SentinelLogo({
  className,
  iconClassName,
  textClassName,
  showWordmark = true,
  size = 'md',
}: SentinelLogoProps) {
  const iconSizeClass = size === 'sm' ? 'w-7 h-7' : size === 'lg' ? 'w-14 h-14' : 'w-9 h-9';

  const titleClass = size === 'lg' ? 'text-4xl' : size === 'sm' ? 'text-lg' : 'text-xl';

  const subtitleClass = size === 'lg' ? 'text-[10px] tracking-[0.3em]' : 'text-[9px] tracking-[0.28em]';

  return (
    <div className={cn('flex items-center gap-3', className)} aria-label="SENTINEL brand logo">
      <img src={markUrl} alt="SENTINEL" className={cn(iconSizeClass, iconClassName)} />

      {showWordmark && (
        <div className={cn('leading-tight', textClassName)}>
          <span className={cn('block font-mono font-bold tracking-[0.2em] text-white', titleClass)}>SENTINEL</span>
          <span className={cn('block font-mono uppercase text-brand-muted', subtitleClass)}>AI + Blockchain Security</span>
        </div>
      )}
    </div>
  );
}