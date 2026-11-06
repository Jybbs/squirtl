import type { Router } from 'vitepress'

import { nextTick } from 'vue'

/**
 * Reads the pixels an inline `left` or `top` holds, an unset one reading as 0.
 */
function offset(written: string): number {
  return Number(written.slice(0, -2))
}

/**
 * Marks both ends of a jump a link inside `root` makes, where the router's
 * `pushState` leaves `:target` where it was. The entry or the marker landed on
 * takes `footnote-hit` and the end left takes `footnote-left`, and the way back
 * to the marker pressed takes `aria-current`, each a change of color alone, so
 * no word moves. The router's own scroll focuses the end landed on.
 */
export function followFootnotes(root: Document) {
  const clear = () => {
    for (const element of root.querySelectorAll('.footnote-hit, .footnote-left')) element.classList.remove('footnote-hit', 'footnote-left')
    for (const arrow of root.querySelectorAll('.footnote-backref[aria-current]')) arrow.removeAttribute('aria-current')
  }

  root.addEventListener('click', event => {
    const link   = (event.target as Element).closest<HTMLAnchorElement>('.footnote-ref a[href], .footnote-backref')
    const target = link && root.querySelector<HTMLElement>(`#${CSS.escape(decodeURIComponent(link.hash.slice(1)))}`)
    if (!target) return

    clear()

    const marker = link.closest('sup.footnote-ref')

    if (marker) {
      target.classList.add('footnote-hit')
      marker.classList.add('footnote-left')
      target.querySelector(`.footnote-backref[href="#${CSS.escape(link.id)}"]`)?.setAttribute('aria-current', 'location')
    } else {
      target.closest('sup.footnote-ref')!.classList.add('footnote-hit')
      link.closest('.footnote-item')!.classList.add('footnote-left')
    }
  })
}

/**
 * Moves each run of markers, each way back, and the list closing a page by the
 * fraction of a device pixel separating its art from a whole device pixel,
 * through a relative offset that takes no room, so the art lands on whole device
 * pixels however the words around it fall. The list moves first, since a way back moves with it, and each
 * level reads every position before writing any.
 */
export function snapFootnotes(root: Document) {
  const ratio = root.defaultView!.devicePixelRatio || 1
  const off   = (value: number) => Math.round(value * ratio) / ratio - value

  for (const selector of ['.footnote-snap', '.footnote-run, .footnote-backref']) {
    const moves = [...root.querySelectorAll<HTMLElement>(selector)].flatMap(item => {
      const probe = item.matches('.footnote-snap') ? item : item.querySelector('.footnote-tile, svg')
      const box   = probe?.getBoundingClientRect()
      if (!box?.width) return []
      return [[item, offset(item.style.left) + off(box.left), offset(item.style.top) + off(box.top)] as const]
    })

    for (const [item, left, top] of moves) {
      item.style.left = `${left}px`
      item.style.top  = `${top}px`
    }
  }
}

/**
 * Follows every jump inside `root`, and snaps the page's footnotes on a change
 * of the layout, a font's arrival, a change of device pixel ratio, and each
 * route `router` reaches, keeping whatever hook the router already runs.
 */
export function watchFootnotes(router: Pick<Router, 'onAfterRouteChange'>, root: Document) {
  const view  = root.defaultView!
  const after = router.onAfterRouteChange
  const snap  = () => snapFootnotes(root)
  const watchRatio = () => {
    view.matchMedia(`(resolution: ${view.devicePixelRatio || 1}dppx)`).addEventListener('change', () => {
      snap()
      watchRatio()
    }, { once: true })
  }

  followFootnotes(root)
  new view.ResizeObserver(snap).observe(root.documentElement)
  root.fonts?.addEventListener('loadingdone', snap)
  watchRatio()

  router.onAfterRouteChange = async to => {
    await after?.(to)
    await nextTick(snap)
  }
}
