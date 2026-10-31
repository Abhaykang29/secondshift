/** Tiny plural helper: plural(1, "finding") -> "1 finding";
 * plural(4, "finding") -> "4 findings". Pass an explicit plural
 * for irregular forms: plural(2, "fix", "fixes"). */
export function plural(count: number, singular: string, pluralForm?: string): string {
  return `${count} ${count === 1 ? singular : (pluralForm ?? `${singular}s`)}`;
}
