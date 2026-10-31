// @vitest-environment happy-dom
import { readFileSync } from 'node:fs'
import { join }         from 'node:path'

import { enableAutoUnmount, mount }        from '@vue/test-utils'
import { afterEach, describe, expect, it } from 'vitest'
import { defineComponent }                 from 'vue'

import { figuresAt, traceOf } from '../../../../../lib/front/reward.ts'
import { CLIMB }              from '../../../../../lib/front/reward/climb.ts'
import { IDENTITY }           from '../../../../../lib/identity/identity.ts'
import * as figures           from '../../../../../theme/components/front/reward/figures.tsx'

/**
 * The sheet setting the columns the widget and its key take.
 */
const SHEET = readFileSync(join(import.meta.dirname, '../../../../../theme/styles/front/reward.css'), 'utf8')

/**
 * Draws the figures at the episode's first step.
 */
const Figures = defineComponent({ setup: () => () => figures.drawFigures(figuresAt(traceOf(), 0)) })

enableAutoUnmount(afterEach)

describe('drawFigures', () => {
  it('lays the figures over the climb only from the width the climb stands beside the screen', () => {
    const classes = mount(Figures).classes()
    const split   = Number(/@container \(width >= ([\d.]+)rem\)/u.exec(SHEET)![1]) * 16
    const right   = classes.find(each => each.startsWith('@lg:pr-'))!.slice('@lg:pr-'.length)
    const gap     = IDENTITY.lengths.spacing[right as keyof typeof IDENTITY.lengths.spacing]

    expect([split, classes.filter(each => each.startsWith('@')).every(each => each.startsWith('@lg:'))])
      .toStrictEqual([IDENTITY.lengths.breakpoints.lg, true])
    expect([classes.filter(each => each.endsWith(':absolute')), gap])
      .toStrictEqual([['@lg:absolute'], CLIMB.tile.gap])
  })
})

describe('RewardKey', () => {
  it('takes the widget’s own columns, setting its two keys under the screen and the climb', () => {
    expect(mount(figures.RewardKey).classes()).toContain('reward-pair')
  })
})
