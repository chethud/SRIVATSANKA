import { Link } from 'react-router-dom';
import { useLayout } from '../context/LayoutContext';

type BrandLogoProps = {
  variant?: 'sidebar' | 'card' | 'compact' | 'horizontal';
  className?: string;
};

/** Sidebar-only: needs LayoutProvider (dashboard shell). */
function SidebarBrandLogo({ className = '' }: { className?: string }) {
  const { sidebarCollapsed } = useLayout();

  return (
    <Link
      to="/"
      className={`flex items-center justify-center w-full h-[72px] min-h-[72px] max-h-[72px] ${className}`}
      title="SRIVATSANKA EVENTS — Dashboard"
      aria-label="Go to dashboard"
    >
      <div className={`flex items-center gap-2.5 w-full min-w-0 ${sidebarCollapsed ? 'justify-center' : 'px-1'}`}>
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
          <span className="min-w-0 flex-1 text-[11px] font-bold tracking-[0.05em] text-[var(--primary)] leading-[1.15]">
            <span className="block">SRIVATSANKA</span>
            <span className="block tracking-[0.12em]">EVENTS</span>
          </span>
        )}
      </div>
    </Link>
  );
}

export function BrandLogo({ variant = 'sidebar', className = '' }: BrandLogoProps) {
  if (variant === 'sidebar') {
    return <SidebarBrandLogo className={className} />;
  }

  const src =
    variant === 'compact'
      ? '/brand/logo-icon.svg?v=4'
      : '/brand/logo-horizontal.svg?v=4';

  return (
    <div className={`flex items-center justify-center ${className}`}>
      <img
        src={src}
        alt="SRIVATSANKA EVENTS"
        className={variant === 'compact' ? 'w-12 h-12' : 'w-full max-w-[280px] h-auto object-contain'}
        decoding="async"
        draggable={false}
      />
    </div>
  );
}
