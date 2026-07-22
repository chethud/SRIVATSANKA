import {
  createContext,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react';

type PageSearchConfig = {
  placeholder: string;
  value: string;
  onChange: (value: string) => void;
};

type PageSearchContextValue = {
  config: PageSearchConfig | null;
  setConfig: (config: PageSearchConfig | null) => void;
};

const PageSearchContext = createContext<PageSearchContextValue | null>(null);

export function PageSearchProvider({ children }: { children: ReactNode }) {
  const [config, setConfig] = useState<PageSearchConfig | null>(null);
  const value = useMemo(() => ({ config, setConfig }), [config]);
  return <PageSearchContext.Provider value={value}>{children}</PageSearchContext.Provider>;
}

export function usePageSearchSlot() {
  const ctx = useContext(PageSearchContext);
  if (!ctx) throw new Error('usePageSearchSlot must be used within PageSearchProvider');
  return ctx;
}

/** Register this page’s search field into the top bar. */
export function usePageSearch(placeholder: string, value: string, onChange: (value: string) => void) {
  const { setConfig } = usePageSearchSlot();

  useEffect(() => {
    setConfig({ placeholder, value, onChange });
  }, [placeholder, value, onChange, setConfig]);

  useEffect(() => () => setConfig(null), [setConfig]);
}
