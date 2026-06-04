import { useLayout } from '../context/LayoutContext';

type BrandLogoProps = {
  variant?: 'sidebar' | 'card' | 'compact' | 'horizontal';
  className?: string;
};

export function BrandLogo({ variant = 'sidebar', className = '' }: BrandLogoProps) {
  const { sidebarCollapsed } = useLayout();

  if (variant === 'sidebar') {
    return (
      <div
        className={`flex items-center justify-center w-full h-[72px] min-h-[72px] max-h-[72px] ${className}`}
        title="SRIVATSANKA"
      >
        <div className={`flex items-center gap-2.5 w-full ${sidebarCollapsed ? 'justify-center' : 'px-1'}`}>
          <img
            src="/brand/logo-icon.svg?v=4"
            alt=""
            width={40}
            height={40}
            className="w-10 h-10 shrink-0 object-contain"
            decoding="async"
            draggable={false}
          />
          {!sidebarCollapsed && (
            <span className="text-[13px] font-bold tracking-[0.14em] text-[var(--primary)] leading-tight truncate">
              SRIVATSANKA
            </span>
          )}
        </div>
      </div>
    );
  }

  const src =
    variant === 'compact'
      ? '/brand/logo-icon.svg?v=4'
      : '/brand/logo-horizontal.svg?v=4';

  return (
    <div className={`flex items-center justify-center ${className}`}>
      <img
        src={src}
        alt="SRIVATSANKA"
        className={variant === 'compact' ? 'w-12 h-12' : 'w-full max-w-[280px] h-auto object-contain'}
        decoding="async"
        draggable={false}
      />
    </div>
  );
}
