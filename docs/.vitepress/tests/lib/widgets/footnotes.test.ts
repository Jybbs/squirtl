// @vitest-environment happy-dom
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { followFootnotes, snapFootnotes, watchFootnotes } from '../../../lib/widgets/footnotes.ts'

const PAGE = `
  <p>
    <span class="footnote-run">
      <sup class="footnote-ref" id="marker">
        <a id="footnote-ref-mnih2015" href="#footnote-mnih2015"><span class="footnote-tile"></span></a>
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
    press('footnote-ref-mnih2015')

    expect(document.querySelector('#footnote-mnih2015')!.classList).toContain('footnote-hit')
    expect(document.querySelector('#marker')!.classList).toContain('footnote-left')
    expect(document.querySelector('#back')!.getAttribute('aria-current')).toBe('location')
    expect(document.querySelector('#back-two')!.hasAttribute('aria-current')).toBe(false)
    expect(document.querySelector('#footnote-mnih2015')!.hasAttribute('tabindex')).toBe(false)
  })

  it('marks the marker landed on and the entry left on the way back, clearing the jump before it', () => {
    followFootnotes(document)
    press('footnote-ref-mnih2015')
    press('back')

    expect(document.querySelector('#marker')!.classList).toContain('footnote-hit')
    expect(document.querySelector('#marker')!.classList).not.toContain('footnote-left')
    expect(document.querySelector('#footnote-mnih2015')!.classList).toContain('footnote-left')
    expect(document.querySelector('#footnote-mnih2015')!.classList).not.toContain('footnote-hit')
    expect(document.querySelector('[aria-current]')).toBeNull()
  })

  it.each([
    ['a link outside the footnotes', 'other'],
    ['a way back to no marker', 'gone']
  ])('leaves the marks alone on %s', (_, id) => {
    followFootnotes(document)
    press('footnote-ref-mnih2015')
    press(id)

    expect(document.querySelector('#footnote-mnih2015')!.classList).toContain('footnote-hit')
  })
})

describe('followFootnotes through a repeated marker and an encoded label', () => {
  it('marks the way back to a repeated marker rather than the first', () => {
    const marker = document.querySelector<HTMLElement>('.footnote-ref a')!

    marker.id = 'footnote-ref-mnih2015:1'
    followFootnotes(document)
    marker.click()

    expect(document.querySelector('#back')!.hasAttribute('aria-current')).toBe(false)
    expect(document.querySelector('#back-two')!.getAttribute('aria-current')).toBe('location')
  })

  it('finds a repeated marker from its way back, whose id holds a colon', () => {
    const marker = document.querySelector<HTMLElement>('.footnote-ref a')!

    marker.id = 'footnote-ref-mnih2015:1'
    followFootnotes(document)
    press('back-two')

    expect(document.querySelector('#marker')!.classList).toContain('footnote-hit')
  })

  it('decodes the address of a label outside ASCII', () => {
    document.body.innerHTML = '<sup class="footnote-ref"><a href="#footnote-m%C3%BCller" id="footnote-ref-a"></a></sup><ol><li id="footnote-müller"></li></ol>'
    document.querySelector('a')!.addEventListener('click', event => event.preventDefault())
    followFootnotes(document)
    document.querySelector('a')!.click()

    expect(document.querySelector('li')!.classList).toContain('footnote-hit')
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
    document.querySelector<HTMLElement>('.footnote-run')!.style.top = '1px'

    snapFootnotes(document)

    expect(document.querySelector<HTMLElement>('.footnote-run')!.style.left).toBe('0.75px')
    expect(document.querySelector<HTMLElement>('.footnote-run')!.style.top).toBe('1px')
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
    press('footnote-ref-mnih2015')
    await router.onAfterRouteChange!('/next')

    expect(document.querySelector('#footnote-mnih2015')!.classList).toContain('footnote-hit')
  })
})

describe('watchFootnotes across changes of the ratio', () => {
  it('watches the ratio it reaches after a change of device pixel ratio', () => {
    const view      = document.defaultView!
    const listeners: (() => void)[] = []

    vi.spyOn(view, 'ResizeObserver').mockImplementation(function observer() {
      return { observe: vi.fn<() => void>() } as unknown as ResizeObserver
    })
    const media = vi.spyOn(view, 'matchMedia').mockImplementation(() => ({
      addEventListener: (_: string, listener: () => void) => listeners.push(listener)
    }) as unknown as MediaQueryList)

    watchFootnotes({ onAfterRouteChange: undefined }, document)
    listeners[0]!()

    expect(media).toHaveBeenCalledTimes(2)
    expect(listeners).toHaveLength(2)
  })

  it('listens to each ratio once', () => {
    const view = document.defaultView!
    const options: unknown[] = []

    vi.spyOn(view, 'ResizeObserver').mockImplementation(function observer() {
      return { observe: vi.fn<() => void>() } as unknown as ResizeObserver
    })
    vi.spyOn(view, 'matchMedia').mockReturnValue({
      addEventListener: (_: string, __: () => void, option: unknown) => options.push(option)
    } as unknown as MediaQueryList)

    watchFootnotes({ onAfterRouteChange: undefined }, document)

    expect(options).toStrictEqual([{ once: true }])
  })
})
