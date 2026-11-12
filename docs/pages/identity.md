# Identity

Every page of the site, its charts, and the logo are drawn in one identity, which `src/squirtl/identity/identity.toml` declares once and `mise write` writes into the theme and into each drawing. Each part below draws one piece of it above the table that lists it, and every table is written from that declaration, so a hex, a face, or a hue read here is the one the site draws in.

## The Palette

Denim, a blue taken after Pokémon Blue's cartridge, leads the palette, beside the hues a chart draws its series in, the hues the sections take, two states, and the grounds, inks, and rules each color scheme sits on. Each hue mixes toward the ground in OKLab for the four shades of its ramp, and Denim's own lighter and darker steps mix it toward white or black. Every contrast below is the ratio WCAG 2.2 measures, where text needs 4.5:1 and a mark needs 3:1.

<details>
<summary>The colors, the ramps, and their contrast</summary>

The tables below are written from `[colors]`, `[neutrals]`, `[ramp]`, `shares`, and `[hues]` in `identity.toml`, and `mise write` rewrites them.

<!-- identity:colors -->

| **Token** | **Name** | **Hex** | **Purpose** |
|---|---|---|---|
| `accent-1` | Heath | `#c08597` | The second series hue, the milestones’ role |
| `accent-2` | Fern | `#5cb878` | The third series hue, the new positions’ role |
| `accent-3` | Amethyst | `#ba55d3` | The fourth series hue, the starter’s role |
| `accent-4` | Seacaller | `#4b8488` | The fifth series hue, random presses’ role |
| `cerulean` | Cerulean | `#91ddff` | The Results section’s hue |
| `critical` | Brick Red | `#c62d42` | The critical state |
| `forest` | Forest | `#0e5900` | The Commands section’s hue |
| `indigo` | Indigo | `#5d05a4` | The Methods section’s hue |
| `primary` | Denim | `#3d6fd0` | The lead, the first series hue, the agent’s role, and the logo’s R and L |
| `warning` | Eureka | `#e8c840` | The warning state |

<!-- /identity:colors -->

<!-- identity:neutrals -->

| **Token** | **Name** | **Hex** | **Purpose** |
|---|---|---|---|
| `dark` | Mirage | `#121722` | The dark ground, and body text on the light ground |
| `dark-lift` | Mirage Lift | `#181e2b` | A raised surface on the dark ground |
| `dark-rule` | Mirage Rule | `#2a3242` | A rule or a border on the dark ground |
| `ground` | Athens Gray | `#f3f4f7` | The light ground, and body text on the dark ground |
| `ground-lift` | Whisper | `#fbfbfd` | A raised surface on the light ground |
| `ground-rule` | Athens Rule | `#dcdfe7` | A rule or a border on the light ground |
| `muted` | Mid Gray | `#999999` | Quiet text on the dark ground |
| `quiet` | Emperor | `#535353` | Quiet text on the light ground |

<!-- /identity:neutrals -->

<!-- identity:ramp -->

| **Token** | **Name** | **Hex** | **Mixes In** | **On Athens Gray** | **On Mirage** | **Purpose** |
|---|---|---|---|---|---|---|
| `deep` | Denim Deep | `#294e95` | 22% black | 7.29:1 | 2.23:1 | A link on the light ground |
| `mid` | Denim Mid | `#7097df` | 27% white | 2.66:1 | 6.13:1 | A link on the dark ground |
| `night` | Denim Night | `#162d5b` | 45% black | 12.24:1 | 1.33:1 | A link under the pointer on the light ground |
| `pale` | Denim Pale | `#92b1e8` | 45% white | 1.97:1 | 8.26:1 | A link under the pointer on the dark ground |

<!-- /identity:ramp -->

<!-- identity:hues -->

