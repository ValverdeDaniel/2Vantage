/*
 * What a TEMPLATE bar saves and applies (plan.md §8.14; J68): a template's config is {path: value}, the deal's own
 * setting paths (the server cleans each with `config.clean`). Pure: the builder payload's resolved settings turned
 * into those paths, and back into one PATCH. A `rows` template's paths are relative to the line it is applied on.
 */

/** Every `output` path of the builder's resolved `output` (the layout template): {'output.layout': …, …}. */
export function layoutConfig(output, prefix = 'output') {
  return Object.entries(output).reduce((paths, [key, value]) => {
    if (value && typeof value === 'object' && !Array.isArray(value)) return { ...paths, ...layoutConfig(value, `${prefix}.${key}`) };
    return { ...paths, [`${prefix}.${key}`]: value ?? null };
  }, {});
}

/** Whether the deal still holds every path of `config` (a built-in template reads as chosen while it does). */
export function matchesConfig(current, config) {
  return Object.entries(config).every(([path, value]) => JSON.stringify(current[path] ?? null) === JSON.stringify(value ?? null));
}

/** A line's rows template: its rows (null = every row with a value) and its card stats (null = the standard set). */
export const rowsConfig = (spec) => ({ rows: spec.rows ?? null, card_stats: spec.card_stats ?? null });

/** A rows template applied on `line`: the line's own paths. */
export const rowsChanges = (line, config) => ({
  [`lines.${line}.rows`]: config.rows ?? null,
  [`lines.${line}.card_stats`]: config.card_stats ?? null,
});

/** The executive summary's template: Show it and the picked figures ([] = the standard set). */
export const summaryConfig = (summary) => ({ 'summary.on': summary.on, 'summary.blocks': summary.picked });
