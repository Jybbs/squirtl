import vueJsx           from '@vitejs/plugin-vue-jsx'
import { defineConfig } from 'vitest/config'

import { projectFacts } from './lib/config/manifest.ts'
import { cacheDir }     from './lib/config/paths.ts'

const { gate } = projectFacts(import.meta.url)

export default defineConfig({
  cacheDir : cacheDir(import.meta.url, 'vitest'),
  plugins  : [vueJsx()],
  test     : {
    expect              : { requireAssertions: true },
    include             : ['.vitepress/tests/**/*.test.ts'],
    pool                : 'threads',
    resolveSnapshotPath : (testPath, extension) => testPath + extension,
    restoreMocks        : true,
    sequence            : { shuffle: true },
    unstubEnvs          : true,
    unstubGlobals       : true,

    coverage: {
      exclude          : ['**/*.data.ts'],
      include          : ['.vitepress/lib/**/*.ts', '.vitepress/theme/**/*.{ts,tsx}'],
      provider         : 'v8',
      reportOnFailure  : true,
      reportsDirectory : cacheDir(import.meta.url, 'coverage/site'),
      thresholds       : { branches: gate, functions: gate, lines: gate, statements: gate }
    },

    reporters: process.env.GITHUB_ACTIONS
             ? ['default', ['github-actions', { jobSummary: { enabled: false } }]]
             : ['default'],

    setupFiles: [
      '.vitepress/tests/common/browser.ts', '.vitepress/tests/common/clock.ts',
      '.vitepress/tests/common/matchers.ts'
    ]
  }
})
