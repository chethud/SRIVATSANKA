import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react';
import {
  brandLogoSrc,
  fetchBrandInfo,
  uploadBrandLogo as uploadBrandLogoApi,
  type BrandInfo,
} from '../api/client';

const DEFAULT_ICON = '/brand/logo-icon.svg?v=4';
const DEFAULT_HORIZONTAL = '/brand/logo-horizontal.svg?v=4';

type BrandContextValue = {
  customLogo: boolean;
  updatedAt: string | null;
  iconSrc: string;
  horizontalSrc: string;
  refreshBrand: () => Promise<void>;
  uploadBrandLogo: (file: File) => Promise<void>;
};

const BrandContext = createContext<BrandContextValue | null>(null);

export function BrandProvider({ children }: { children: ReactNode }) {
  const [info, setInfo] = useState<BrandInfo>({ customLogo: false, updatedAt: null });

  const refreshBrand = useCallback(async () => {
    try {
      setInfo(await fetchBrandInfo());
    } catch {
      setInfo({ customLogo: false, updatedAt: null });
    }
  }, []);

  useEffect(() => {
    void refreshBrand();
  }, [refreshBrand]);

  const uploadBrandLogo = useCallback(async (file: File) => {
    const next = await uploadBrandLogoApi(file);
    setInfo(next);
  }, []);

  const value = useMemo<BrandContextValue>(() => {
    const customSrc = info.customLogo ? brandLogoSrc(info.updatedAt) : null;
    return {
      customLogo: info.customLogo,
      updatedAt: info.updatedAt,
      iconSrc: customSrc ?? DEFAULT_ICON,
      horizontalSrc: customSrc ?? DEFAULT_HORIZONTAL,
      refreshBrand,
      uploadBrandLogo,
    };
  }, [info, refreshBrand, uploadBrandLogo]);

  return <BrandContext.Provider value={value}>{children}</BrandContext.Provider>;
}

export function useBrand() {
  const ctx = useContext(BrandContext);
  if (!ctx) throw new Error('useBrand must be used within BrandProvider');
  return ctx;
}