| **Hue** | **Ground** | **Step** | **Hex** | **Mixes In** | **Contrast** |
|---|---|---|---|---|---|
| Amethyst | Athens Gray | Shade 1 | `#ede2f4` | 88% Athens Gray | 1.14:1 |
| Amethyst | Athens Gray | Shade 2 | `#e4c6ee` | 70% Athens Gray | 1.40:1 |
| Amethyst | Athens Gray | Shade 3 | `#d6a0e5` | 45% Athens Gray | 1.91:1 |
| Amethyst | Athens Gray | Shade 4 | `#c778dc` | 20% Athens Gray | 2.67:1 |
| Amethyst | Athens Gray | Text | `#9248a8` | 22% Mirage | 5.14:1 |
| Amethyst | Mirage | Shade 1 | `#241f34` | 88% Mirage | 1.13:1 |
| Amethyst | Mirage | Shade 2 | `#402a52` | 70% Mirage | 1.43:1 |
| Amethyst | Mirage | Shade 3 | `#693a7d` | 45% Mirage | 2.14:1 |
| Amethyst | Mirage | Shade 4 | `#9549ac` | 20% Mirage | 3.27:1 |
| Amethyst | Mirage | Text | `#bf64d7` | 8% Athens Gray | 5.14:1 |
| Cerulean | Athens Gray | Shade 1 | `#e8f1f8` | 88% Athens Gray | 1.04:1 |
| Cerulean | Athens Gray | Shade 2 | `#d7eefa` | 70% Athens Gray | 1.09:1 |
| Cerulean | Athens Gray | Shade 3 | `#c0e8fc` | 45% Athens Gray | 1.18:1 |
| Cerulean | Athens Gray | Shade 4 | `#a6e2fe` | 20% Athens Gray | 1.28:1 |
| Cerulean | Athens Gray | Text | `#4d7288` | 50% Mirage | 4.68:1 |
| Cerulean | Mirage | Shade 1 | `#1f2b38` | 88% Mirage | 1.25:1 |
| Cerulean | Mirage | Shade 2 | `#344b5c` | 70% Mirage | 1.97:1 |
| Cerulean | Mirage | Shade 3 | `#547c93` | 45% Mirage | 4.00:1 |
| Cerulean | Mirage | Shade 4 | `#75b1ce` | 20% Mirage | 7.63:1 |
| Cerulean | Mirage | Text | `#91ddff` | None | 11.94:1 |
| Denim | Athens Gray | Shade 1 | `#dce4f4` | 88% Athens Gray | 1.16:1 |
| Denim | Athens Gray | Shade 2 | `#bbcdee` | 70% Athens Gray | 1.46:1 |
| Denim | Athens Gray | Shade 3 | `#8dace5` | 45% Athens Gray | 2.08:1 |
| Denim | Athens Gray | Shade 4 | `#608bda` | 20% Athens Gray | 3.08:1 |
| Denim | Athens Gray | Text | `#294e95` | 22% black | 7.29:1 |
| Denim | Mirage | Shade 1 | `#172134` | 88% Mirage | 1.11:1 |
| Denim | Mirage | Shade 2 | `#1f3051` | 70% Mirage | 1.37:1 |
| Denim | Mirage | Shade 3 | `#2a457c` | 45% Mirage | 1.91:1 |
| Denim | Mirage | Shade 4 | `#345caa` | 20% Mirage | 2.78:1 |
| Denim | Mirage | Text | `#7097df` | 27% white | 6.13:1 |
| Fern | Athens Gray | Shade 1 | `#e2ede7` | 88% Athens Gray | 1.09:1 |
| Fern | Athens Gray | Shade 2 | `#c8e3d0` | 70% Athens Gray | 1.24:1 |
| Fern | Athens Gray | Shade 3 | `#a4d4b1` | 45% Athens Gray | 1.51:1 |
| Fern | Athens Gray | Shade 4 | `#7ec491` | 20% Athens Gray | 1.87:1 |
| Fern | Athens Gray | Text | `#3e7456` | 39% Mirage | 4.98:1 |
| Fern | Mirage | Shade 1 | `#1a282c` | 88% Mirage | 1.18:1 |
| Fern | Mirage | Shade 2 | `#27423c` | 70% Mirage | 1.65:1 |
| Fern | Mirage | Shade 3 | `#396a51` | 45% Mirage | 2.86:1 |
| Fern | Mirage | Shade 4 | `#4c9467` | 20% Mirage | 4.90:1 |
| Fern | Mirage | Text | `#5cb878` | None | 7.33:1 |
| Forest | Athens Gray | Shade 1 | `#d7e1d9` | 88% Athens Gray | 1.22:1 |
| Forest | Athens Gray | Shade 2 | `#afc4ae` | 70% Athens Gray | 1.69:1 |
| Forest | Athens Gray | Shade 3 | `#789d74` | 45% Athens Gray | 2.78:1 |
| Forest | Athens Gray | Shade 4 | `#42773b` | 20% Athens Gray | 4.85:1 |
| Forest | Athens Gray | Text | `#0e5900` | None | 7.80:1 |
| Forest | Mirage | Shade 1 | `#131f22` | 88% Mirage | 1.06:1 |
| Forest | Mirage | Shade 2 | `#142a21` | 70% Mirage | 1.18:1 |
| Forest | Mirage | Shade 3 | `#143b1d` | 45% Mirage | 1.43:1 |
| Forest | Mirage | Shade 4 | `#124b13` | 20% Mirage | 1.74:1 |
| Forest | Mirage | Text | `#658f60` | 36% Athens Gray | 4.82:1 |
| Heath | Athens Gray | Shade 1 | `#ede6eb` | 88% Athens Gray | 1.12:1 |
| Heath | Athens Gray | Shade 2 | `#e5d2d9` | 70% Athens Gray | 1.31:1 |
| Heath | Athens Gray | Shade 3 | `#d8b6c1` | 45% Athens Gray | 1.68:1 |
| Heath | Athens Gray | Shade 4 | `#cb9ba9` | 20% Athens Gray | 2.17:1 |
| Heath | Athens Gray | Text | `#815e6e` | 33% Mirage | 5.08:1 |
| Heath | Mirage | Shade 1 | `#24232f` | 88% Mirage | 1.16:1 |
| Heath | Mirage | Shade 2 | `#413542` | 70% Mirage | 1.55:1 |
| Heath | Mirage | Shade 3 | `#6c515f` | 45% Mirage | 2.54:1 |
| Heath | Mirage | Shade 4 | `#9a6d7e` | 20% Mirage | 4.15:1 |
| Heath | Mirage | Text | `#c08597` | None | 6.01:1 |
| Indigo | Athens Gray | Shade 1 | `#dfdaef` | 88% Athens Gray | 1.24:1 |
| Indigo | Athens Gray | Shade 2 | `#c2b4e2` | 70% Athens Gray | 1.75:1 |
| Indigo | Athens Gray | Shade 3 | `#9b7fce` | 45% Athens Gray | 3.02:1 |
| Indigo | Athens Gray | Shade 4 | `#7749b7` | 20% Athens Gray | 5.58:1 |
| Indigo | Athens Gray | Text | `#5d05a4` | None | 9.44:1 |
| Indigo | Mirage | Shade 1 | `#1a1930` | 88% Mirage | 1.05:1 |
| Indigo | Mirage | Shade 2 | `#271b46` | 70% Mirage | 1.14:1 |
| Indigo | Mirage | Shade 3 | `#3a1b66` | 45% Mirage | 1.30:1 |
| Indigo | Mirage | Shade 4 | `#4d1588` | 20% Mirage | 1.52:1 |
| Indigo | Mirage | Text | `#9373c9` | 39% Athens Gray | 4.73:1 |
| Seacaller | Athens Gray | Shade 1 | `#dee6e9` | 88% Athens Gray | 1.15:1 |
| Seacaller | Athens Gray | Shade 2 | `#c0d1d5` | 70% Athens Gray | 1.43:1 |
| Seacaller | Athens Gray | Shade 3 | `#96b5b9` | 45% Athens Gray | 1.99:1 |
| Seacaller | Athens Gray | Shade 4 | `#6d9a9d` | 20% Athens Gray | 2.82:1 |
| Seacaller | Athens Gray | Text | `#406d73` | 19% Mirage | 5.23:1 |
| Seacaller | Mirage | Shade 1 | `#19222d` | 88% Mirage | 1.12:1 |
| Seacaller | Mirage | Shade 2 | `#22353e` | 70% Mirage | 1.41:1 |
| Seacaller | Mirage | Shade 3 | `#315057` | 45% Mirage | 2.06:1 |
| Seacaller | Mirage | Shade 4 | `#3f6c72` | 20% Mirage | 3.07:1 |
| Seacaller | Mirage | Text | `#5e9094` | 11% Athens Gray | 5.03:1 |

