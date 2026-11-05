// @vitest-environment happy-dom
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { followFootnotes, snapFootnotes, watchFootnotes } from '../../../lib/widgets/footnotes.ts'

const PAGE = `
  <p>
    <span class="footnote-run">
      <sup class="footnote-ref" id="marker">
        <a id="press" href="#footnote-mnih2015"><span class="footnote-tile"></span></a>
        <a class="footnote-anchor" id="footnote-ref-mnih2015"></a>
      </sup>
    </span>
    <a id="other" href="#elsewhere">Other</a>
    <a id="gone" class="footnote-backref" href="#nothing"></a>
  </p>
  <section class="footnotes footnote-snap">
    <li class="footnote-item" id="footnote-mnih2015">
      <a id="back" class="footnote-backref" href="#footnote-ref-mnih2015"><svg></svg></a>
      <a id="back-two" class="footnote-backref" href="#footnote-ref-mnih2015:1"></a>
    </li>
  </section>
`

/**
 * Presses the link holding `id` in the page.
 */
function press(id: string) {
  document.querySelector<HTMLElement>(`#${id}`)!.click()
}

/**
 * Gives every element `selector` matches a box standing at `left` and `top`.
 */
function boxAt(selector: string, left: number, top: number) {
  for (const element of document.querySelectorAll(selector)) {
    vi.spyOn(element, 'getBoundingClientRect').mockReturnValue({ left, top, width: 10 } as DOMRect)
  }
}

beforeEach(() => {
  document.body.innerHTML = PAGE
  for (const element of document.querySelectorAll('[href]')) element.addEventListener('click', event => event.preventDefault())
})

describe('followFootnotes', () => {
  it('marks the entry landed on, the marker left, and the way back to that marker', () => {
    followFootnotes(document)
    press('press')

    expect(document.querySelector('#footnote-mnih2015')!.classList).toContain('footnote-hit')
    expect(document.querySelector('#marker')!.classList).toContain('footnote-left')
    expect(document.querySelector('#back')!.getAttribute('aria-current')).toBe('location')
    expect(document.querySelector('#back-two')!.hasAttribute('aria-current')).toBe(false)
    expect(document.querySelector('#footnote-mnih2015')!.getAttribute('tabindex')).toBe('-1')
    expect(document.activeElement).toBe(document.querySelector('#footnote-mnih2015'))
  })

  it('marks the marker landed on and the entry left on the way back, clearing the jump before it', () => {
    followFootnotes(document)
    press('press')
    press('back')

    expect(document.querySelector('#marker')!.classList).toContain('footnote-hit')
    expect(document.querySelector('#marker')!.classList).not.toContain('footnote-left')
    expect(document.querySelector('#footnote-mnih2015')!.classList).toContain('footnote-left')
    expect(document.querySelector('#footnote-mnih2015')!.classList).not.toContain('footnote-hit')
    expect(document.querySelector('[aria-current]')).toBeNull()
    expect(document.activeElement).toBe(document.querySelector('#press'))
  })

  it.each([
    ['a link outside the footnotes', 'other'],
    ['a way back to no marker', 'gone']
  ])('leaves the marks alone on %s', (_, id) => {
    followFootnotes(document)
    press('press')
    press(id)

    expect(document.querySelector('#footnote-mnih2015')!.classList).toContain('footnote-hit')
  })
})

describe('snapFootnotes', () => {
  it('moves each piece by the part of a device pixel its art stands off one', () => {
    boxAt('.footnote-snap', 10.25, 20.5)
    boxAt('.footnote-tile', 3.25, 4.75)
    boxAt('.footnote-backref svg', 5.5, 6)

    snapFootnotes(document)

    const list = document.querySelector<HTMLElement>('.footnote-snap')!
    const run  = document.querySelector<HTMLElement>('.footnote-run')!
    const back = document.querySelector<HTMLElement>('#back')!

    expect([list.style.left, list.style.top]).toEqual(['-0.25px', '0.5px'])
    expect([run.style.left, run.style.top]).toEqual(['-0.25px', '0.25px'])
    expect([back.style.left, back.style.top]).toEqual(['0.5px', '0px'])
  })

  it('adds a move to the offset the piece already holds', () => {
    boxAt('.footnote-tile', 3.25, 4)
    document.querySelector<HTMLElement>('.footnote-run')!.style.left = '1px'

    snapFootnotes(document)

    expect(document.querySelector<HTMLElement>('.footnote-run')!.style.left).toBe('0.75px')
  })

  it('leaves a piece with no box or no art where it stands', () => {
    snapFootnotes(document)

    expect(document.querySelector<HTMLElement>('.footnote-run')!.style.left).toBe('')
    expect(document.querySelector<HTMLElement>('#back-two')!.style.left).toBe('')
  })
})

