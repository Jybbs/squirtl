// @vitest-environment happy-dom
import { enableAutoUnmount, mount }        from '@vue/test-utils'
import { afterEach, describe, expect, it } from 'vitest'
import { markRaw }                          from 'vue'

import { RoomImages }  from '../../../../../lib/game/images.ts'
import { pressName }   from '../../../../../lib/game/pad.ts'
import { SEARCH }      from '../../../../../lib/methods/search.ts'
import * as moments    from '../../../../../lib/methods/search/moments.ts'
import { fixed }       from '../../../../../lib/widgets/numbers.ts'
import { SearchGroup } from '../../../../../theme/components/methods/search/group.tsx'
import { drawInto }    from '../../../../common/canvas.ts'

enableAutoUnmount(afterEach)

/**
 * The first iteration in which a rollout sets a flag.
 */
const AT = SEARCH.iterations.findIndex(({ groups }) =>
  groups.some(({ copies }) => copies.some(copy => copy.term !== null)))
/**
 * Each group of that iteration once every rollout has ended, beside its
 * number.
 */
const GROUPS = moments.shownOf(AT, moments.ENDED).map((copies, g) => ({ copies, n: g + 1 }))

describe('SearchGroup', () => {
  it.each(GROUPS)(
    'shows group $n’s best reward and each copy’s button, uncertainty, dimming, and badge',
    ({ copies, n }) => {
      drawInto(null)
      const images  = markRaw(new RoomImages(() => new Image()))
      const wrapper = mount(SearchGroup, { props: { copies, images, n } })

      expect([wrapper.get('div').text(), wrapper.findAll('.search-copy').map(copy => [
        copy.get('canvas').classes().includes('opacity-30'),
        copy.findAll('.top-1.right-1').length,
        copy.text()
      ])]).toStrictEqual([
        `Group ${n}Reward${fixed(Math.max(...copies.map(each => each.total)), 4)}`,
        copies.map(each => [
          each.state === 'dead',
          Number(each.term !== null),
          `${pressName(each.copy.held)}${fixed(each.uncertainty!, 2)}`
        ])
      ])
    }
  )
})
