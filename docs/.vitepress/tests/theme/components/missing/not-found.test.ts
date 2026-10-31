// @vitest-environment happy-dom
import { type VueWrapper, enableAutoUnmount, flushPromises, mount } from '@vue/test-utils'
import { afterEach, describe, expect, it, vi }                      from 'vitest'
import { nextTick }                                                 from 'vue'

import { frameFor }           from '../../../../lib/game/actors.ts'
import { paintSprite }        from '../../../../lib/game/screen.ts'
import { NOT_FOUND }          from '../../../../lib/missing/page.ts'
import { stopsOf }            from '../../../../lib/missing/stops.ts'
import * as browser           from '../../../common/browser.ts'
import { Recorder, drawInto } from '../../../common/canvas.ts'
import { METHODS }            from '../../../common/sections.ts'

/**
 * The version and the host the site's theme configuration names.
 */
const EDITION = { host: 'squirtl.fyi', version: '0.2.0' }

vi.mock('vitepress', () => ({
  useData  : () => ({ theme: { value: { edition: EDITION } } }),
  useRoute : () => ({ path: '/methods/agnet/' }),
  withBase : (path: string) => `/squirtl${path}`
}))
vi.mock('../../../../lib/missing/stops.ts', async original => {
  const stops = await original<typeof import('../../../../lib/missing/stops.ts')>()
  return { ...stops, stopsOf: () => stops.stopsOf([METHODS]) }
})

const { NotFound } = await import('../../../../theme/components/missing/not-found.tsx')

enableAutoUnmount(afterEach)

/**
 * Mounts the page with every canvas drawing into `recorder`, and lets Pallet
 * Town's image load.
 */
async function mounted(recorder: Recorder | null = new Recorder()): Promise<VueWrapper> {
  browser.stubSight()
  drawInto(recorder)
  const wrapper = mount(NotFound, { attachTo: document.body })
  await flushPromises()
  return wrapper
}

/**
 * Reads the rectangles Blue's sprite fills standing on his square facing down.
 */
function standing(): Recorder['marks'] {
  const recorder = new Recorder()
  paintSprite(recorder, frameFor('player', 'down'), 64, 60)
  return recorder.marks
}

describe('NotFound', () => {
  it('names the page, says what happened, and gives the address asked for', async () => {
    const wrapper = await mounted()

    expect([wrapper.get('h1').text(), wrapper.findAll('p')[0]!.text(), wrapper.get('code').text()])
      .toStrictEqual([NOT_FOUND.title, NOT_FOUND.lead, 'squirtl.fyi/methods/agnet/'])
  })

  it('publishes its title, its line, its cards, and its drawing’s label in the project’s prose', async () => {
    const wrapper = await mounted()
    const label   = wrapper.get('canvas').attributes('aria-label')!

    for (const text of [wrapper.text(), label]) expect(text).toBePublishedProse()
  })

  it('leads back to the front page and to each section through its card, in its hue', async () => {
    const cards = (await mounted()).findAll('li')
    const ways  = cards.map(card => [
      card.get('a').attributes('href'),
      card.get('a .font-display').text(),
      card.get(':scope > span').text(),
      card.classes().at(-1)
    ])

    expect(ways).toStrictEqual([
      ['/squirtl/', 'The front page', stopsOf()[0]!.note, 'text-link'],
      ['/squirtl/methods/', 'Methods', 'What the agent learns, and how.', 'text-indigo-text']
    ])
    expect(cards[0]!.get('a > span').html()).toContain('viewBox="0 0 1200 630"')
    expect(cards[1]!.get('.rounded-full').classes()).toContain('bg-indigo-1')
  })
})

describe('NotFound drawing', () => {
  it('stands Blue still on his square facing down in the Glitch City under reduced motion', async () => {
    browser.preference.value = 'reduce'
    const recorder           = new Recorder()
    await mounted(recorder)

    expect([recorder.views.length > 0, recorder.marks.slice(-standing().length)])
      .toStrictEqual([true, standing()])
  })

  it('sets the warp back to Blue standing once motion stops partway through a spin', async () => {
    vi.useFakeTimers({ toFake: ['requestAnimationFrame', 'performance'] })
    const recorder = drawInto(new Recorder())
    const sight    = browser.stubSight()
    mount(NotFound, { attachTo: document.body })
    await flushPromises()

    sight.show(true)
    vi.advanceTimersByTime(2800)
    const spinning           = recorder.marks.slice(-standing().length)
    browser.preference.value = 'reduce'
    await nextTick()

    expect([spinning, recorder.marks.slice(-standing().length)])
      .toStrictEqual([expect.not.arrayContaining(standing()), standing()])
  })

  it('keeps the page whole where the document gives its canvas no context', async () => {
    const wrapper = await mounted(null)

    expect([wrapper.get('h1').text(), wrapper.findAll('li').length]).toStrictEqual([NOT_FOUND.title, 2])
  })

  it('leaves the drawing blank where Pallet Town’s image fails to decode', async () => {
    vi.spyOn(HTMLImageElement.prototype, 'decode').mockRejectedValue(new Error('undecodable'))
    const recorder = new Recorder()
    await mounted(recorder)

    expect(recorder.views).toStrictEqual([])
  })
})
