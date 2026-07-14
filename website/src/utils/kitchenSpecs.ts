/**
 * Labels highlighted in red on kitchen copies (Muralidharan reference).
 * Dish names with "(No Onion Garlic)" stay normal black — only true specs / ritual titles go red.
 */
export function isKitchenSpecification(text: string): boolean {
  const t = text.trim();
  if (!t) return false;
  if (/^(note\s*:)/i.test(t)) return true;
  if (/^garlands?\b/i.test(t)) return true;
  if (/^(seer\s*bhakash|bhakashan|kasi\s*yatra|varapujai|varapuja|arpanam)\b/i.test(t)) return true;
  if (/\bbride allergy\b/i.test(t)) return true;
  if (/^check with\b/i.test(t)) return true;
  if (t.length <= 90 && /^all items\b/i.test(t)) return true;
  return false;
}

/** Dietary / allergy lines shown as a red kitchen banner (skip schedule noise). */
export function kitchenSpecificationNotes(dietary: string[]): string[] {
  const notes: string[] = [];
  for (const item of dietary) {
    const t = item.trim();
    if (!t) continue;
    if (/callback|occasion date|scheduled|requested:/i.test(t)) continue;
    if (t.length > 200) continue;
    notes.push(t);
  }
  return notes;
}