<!-- /identity:hues -->

</details>

## The Faces

Headings and the logo are set in Bitcount Prop Double, a face of round dots, body text in Literata, and code and figures in JetBrains Mono, which the site sets at the size that lines its lowercase letters up with Literata's. Each face loads from Google Fonts at the axes listed below, and a browser sets the text in the fallback until it does.

<details>
<summary>The faces, their axes, and their fallbacks</summary>

The table below is written from `[faces]` in `identity.toml`, and `mise write` rewrites it.

<!-- identity:faces -->

| **Role** | **Family** | **Sets** | **Axes** | **Fallback** |
|---|---|---|---|---|
| Body | Literata | Every paragraph and caption | `ital,opsz,wght@0,7..72,400..700;1,7..72,400..700` | Iowan Old Style, Georgia, serif |
| Code | JetBrains Mono | Code, figures, labels, and chips | `wght@400;500;700` | ui-monospace, SFMono-Regular, Menlo, monospace |
| Display | Bitcount Prop Double | Headings, the hero, and the logo’s letters | `CRSV,ELSH,wght@0,0,500` | ui-monospace, monospace |

<!-- /identity:faces -->

</details>

## The Logo

The logo sets the project's name in the display face's dots, with Blue standing in the R and in the L and a Poké Ball ending the path he walks, a trail of dots in Denim's ramp running from the oldest third to the newest. The trail runs from light to dark on the light ground and from dark to light on the dark one, so its newest dots stand farthest from each ground. Blue's sprite leaves the Game Boy's lightest shade clear where it reaches the sprite's edge, as the Game Boy does, sets it in the light ground where the sprite encloses it, and takes a step of Denim's ramp for each darker shade.

