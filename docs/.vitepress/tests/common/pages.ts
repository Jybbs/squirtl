/**
 * The text of each page under `docs/pages/`, keyed by its path there, each page
 * imported through `?raw` into the module graph of every test file importing
 * this one.
 */
export const PAGES: Readonly<Record<string, string>> = Object.fromEntries(
  Object.entries(import.meta.glob<string>('./**/*.md', {
    base   : '../../../pages',
    eager  : true,
    import : 'default',
    query  : '?raw'
  })).map(([file, text]) => [file.slice('./'.length), text])
)
