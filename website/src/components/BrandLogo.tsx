type BrandLogoProps = {
  variant?: 'sidebar' | 'card' | 'compact';
  className?: string;
};

export function BrandLogo({ variant = 'sidebar', className = '' }: BrandLogoProps) {
  const imgClass =
    variant === 'sidebar'
      ? 'w-full h-auto object-contain block'
      : variant === 'card'
        ? 'w-full max-w-[220px] h-auto object-contain mx-auto block'
        : 'w-full max-w-[160px] h-auto object-contain mx-auto block';

  const panelClass =
    variant === 'sidebar'
      ? 'rounded-xl p-2.5 w-full'
      : variant === 'card'
        ? 'rounded-xl p-4 max-w-[240px] mx-auto'
        : 'rounded-lg p-3 max-w-[180px] mx-auto';

  return (
    <div
      className={`${panelClass} bg-[var(--logo-panel-bg)] border border-[var(--logo-panel-border)] ${className}`}
      style={{ boxShadow: 'var(--logo-panel-shadow)' }}
    >
      <img
        src="/logo.png?v=2"
        alt="SRIVATSANKA — Pure Veg Catering Services for all Occasions"
        className={imgClass}
        width={240}
        height={150}
        decoding="async"
      />
    </div>
  );
}
