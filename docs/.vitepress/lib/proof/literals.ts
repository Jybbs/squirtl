/**
 * The named colors CSS Color 4 defines, which a stylesheet may write in place
 * of a hex, each a literal color no theme variable supplies.
 */
const NAMED = [
  'aliceblue', 'antiquewhite', 'aqua', 'aquamarine', 'azure', 'beige', 'bisque', 'black',
  'blanchedalmond', 'blue', 'blueviolet', 'brown', 'burlywood', 'cadetblue', 'chartreuse',
  'chocolate', 'coral', 'cornflowerblue', 'cornsilk', 'crimson', 'cyan', 'darkblue',
  'darkcyan', 'darkgoldenrod', 'darkgray', 'darkgreen', 'darkgrey', 'darkkhaki',
  'darkmagenta', 'darkolivegreen', 'darkorange', 'darkorchid', 'darkred', 'darksalmon',
  'darkseagreen', 'darkslateblue', 'darkslategray', 'darkslategrey', 'darkturquoise',
  'darkviolet', 'deeppink', 'deepskyblue', 'dimgray', 'dimgrey', 'dodgerblue', 'firebrick',
  'floralwhite', 'forestgreen', 'fuchsia', 'gainsboro', 'ghostwhite', 'gold', 'goldenrod',
  'gray', 'green', 'greenyellow', 'grey', 'honeydew', 'hotpink', 'indianred', 'indigo',
  'ivory', 'khaki', 'lavender', 'lavenderblush', 'lawngreen', 'lemonchiffon', 'lightblue',
  'lightcoral', 'lightcyan', 'lightgoldenrodyellow', 'lightgray', 'lightgreen', 'lightgrey',
  'lightpink', 'lightsalmon', 'lightseagreen', 'lightskyblue', 'lightslategray',
  'lightslategrey', 'lightsteelblue', 'lightyellow', 'lime', 'limegreen', 'linen',
  'magenta', 'maroon', 'mediumaquamarine', 'mediumblue', 'mediumorchid', 'mediumpurple',
  'mediumseagreen', 'mediumslateblue', 'mediumspringgreen', 'mediumturquoise',
  'mediumvioletred', 'midnightblue', 'mintcream', 'mistyrose', 'moccasin', 'navajowhite',
  'navy', 'oldlace', 'olive', 'olivedrab', 'orange', 'orangered', 'orchid', 'palegoldenrod',
  'palegreen', 'paleturquoise', 'palevioletred', 'papayawhip', 'peachpuff', 'peru', 'pink',
  'plum', 'powderblue', 'purple', 'rebeccapurple', 'red', 'rosybrown', 'royalblue',
  'saddlebrown', 'salmon', 'sandybrown', 'seagreen', 'seashell', 'sienna', 'silver',
  'skyblue', 'slateblue', 'slategray', 'slategrey', 'snow', 'springgreen', 'steelblue',
  'tan', 'teal', 'thistle', 'tomato', 'turquoise', 'violet', 'wheat', 'white', 'whitesmoke',
  'yellow', 'yellowgreen'
] as const

/**
 * The shapes of a literal a declaration may set where a theme variable should
 * supply it, a length or a time other than zero, a color written as a hex, a
 * color function, or a name, and an easing curve written as a function or a
 * keyword.
 */
const SHAPES = [
  /(?<![\w.-])-?(?:\d*\.)?\d*[1-9]\d*(?:\.\d+)?(?:px|rem|em|ex|ch|lh|vw|vh|vmin|vmax|dvh|svh|cqw|cqh|cqi|pt|pc|cm|mm|in|ms|s)\b/u,
  /#[\da-f]{3,8}\b/iu,
  /\b(?:rgba?|hsla?|hwb|lab|lch|oklab|oklch|color)\(/iu,
  /\b(?:cubic-bezier|steps|linear)\(/iu,
  /(?:^|[\s,])(?:ease|ease-in|ease-out|ease-in-out|linear|step-start|step-end)(?=$|[\s,])/iu,
  new RegExp(String.raw`(?:^|[\s,(])(?:${NAMED.join('|')})(?=$|[\s,)])`, 'iu')
]

/**
 * The properties that name a face, the `font` shorthand, `font-family`, and a
 * custom property holding one, such as VitePress's `--vp-font-family-base`.
 */
const FAMILY = /^font$|(?:^|-)font-family(?:$|-)/u

/**
 * The keywords a property naming a face may take in place of a family, each
 * deferring to a value set elsewhere.
 */
const KEYWORDS = /^(?:inherit|initial|revert|revert-layer|unset)$/u

/**
 * The one literal length a theme variable cannot supply and Tailwind writes for
 * a fully rounded corner, which stands for no particular size.
 */
const UNBOUNDED = /calc\(infinity \* 1px\)/gu

/**
 * Lists the declarations of `css` that set a length, a time, a color, an easing
 * curve, or a face no theme variable supplies, reading only the declarations
 * inside rule blocks, so the initial value an `@property` rule registers, a
 * media or container query's width, and a selector pass, and dropping every
 * `var()` before it looks, so a value that reads a variable passes whatever its
 * fallback. A custom property's own value passes unless `handwritten` is set,
 * as it is for every sheet but the utilities, whose `@theme` block declares
 * each variable from the identity. Each declaration is written as its property
 * and its value, `name: value`.
 */
export function literals(css: string, handwritten = false): string[] {
  const found: string[]  = []
  const text             = css.replaceAll(/\/\*[\s\S]*?\*\//gu, '')
  const blocks: string[] = []
  let start              = 0
  for (const { 0: char, index } of text.matchAll(/[{};]/gu)) {
    if (char === '{') {
      blocks.push(text.slice(start, index).trim())
    } else {
      const body   = text.slice(start, index).trim()
      const colon  = body.indexOf(':')
      const name   = body.slice(0, colon).trim()
      const value  = body.slice(colon + 1).trim()
      const bare   = value.replaceAll(/var\([^()]*(?:\([^()]*\)[^()]*)*\)/gu, '').replaceAll(UNBOUNDED, '')
      const ruled  = blocks.length > 0 && !blocks.at(-1)!.startsWith('@property')
      const face   = FAMILY.test(name) && bare.trim() !== '' && !KEYWORDS.test(bare.trim())
      const listed = handwritten || !name.startsWith('--')
      if (ruled && colon > 0 && listed && (face || SHAPES.some(shape => shape.test(bare)))) {
        found.push(`${name}: ${value}`)
      }
      if (char === '}') blocks.pop()
    }
    start = index + 1
  }
  return found
}
