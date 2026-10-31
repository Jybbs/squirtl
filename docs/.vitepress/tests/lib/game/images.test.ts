// @vitest-environment happy-dom
import { flushPromises }            from '@vue/test-utils'
import { describe, expect, it, vi } from 'vitest'

import WORLD          from '../../../lib/art/world.json' with { type: 'json' }
import { RoomImages } from '../../../lib/game/images.ts'

/**
 * Makes a stand-in for the browser's image loading, which records every source
 * it loads and gives back an image whose decoding settles as `decoded` does.
 */
function loading(decoded: () => Promise<void> = async () => {}) {
  const sources: string[] = []
  const decode            = vi.fn<() => Promise<void>>(decoded)
  const load              = (source: string) => {
    sources.push(source)
    return { decode, src: source } as unknown as HTMLImageElement
  }
  return { decode, load, sources }
}

describe('RoomImages', () => {
  it('loads a room’s image in the light scheme on its first read and keeps it for every later read', () => {
    const { load, sources } = loading()
    const images            = new RoomImages(load)
    const first             = images.image('pallet')

    expect([images.image('pallet'), sources]).toStrictEqual([first, [WORLD.pallet.image.light]])
  })

  it('decodes every room’s image and calls back once all of them can draw', async () => {
    const { decode, load, sources } = loading()
    const then                      = vi.fn<() => void>()

    new RoomImages(load).whenReady(then)
    await flushPromises()

    expect(sources).toStrictEqual(Object.values(WORLD).map(room => room.image.light))
    expect([decode.mock.calls.length, then.mock.calls.length]).toStrictEqual([sources.length, 1])
  })

  it('decodes only the rooms it is given', async () => {
    const { load, sources } = loading()
    const then              = vi.fn<() => void>()

    new RoomImages(load).whenReady(then, ['pallet'])
    await flushPromises()

    expect([sources, then.mock.calls.length]).toStrictEqual([[WORLD.pallet.image.light], 1])
  })

  it('leaves the call unmade where an image fails to decode', async () => {
    const { load } = loading(() => Promise.reject(new Error('undecodable')))
    const then     = vi.fn<() => void>()

    new RoomImages(load).whenReady(then)
    await flushPromises()

    expect(then).not.toHaveBeenCalled()
  })

  it('loads through the page’s own `Image` unless given a loader', () => {
    const image = new RoomImages().image('lab')

    expect(image).toBeInstanceOf(HTMLImageElement)
    expect(image.getAttribute('src')).toBe(WORLD.lab.image.light)
  })
})
