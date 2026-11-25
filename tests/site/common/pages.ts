/**
 * The text of each page under `docs/pages/`, keyed by its path there, each page
 * imported through `?raw`, so a change to a page selects every test file that
 * imports this one under Node's environment and none under `happy-dom`, where
 * Vite rewrites the import to `.md?import&raw` and Vitest's `--changed` reads
 * no such import.
 */
export const PAGES: Readonly<Record<string, string>> = Object.fromEntries(
  Object.entries(import.meta.glob<string>('./**/*.md', {
    base   : '../../../docs/pages',
    eager  : true,
    import : 'default',
    query  : '?raw'
  })).map(([file, text]) => [file.slice('./'.length), text])
)
