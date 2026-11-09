import { type Theme, inBrowser } from 'vitepress'
import DefaultTheme              from 'vitepress/theme-without-fonts'

import './styles/site.css'
import './styles/roles.css'
import './styles/kit/chip.css'
import './styles/kit/clock.css'
import './styles/kit/focus.css'
import './styles/kit/footnotes.css'
import './styles/kit/key.css'
import './styles/front/story.css'
import './styles/front/hero.css'
import './styles/front/reward.css'
import './styles/front/sees.css'
import './styles/commands/watch.css'
import './styles/methods/curriculum.css'
import './styles/methods/experience.css'
import './styles/methods/memory.css'
import './styles/methods/reach.css'
import './styles/methods/step.css'
import './styles/section/ribbon.css'

import { titleNotFound }  from '../lib/missing/page.ts'
import { watchFootnotes } from '../lib/widgets/footnotes.ts'
import { COMPONENTS }     from './components/widgets.ts'
import { Layout }         from './layout.ts'

export default {
  Layout  : Layout,
  extends : DefaultTheme,

  enhanceApp: ({ app, router, siteData }) => {
    for (const widget of COMPONENTS) {
      app.component(widget.name!, widget)
    }
    titleNotFound(router, () => siteData.value.description)
    if (inBrowser) watchFootnotes(router, document)
  }
} satisfies Theme
