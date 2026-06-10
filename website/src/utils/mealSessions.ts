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

export function isMenuSessionCategory(category: string): boolean {
  return !PREFERENCE_CATEGORIES.has(category);
}
