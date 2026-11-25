import fs                from 'node:fs'
import os                from 'node:os'
import path              from 'node:path'
import { pathToFileURL } from 'node:url'

import { test as base } from 'vitest'

/**
 * A scratch checkout a case writes files into, beside the `import.meta.url` a
 * module under its `docs/.vitepress/` would carry.
 */
export interface Checkout {
  metaUrl : string
  root    : string
}

/**
 * The files a case writes, each under its path from the checkout's root.
 */
type Files = Record<string, string>

/**
 * Extends `test` with a `checkout` fixture, which writes `files` into a fresh
 * folder holding a `.git` folder, so every function under `lib/` that finds the
 * root of its checkout finds that folder, and removes the folder once the case
 * ends.
 */
export const test = base.extend<{ checkout: (files?: Files) => Checkout }>({
  checkout: async ({ onTestFinished }, use) => {
    await use((files = {}) => {
      const scratch = fs.mkdtempDisposableSync(path.join(os.tmpdir(), 'squirtl-15-site-'))
      onTestFinished(() => scratch.remove())
      fs.mkdirSync(path.join(scratch.path, '.git'))
      for (const [name, text] of Object.entries(files)) {
        const file = path.join(scratch.path, name)
        fs.mkdirSync(path.dirname(file), { recursive: true })
        fs.writeFileSync(file, text)
      }
      const config = path.join(scratch.path, 'docs', '.vitepress', 'config.ts')
      return { metaUrl: pathToFileURL(config).href, root: scratch.path }
    })
  }
})
