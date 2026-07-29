import { createContext, useContext, useEffect, useState, type ReactNode } from 'react';

type Theme = 'light' | 'dark';

/** Root rem scale — most of the UI uses rem/Tailwind, so this scales the site. */
export type FontScale = 'sm' | 'md' | 'lg' | 'xl';

export const FONT_SCALE_OPTIONS: { id: FontScale; label: string; px: number }[] = [
  { id: 'sm', label: 'Small', px: 16 },
  { id: 'md', label: 'Default', px: 18 },
  { id: 'lg', label: 'Large', px: 20 },
  { id: 'xl', label: 'Extra large', px: 22 },
];

interface ThemeContextValue {
  theme: Theme;
  toggleTheme: () => void;
  fontScale: FontScale;
  setFontScale: (scale: FontScale) => void;
}

const ThemeContext = createContext<ThemeContextValue | null>(null);

function readFontScale(): FontScale {
  try {
    const saved = localStorage.getItem('srivatsanka-font-scale');
    if (saved === 'sm' || saved === 'md' || saved === 'lg' || saved === 'xl') return saved;
  } catch {
    /* ignore storage read failures */
  }
  return 'md';
}

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [theme, setTheme] = useState<Theme>(() => {
    try {
      const saved = localStorage.getItem('srivatsanka-theme') as Theme | null;
      if (saved === 'light' || saved === 'dark') return saved;
    } catch {
      /* ignore storage read failures */
    }
    return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  });
  const [fontScale, setFontScaleState] = useState<FontScale>(readFontScale);

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
    try {
      localStorage.setItem('srivatsanka-theme', theme);
    } catch {
      /* ignore storage write failures */
    }
  }, [theme]);

  useEffect(() => {
    const px = FONT_SCALE_OPTIONS.find((o) => o.id === fontScale)?.px ?? 18;
    document.documentElement.style.fontSize = `${px}px`;
    document.documentElement.setAttribute('data-font-scale', fontScale);
    try {
      localStorage.setItem('srivatsanka-font-scale', fontScale);
    } catch {
      /* ignore storage write failures */
    }
  }, [fontScale]);

  const toggleTheme = () => setTheme((t) => (t === 'light' ? 'dark' : 'light'));
  const setFontScale = (scale: FontScale) => setFontScaleState(scale);

  return (
    <ThemeContext.Provider value={{ theme, toggleTheme, fontScale, setFontScale }}>
      {children}
    </ThemeContext.Provider>
  );
}

export function useTheme() {
  const ctx = useContext(ThemeContext);
  if (!ctx) throw new Error('useTheme must be used within ThemeProvider');
  return ctx;
}
