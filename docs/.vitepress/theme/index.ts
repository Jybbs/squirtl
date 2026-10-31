import type { Theme } from 'vitepress'
import DefaultTheme   from 'vitepress/theme-without-fonts'

import './styles/site.css'
import './styles/roles.css'
import './styles/kit/chip.css'
import './styles/kit/clock.css'
import './styles/kit/focus.css'
import './styles/kit/key.css'
import './styles/front/story.css'
import './styles/front/hero.css'
import './styles/front/reward.css'
import './styles/front/sees.css'
import './styles/section/ribbon.css'

import { titleNotFound } from '../lib/missing/page.ts'
import { StoryLearning } from './components/front/learning.tsx'
import { StoryRace }     from './components/front/race.tsx'
import { StoryReward }   from './components/front/reward.tsx'
import { StorySees }     from './components/front/sees.tsx'
import { Layout }        from './layout.ts'

export default {
  Layout  : Layout,
  extends : DefaultTheme,

  enhanceApp: ({ app, router, siteData }) => {
    for (const widget of [StoryLearning, StoryRace, StoryReward, StorySees]) {
      app.component(widget.name!, widget)
    }
    titleNotFound(router, () => siteData.value.description)
  }
} satisfies Theme