<details>
<summary>The trail on each ground and the Game Boy shades</summary>

The tables below are written from `[logo]` in `identity.toml`, and `mise write` rewrites them.

<!-- identity:logo -->

| **Part** | **On Athens Gray** | **On Mirage** |
|---|---|---|
| The dot still ahead | Denim Pale `#92b1e8` | Denim Night `#162d5b` |
| Blue’s block | Denim `#3d6fd0` | Denim Mid `#7097df` |
| The first third, oldest | Denim Mid `#7097df` | Denim Deep `#294e95` |
| The middle third | Denim `#3d6fd0` | Denim `#3d6fd0` |
| The last third, newest | Denim Deep `#294e95` | Denim Pale `#92b1e8` |

| **Game Boy Shade** | **Takes** |
|---|---|
| 0 | Athens Gray `#f3f4f7` |
| 1 | Denim Pale `#92b1e8` |
| 2 | Denim Deep `#294e95` |
| 3 | Denim Night `#162d5b` |

<!-- /identity:logo -->

</details>

## The Series Order

A chart draws its series in the hues below, in this order, and each hue takes one role wherever a drawing draws it, so the agent reads in Denim on every page. The lines drawn here are made up, each the share of its best across one run. The sections take hues of their own, which no chart draws a series in.

<details>
<summary>The order, the roles, and the sections</summary>

The tables below are written from `order`, `[roles]`, and `[sections]` in `identity.toml`, and `mise write` rewrites them.

<!-- identity:order -->

| **Place** | **Hue** | **Hex** | **Role** |
|---|---|---|---|
| 1 | Denim | `#3d6fd0` | `agent` |
| 2 | Heath | `#c08597` | `milestone` |
| 3 | Fern | `#5cb878` | `novelty` |
| 4 | Amethyst | `#ba55d3` | `starter` |
| 5 | Seacaller | `#4b8488` | `random` |

<!-- /identity:order -->

<!-- identity:sections -->

| **Section** | **Hue** | **Hex** |
|---|---|---|
| Commands | Forest | `#0e5900` |
| Methods | Indigo | `#5d05a4` |
| Results | Cerulean | `#91ddff` |

<!-- /identity:sections -->

</details>

## The Tagline and Byline

The tagline is the one sentence the front page, the README, and the site's card set beneath the name, and the byline is the description the repository, the package, and a link to the site carry.

<details>
<summary>The tagline and the byline</summary>

The table below is written from `tagline` in `identity.toml` and the `description` under `[project]` in `pyproject.toml`, and `mise write` rewrites it.

<!-- identity:tagline -->

| **Line** | **Text** |
|---|---|
| Tagline | An agent that learns the walk to Oak’s lab. |
| Byline | Trains an agent to play Pokémon Blue from the screen, through PyBoy and PyTorch. |

<!-- /identity:tagline -->

</details>

## The Results Charts

The charts on the [Results](results/index.md) page share one look, each part named below by the row of their legend it sits in. The runs it draws are made up, so none of its figures is a measured result.
