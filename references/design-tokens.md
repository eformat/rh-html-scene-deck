# Design Tokens & Theming

All brand-specific values live in the `THEME TOKENS` block at the top of
`assets/deck-template.html` (`:root` custom properties). Component rules below
it reference tokens only — retheming means changing that block, never the
components.

## Red Hat default token set

### Brand
| Token | Value | Role |
|---|---|---|
| `--accent` | `#EE0000` | Primary brand color: headlines' key phrase, progress bar, scene dots, active states |
| `--accent-dark` | `#a30000` | Pressed / gradient stop, `done` dots |
| `--accent-glow` | `rgba(238,0,0,.15)` | Box-shadow glows on `.lit` elements |

### Surfaces & text
| Token | Value |
|---|---|
| `--bg-primary` | `#151515` (deck background) |
| `--bg-secondary` | `#1e1e1e` (cards, topbar gradient) |
| `--bg-hover` | `#252525` |
| `--border` | `#3a3a3a` (cards, dividers, tracks) |
| `--text-primary` | `#ffffff` (h1/h2) |
| `--text-secondary` | `#f0f0f0` (body, lead) |
| `--text-dim` | `#dcdcdc` (meta, footnotes, chrome) |

### Semantic colors (diagrams, charts, statuses)
`--green #5cb85c` · `--blue #4a90d9` · `--magenta #e44d8e` ·
`--yellow #f0ad4e` · `--orange #e87040` · `--cyan #5bc0de` · `--purple #9b59b6`

Use semantic colors for diagram roles (request path, trust boundaries,
statuses), never as decoration. In charts, one color per series, accent only
for the series the argument is about.

### Typography
- Display: `'Red Hat Display', Arial, sans-serif` — everything
- Mono: `'Red Hat Mono', 'Courier New', monospace` — labels, ticks, badges,
  footnotes, the scene-label chrome

Type scale is presentation-sized with `clamp()`, so the same file works on a
projector (large) and a laptop (small):

| Token | clamp range |
|---|---|
| `--title-size` | `clamp(2rem, 5vw, 4rem)` |
| `--h2-size` | `clamp(1.75rem, 3.5vw, 2.5rem)` |
| `--h3-size` | `clamp(1.15rem, 2.5vw, 1.75rem)` |
| `--body-size` | `clamp(1rem, 1.8vw, 1.25rem)` |
| `--small-size` | `clamp(0.8rem, 1.2vw, 1rem)` |

### Motion
`--ease-out-expo cubic-bezier(.16,1,.3,1)` · `--ease-out-cubic
cubic-bezier(.33,1,.68,1)` · `--ease-in-out cubic-bezier(.42,0,.58,1)`.
Reveals and bar growth use the out-cubic curve; the fl-dash connector
animation uses linear.

## Retheming

1. Change `--accent`, `--accent-dark`, `--accent-glow` (and the two hardcoded
   particle/drawing colors in the script — search `238, 0, 0`).
2. Swap `--font-display`/`--font-mono` and the Google Fonts `<link>` if not
   Red Hat branded.
3. Adjust `--bg-primary`/`--bg-secondary` for a light theme — also review
   `.topbar` and `.sidebar` gradients and the `--border` value for contrast.
4. Keep the `clamp()` scales and height breakpoints — they encode the
   projector-vs-laptop sizing this deck family relies on.

## Height breakpoints (encoded responsive behavior)

- `≤700px` viewport height: smaller padding/type (wall screens, split view)
- `≤600px`: smaller again; **sidebar and scene dots hidden** (no room)
- `≤500px`: minimum type scale (laptop with docked console)
- `≤600px` width: title scale adjusts for narrow screens

These exist because decks in this family get briefed from lecture halls,
laptops, and screen shares. Don't remove them; tune the values only if a
target device requires it.
