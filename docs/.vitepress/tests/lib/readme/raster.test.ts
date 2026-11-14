import { describe, expect, it } from 'vitest'

import { Raster } from '../../../lib/readme/raster.ts'

/**
 * Reads every pixel of `raster` as its red, green, blue, and alpha bytes.
 */
const bytesOf = ({ view }: Raster): number[][] =>
  Array.from({ length: view.data.length / 4 }, (_, at) => [...view.data.subarray(4 * at, 4 * at + 4)])

describe('Raster', () => {
  it('opens on a grid of the size asked with every pixel clear', () => {
    const { view } = new Raster(3, 2)

    expect([view.width, view.height, view.data.length]).toStrictEqual([3, 2, 24])
    expect(view.data.every(byte => byte === 0)).toBe(true)
  })

  it('fills only the part of a rectangle inside the grid', () => {
    const raster     = new Raster(2, 2)
    raster.fillStyle = '#ff8000'

    raster.fillRect(1, -1, 4, 2)

    expect(bytesOf(raster)).toStrictEqual([[0, 0, 0, 0], [255, 128, 0, 255], [0, 0, 0, 0], [0, 0, 0, 0]])
  })

  it('blends a fill over what lies under it at the opacity it holds', () => {
    const raster     = new Raster(1, 1)
    raster.fillStyle = '#ffffff'
    raster.fillRect(0, 0, 1, 1)

    raster.globalAlpha = 0.25
    raster.fillStyle   = '#000000'
    raster.fillRect(0, 0, 1, 1)

    expect(bytesOf(raster)).toStrictEqual([[191, 191, 191, 255]])
  })

  it('copies a view onto the grid at the corner it is put at', () => {
    const raster   = new Raster(3, 2)
    const { view } = new Raster(2, 1)
    view.data.set([1, 2, 3, 4, 5, 6, 7, 8])

    raster.putImageData(view, 1, 1)

    expect(bytesOf(raster).slice(3)).toStrictEqual([[0, 0, 0, 0], [1, 2, 3, 4], [5, 6, 7, 8]])
  })
})