describe('snapFootnotes across the page', () => {
  it('reads a device pixel ratio of 1 where the window reports none', () => {
    vi.spyOn(window, 'devicePixelRatio', 'get').mockReturnValue(0)
    boxAt('.footnote-tile', 3.25, 4)

    snapFootnotes(document)

    expect(document.querySelector<HTMLElement>('.footnote-run')!.style.left).toBe('-0.25px')
  })

  it('moves a piece to a whole device pixel at the ratio the window reports', () => {
    vi.spyOn(window, 'devicePixelRatio', 'get').mockReturnValue(2)
    boxAt('.footnote-tile', 3.25, 4)

    snapFootnotes(document)

    expect(document.querySelector<HTMLElement>('.footnote-run')!.style.left).toBe('0.25px')
  })

  it('moves the list before a way back it holds, which moves with it', () => {
    const list = document.querySelector<HTMLElement>('.footnote-snap')!
    const back = document.querySelector<HTMLElement>('#back')!

    boxAt('.footnote-snap', 10.25, 0)
    vi.spyOn(back.querySelector('svg')!, 'getBoundingClientRect').mockImplementation(
      () => ({ left: 5.25 + Number(list.style.left.slice(0, -2)), top: 0, width: 10 }) as DOMRect
    )

    snapFootnotes(document)

    expect(list.style.left).toBe('-0.25px')
    expect(back.style.left).toBe('0px')
  })
})

describe('watchFootnotes', () => {
  it.each(['a change of the layout', 'a font arriving', 'a change of device pixel ratio'])('snaps on %s', name => {
    const view  = document.defaultView!
    const fonts = new EventTarget()
    const fired = new Map<string, () => void>([['a font arriving', () => fonts.dispatchEvent(new Event('loadingdone'))]])

    vi.spyOn(view, 'ResizeObserver').mockImplementation(function observer(callback) {
      fired.set('a change of the layout', () => callback([], {} as ResizeObserver))
      return { observe: vi.fn<() => void>() } as unknown as ResizeObserver
    })
    vi.spyOn(view, 'matchMedia').mockReturnValue({
      addEventListener: (_: string, listener: () => void) => fired.set('a change of device pixel ratio', listener)
    } as unknown as MediaQueryList)
    Object.defineProperty(document, 'fonts', { configurable: true, value: fonts })

    watchFootnotes({ onAfterRouteChange: undefined }, document)
    boxAt('.footnote-tile', 3.25, 4)
    fired.get(name)!()
    Reflect.deleteProperty(document, 'fonts')

    expect(document.querySelector<HTMLElement>('.footnote-run')!.style.left).toBe('-0.25px')
  })

  it('snaps on each route, keeping the hook the router already runs', async () => {
    const after  = vi.fn<(to: string) => void>()
    const router = { onAfterRouteChange: after as ((to: string) => void) | undefined }

    watchFootnotes(router, document)
    boxAt('.footnote-tile', 3.25, 4)
    await router.onAfterRouteChange!('/next')

    expect(after).toHaveBeenCalledWith('/next')
    expect(document.querySelector<HTMLElement>('.footnote-run')!.style.left).toBe('-0.25px')
  })

  it('follows a jump and snaps on a route with no earlier hook', async () => {
    const router = { onAfterRouteChange: undefined as ((to: string) => void) | undefined }

    watchFootnotes(router, document)
    press('press')
    await router.onAfterRouteChange!('/next')

    expect(document.querySelector('#footnote-mnih2015')!.classList).toContain('footnote-hit')
  })
})
