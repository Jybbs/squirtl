/**
 * A GIF read back as a viewer shows it, its size, its global palette, the
 * frames carrying a palette of their own, the times it repeats, and each frame
 * whole with the hundredths of a second it holds.
 */
export interface Decoded {
  delays  : number[]
  frames  : Uint32Array[]
  height  : number
  locals  : number
  loops   : number | undefined
  palette : number[]
  width   : number
}

/**
 * Unpacks the LZW codes of one image into its palette indices, as the GIF89a
 * specification sets the decoder out, a code one bit wider each time the table
 * reaches the width's last code.
 */
function decompress(data: Uint8Array, depth: number): number[] {
  const clear  = 1 << depth
  const end    = clear + 1
  const out    : number[] = []
  let table    : number[][] = []
  let size     = depth + 1
  let previous : number[] | undefined
  let [bit, code] = [0, 0]
  const reset = () => {
    table    = Array.from({ length: clear + 2 }, (_, at) => [at])
    size     = depth + 1
    previous = undefined
  }
  reset()
  while (bit + size <= data.length * 8) {
    code = 0
    for (let n = 0; n < size; n++, bit++) code |= (data[bit >> 3]! >> (bit & 7) & 1) << n
    if (code === clear) {
      reset()
      continue
    }
    if (code === end) break
    const entry = code < table.length ? table[code]! : [...previous!, previous![0]!]
    if (previous) table.push([...previous, entry[0]!])
    out.push(...entry)
    previous = entry
    if (table.length === 1 << size && size < 12) size++
  }
  return out
}

/**
 * Reads the bytes of the data sub-blocks starting at `at` in `bytes`.
 *
 * Returns:
 *   The joined bytes and the place just past the block terminator.
 */
function subBlocks(bytes: Uint8Array, at: number): [Uint8Array, number] {
  const parts: number[] = []
  for (let size = bytes[at]!; size > 0; size = bytes[at]!) {
    parts.push(...bytes.subarray(at + 1, at + 1 + size))
    at += size + 1
  }
  return [Uint8Array.from(parts), at + 1]
}

/**
 * Decodes `bytes` as a GIF89a drawn in its global palette, counting each frame
 * carrying a palette of its own, each frame drawn over the one before and left
 * in place, its clear index letting the frame before show.
 */
export function decodeGif(bytes: Uint8Array): Decoded {
  const short   = (at: number) => bytes[at]! | bytes[at + 1]! << 8
  const width   = short(6)
  const height  = short(8)
  const colors  = 2 ** ((bytes[10]! & 7) + 1)
  const palette = Array.from({ length: colors }, (_, n) =>
    bytes[13 + 3 * n]! << 16 | bytes[14 + 3 * n]! << 8 | bytes[15 + 3 * n]!)
  const shown   = new Uint32Array(width * height)
  const decoded : Decoded = { delays: [], frames: [], height, locals: 0, loops: undefined, palette, width }
  let [at, clear, delay] = [13 + 3 * colors, -1, 0]
  while (bytes[at] !== 0x3b) {
    if (bytes[at] === 0x21 && bytes[at + 1] === 0xf9) {
      delay = short(at + 4)
      clear = bytes[at + 3]! & 1 ? bytes[at + 6]! : -1
      at   += 8
    } else if (bytes[at] === 0x21) {
      if (bytes[at + 1] === 0xff) decoded.loops = short(at + 16)
      at = subBlocks(bytes, at + 2)[1]
    } else {
      const [left, top, w] = [short(at + 1), short(at + 3), short(at + 5)]
      const local          = bytes[at + 9]! & 0x80 ? 3 * 2 ** ((bytes[at + 9]! & 7) + 1) : 0
      const [data, next]   = subBlocks(bytes, at + 11 + local)
      decoded.locals      += Math.sign(local)
      for (const [n, index] of decompress(data, bytes[at + 10 + local]!).entries()) {
        if (index !== clear) shown[(top + Math.floor(n / w)) * width + left + n % w] = palette[index]!
      }
      decoded.frames.push(shown.slice())
      decoded.delays.push(delay)
      at = next
    }
  }
  return decoded
}
