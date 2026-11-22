import vueJsx                           from '@vitejs/plugin-vue-jsx'
import { configDefaults, defineConfig } from 'vitest/config'

import { projectFacts }                 from '../lib/config/manifest.ts'
import { cacheDir, repoRoot }           from '../lib/config/paths.ts'

const { gate } = projectFacts(import.meta.url)

export default defineConfig({
  cacheDir : cacheDir(import.meta.url, 'vitest'),
  plugins  : [vueJsx()],
  server   : { fs: { allow: [repoRoot(import.meta.url)] } },
  test     : {
    css                 : { include: [/\?raw$/u] },
    dir                 : '../tests/site',
    expect              : { requireAssertions: true },
    include             : ['**/*.test.ts'],
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

    forceRerunTriggers: [
      ...configDefaults.forceRerunTriggers, '**/.vitepress/lib/rendered/theme.css', '**/docs/bun.lock',
      '**/pyproject.toml'
    ],

    reporters: process.env.GITHUB_ACTIONS
             ? ['default', ['github-actions', { jobSummary: { enabled: false } }]]
             : ['default'],

    setupFiles: [
      '../tests/site/common/browser.ts', '../tests/site/common/clock.ts', '../tests/site/common/matchers.ts'
    ]
  }
})
