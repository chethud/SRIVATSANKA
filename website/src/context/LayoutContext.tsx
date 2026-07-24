import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from 'react';

interface LayoutContextValue {
  sidebarCollapsed: boolean;
  toggleSidebar: () => void;
  sidebarWidth: string;
  /** True below the lg breakpoint — sidebar becomes an off-canvas drawer. */
  isMobileNav: boolean;
  mobileNavOpen: boolean;
  openMobileNav: () => void;
  closeMobileNav: () => void;
  toggleMobileNav: () => void;
}

const LayoutContext = createContext<LayoutContextValue | null>(null);

const STORAGE_KEY = 'srivatsanka-sidebar-collapsed';
const MOBILE_MQ = '(max-width: 1023px)';

export const SIDEBAR_EXPANDED = '14rem';
export const SIDEBAR_COLLAPSED = '4.25rem';

function readIsMobileNav(): boolean {
  if (typeof window === 'undefined') return false;
  return window.matchMedia(MOBILE_MQ).matches;
}

export function LayoutProvider({ children }: { children: ReactNode }) {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(() => {
    return localStorage.getItem(STORAGE_KEY) === '1';
  });
  const [isMobileNav, setIsMobileNav] = useState(readIsMobileNav);
  const [mobileNavOpen, setMobileNavOpen] = useState(false);

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, sidebarCollapsed ? '1' : '0');
  }, [sidebarCollapsed]);

  useEffect(() => {
    const mq = window.matchMedia(MOBILE_MQ);
    const onChange = () => {
      const mobile = mq.matches;
      setIsMobileNav(mobile);
      if (!mobile) setMobileNavOpen(false);
    };
    onChange();
    mq.addEventListener('change', onChange);
    return () => mq.removeEventListener('change', onChange);
  }, []);

  useEffect(() => {
    if (!mobileNavOpen) return;
    const { overflow, paddingRight } = document.body.style;
    const gap = window.innerWidth - document.documentElement.clientWidth;
    document.body.style.overflow = 'hidden';
    if (gap > 0) document.body.style.paddingRight = `${gap}px`;
    return () => {
      document.body.style.overflow = overflow;
      document.body.style.paddingRight = paddingRight;
    };
  }, [mobileNavOpen]);

  const openMobileNav = useCallback(() => setMobileNavOpen(true), []);
  const closeMobileNav = useCallback(() => setMobileNavOpen(false), []);
  const toggleMobileNav = useCallback(() => setMobileNavOpen((o) => !o), []);

  const sidebarWidth = isMobileNav ? '0px' : sidebarCollapsed ? SIDEBAR_COLLAPSED : SIDEBAR_EXPANDED;

  return (
    <LayoutContext.Provider
      value={{
        sidebarCollapsed,
        toggleSidebar: () => setSidebarCollapsed((c) => !c),
        sidebarWidth,
        isMobileNav,
        mobileNavOpen,
        openMobileNav,
        closeMobileNav,
        toggleMobileNav,
      }}
    >
      {children}
    </LayoutContext.Provider>
  );
}

export function useLayout() {
  const ctx = useContext(LayoutContext);
  if (!ctx) throw new Error('useLayout must be used within LayoutProvider');
  return ctx;
}
