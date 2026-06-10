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
