import path from 'node:path'

import { describe, expect, it } from 'vitest'

import { MARKS }   from '../../../lib/config/marks.ts'
import { docsDir } from '../../../lib/config/paths.ts'

describe('MARKS', () => {
  it.each(Object.entries(MARKS))('holds docs/%s to the drawing it lists', async (file, draw) => {
    await expect(draw()).toMatchFileSnapshot(path.join(docsDir(import.meta.url), file))
  })
})
