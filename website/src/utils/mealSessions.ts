export const MEAL_SESSIONS = [
  { id: 'Breakfast', label: 'Breakfast' },
  { id: 'Lunch', label: 'Lunch' },
  { id: 'Dinner', label: 'Dinner' },
  { id: 'Reception Dinner', label: 'Reception Dinner' },
  { id: 'Snacks', label: 'Snacks' },
  { id: 'Coffee', label: 'Coffee' },
  { id: 'Tea', label: 'Tea' },
  { id: 'Juice', label: 'Juice' },
  { id: 'Dessert', label: 'Dessert' },
] as const;

export type MealSessionId = (typeof MEAL_SESSIONS)[number]['id'];

export const MEAL_SESSION_ORDER: string[] = [
  ...MEAL_SESSIONS.map((s) => s.id),
  'Meal Preference',
  'Cuisine Preference',
];

export const PREFERENCE_CATEGORIES = new Set(['Meal Preference', 'Cuisine Preference']);

/** Default service windows per meal session (matches typical wedding menus). */
export const DEFAULT_MEAL_TIMES: Record<string, { timeFrom: string; timeTo: string }> = {
  Breakfast: { timeFrom: '08:00', timeTo: '11:00' },
  Lunch: { timeFrom: '12:00', timeTo: '15:00' },
  Dinner: { timeFrom: '19:00', timeTo: '22:00' },
  'Reception Dinner': { timeFrom: '19:00', timeTo: '23:00' },
  Snacks: { timeFrom: '16:30', timeTo: '18:00' },
  Coffee: { timeFrom: '06:00', timeTo: '11:00' },
  Tea: { timeFrom: '15:00', timeTo: '18:00' },
  Juice: { timeFrom: '10:00', timeTo: '17:00' },
  Dessert: { timeFrom: '20:00', timeTo: '22:00' },
};

export function allMealSessionIds(): string[] {
  return MEAL_SESSIONS.map((s) => s.id);
}

export function isMenuSessionCategory(category: string): boolean {
  return !PREFERENCE_CATEGORIES.has(category);
}

export function isPresetMealSession(id: string): boolean {
  return MEAL_SESSIONS.some((s) => s.id === id);
}

/** Preset sessions + custom ones (order notes / catalog). */
export function resolveSessionTabs(
  customSessions: string[] | null | undefined,
  extraCategories: string[] = [],
): { id: string; label: string }[] {
  const seen = new Set<string>();
  const tabs: { id: string; label: string }[] = [];

  for (const s of MEAL_SESSIONS) {
    seen.add(s.id.toLowerCase());
    tabs.push({ id: s.id, label: s.label });
  }

  const addCustom = (raw: string) => {
    const name = raw.trim();
    if (!name || PREFERENCE_CATEGORIES.has(name)) return;
    const key = name.toLowerCase();
    if (seen.has(key)) return;
    seen.add(key);
    tabs.push({ id: name, label: name });
  };

  for (const s of customSessions ?? []) addCustom(s);
  for (const c of extraCategories) addCustom(c);

  return tabs;
}
