// @vitest-environment happy-dom
import { enableAutoUnmount }                               from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { nextTick, ref }                                   from 'vue'

import { IDENTITY }   from '../../../../lib/identity/identity.ts'
import * as places    from '../../../../lib/identity/places.ts'
import * as browser   from '../../../common/browser.ts'
import { FACTS }      from '../../../common/facts.ts'

/**
 * Whether the page stands in the dark scheme, which a case sets.
 */
const dark = ref(false)

vi.mock('vitepress', () => ({
  useData: () => ({ isDark: dark, theme: ref({ edition: { host: FACTS.host, version: FACTS.version }, project: FACTS }) })
}))

const { IdentityTagline } = await import('../../../../theme/components/identity/tagline.tsx')

enableAutoUnmount(afterEach)

beforeEach(() => {
  dark.value = false
  vi.useFakeTimers()
  return () => vi.useRealTimers()
})

/**
 * Reads the place the folder on top shows.
 */
const top = (wrapper: Awaited<ReturnType<typeof browser.shown>>): string | undefined =>
  wrapper.find('.identity-folder[data-depth="0"]').attributes('aria-label')

describe('IdentityTagline', () => {
  it('opens on GitHub’s repository page, the byline in its About box beside the host and every keyword', async () => {
    const wrapper = await browser.shown(IdentityTagline)
    const github  = wrapper.get('.identity-folder[data-depth="0"]')

    expect([
      top(wrapper),
      github.text().includes(FACTS.description),
      github.findAll('.identity-topic').map(topic => topic.text())
    ]).toStrictEqual([places.PLACES[0]!.name, true, FACTS.keywords])
    expect(wrapper.text()).toBePublishedProse()
  })

  it('draws the README’s tagline and badges and the card’s byline in the folders beneath', async () => {
    const wrapper = await browser.shown(IdentityTagline)

    expect([
      wrapper.text().includes(IDENTITY.tagline),
      wrapper.findAll('.identity-badge').map(badge => badge.attributes('alt')),
      wrapper.findAll('.identity-card-art').length
    ]).toStrictEqual([true, places.badgesOf(FACTS).map(badge => badge.name), 1])
  })

})

describe('IdentityTagline’s folding', () => {
  it('holds the opening place a full beat, then folds to the next and around to the first', async () => {
    const wrapper = await browser.shown(IdentityTagline)
    const seen    = [top(wrapper)]
    const fold    = async () => {
      vi.advanceTimersByTime(places.BEAT)
      await nextTick()
      seen.push(top(wrapper))
    }

    await fold()
    await fold()
    await fold()

    expect(seen).toStrictEqual([...places.PLACES.map(each => each.name), places.PLACES[0]!.name])
  })

  it('shows the place a reader picks by its tab a full beat before folding on', async () => {
    const wrapper = await browser.shown(IdentityTagline)
    vi.advanceTimersByTime(places.BEAT - 1)

    await wrapper.findAll('.identity-folder-tab')[2]!.trigger('click')
    const picked = top(wrapper)
    vi.advanceTimersByTime(places.BEAT)
    await nextTick()

    expect([picked, top(wrapper)]).toStrictEqual([places.PLACES[2]!.name, places.PLACES[2]!.name])
  })

})

describe('IdentityTagline’s holds', () => {
  it('holds the place while a mouse rests on the widget or a tab holds focus, a full beat more once each lets go', async () => {
    const wrapper = await browser.shown(IdentityTagline)
    const root    = wrapper.get('.identity-folders')
    const seen    = []

    await root.trigger('pointerenter', { pointerType: 'mouse' })
    vi.advanceTimersByTime(2 * places.BEAT)
    await root.trigger('pointerleave', { pointerType: 'mouse' })
    await root.trigger('focusin')
    vi.advanceTimersByTime(2 * places.BEAT)
    await root.trigger('focusout')
    vi.advanceTimersByTime(places.BEAT - 1)
    await nextTick()
    seen.push(top(wrapper))
    vi.advanceTimersByTime(1)
    await nextTick()
    seen.push(top(wrapper))

    expect(seen).toStrictEqual([places.PLACES[0]!.name, places.PLACES[1]!.name])
  })

  it('stands on the opening place under reduced motion, a touch on the widget holding nothing', async () => {
    browser.preference.value = 'reduce'
    const wrapper            = await browser.shown(IdentityTagline)
    const root               = wrapper.get('.identity-folders')

    await root.trigger('pointerenter', { pointerType: 'touch' })
    await root.trigger('pointerleave', { pointerType: 'touch' })
    vi.advanceTimersByTime(2 * places.BEAT)
    await nextTick()

    expect(top(wrapper)).toBe(places.PLACES[0]!.name)
  })

  it('draws the README’s logo for the dark ground in the dark scheme, its letters in the light ground’s hex', async () => {
    dark.value    = true
    const wrapper = await browser.shown(IdentityTagline)

    expect(wrapper.get('.identity-readme-mark').html()).toContain(`fill="${IDENTITY.neutrals.ground.hex}"`)
  })
})
