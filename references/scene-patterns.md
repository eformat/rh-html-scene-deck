# Scene Patterns & Animation Cookbook

Patterns extracted from the deck family this skill reverses. Each scene is a
`<div class="scene" id="sc-…">` registered in `scenes[]` with an aligned entry
in `sceneLabels[]` (and optionally `sceneAgendaMap[]`).

## Scene skeleton

```html
<!-- ═══════ sc-<name> ═══════ -->
<div class="scene" id="sc-<name>">
    <div class="scene-content">
        <h2 class="rv" id="XX-h">Headline with <span style="color:var(--accent);">key phrase</span></h2>
        <p class="lead rv" id="XX-s">One-sentence setup of the argument.</p>
        <!-- scene body -->
        <div class="footnote rv" id="XX-fn">Source: primary source for any claim above.</div>
    </div>
</div>
```

Conventions:

- **Every element an animation touches gets an id**, prefixed with a short
  scene prefix (`tp-`, `gw-`, `qa-`…). The validator cross-checks every
  animation target against the DOM — a typo'd id is a silent no-op on stage.
- **Mark elements `.rv`** that should be hidden until their reveal beat. They
  transition in via opacity + translate when `.visible` is added.
- **Key phrase highlighting**: wrap it in `<span style="color:var(--accent);">`
  for static accent, or animate `addCls(id,'highlight',delay)` for staged color.
- **Footnotes on data scenes** — every number carries its source. Decks in this
  family end with a sources appendix; a scene-level footnote keeps the claim
  next to the evidence.

## Vertical rhythm (the layout invariant)

Every slide follows the same three-point vertical layout — titles top,
footnotes bottom, content centered between. The template ships the rules; do
not fight them with per-scene hacks:

```css
.scene-content { justify-content: flex-start; }   /* title block at the top */
.scene-content > h2 + :not(.lead) { margin-top: auto; }   /* band start (no lead) */
.scene-content > .lead + * { margin-top: auto; }          /* band start (after lead) */
.scene-content > :nth-last-child(2) { margin-bottom: auto; }  /* band end */
.footnote { margin-top: auto; }                   /* footnote pinned to the bottom */
```

- The **footnote's `margin-top: auto`** pins it to the slide bottom and —
  together with the band's auto margins — splits the free space *above and
  below the content band*, so short slides center their content instead of
  packing at the top with one dead void above the footnote.
- `.text-slide` (hero/title scenes, no footnote) carries `flex: 1` +
  `justify-content: center` — the whole hero block centers vertically. Without
  `flex: 1` the slide keeps its content height and hugs the top of the page.
- **Exception — a scene whose last element grows** (e.g. an embedded demo
  poster with `flex-grow`, or a full-height ladder): opt that scene out of the
  band rules and let the growing element absorb the leftover —
  `#sc-x .scene-content > .lead + * { margin-top: 0; }`,
  `#sc-x .scene-content > :nth-last-child(2) { margin-bottom: auto → 0; }` and
  `#sc-x .footnote { margin-top: 0; }`. The growing element then fills the
  space and the footnote lands at the bottom anyway.
- Verify per slide at two window heights (e.g. 1895×995 and 1280×800): h2 top
  = content top, footnote bottom = content bottom, `scrollHeight ≤
  clientHeight`, and the gap above the band ≈ gap below it.

## Idiom patterns

### Title scene
Eyebrow (mono, uppercase, accent) → h1 → one-line promise →
border-topped meta line (audience · location · date). Reveal 4 beats, ~450ms apart.

### Cards / grid
`h2` headline → `.cards` grid of `.card`s (parallel structure: claim in the
first sentence, evidence in the second) → optional footnote.
Reveal cards one per beat (`reveal(['c-1','c-2','c-3'], 600, 500)`).

### Comparison (BEFORE / AFTER)
Two `.card`s side by side, headers `BEFORE` / `AFTER` (mono, letter-spaced),
the AFTER card carrying `highlight-green` on the delta. Reveal BEFORE fully,
then AFTER, then animate the delta metric last — the contrast is the argument.

### Layered architecture diagram
HTML/CSS layers (flex column of bordered boxes) or SVG. Each layer: mono label
+ `.ext-sub` description. Animate top-down with `reveal()`, then light the
request path with `.flowing` connectors (SVG paths with `fl-dash` dash
animation) and `addCls(id,'lit',…)` on the boxes the request touches.
Interactive variant: clicking a layer explores it (`onclick` → add
`.explored`/`.optimal` classes — remember resetScene must clear them).

### Data / bar chart scene
SVG with axes as `<line>`, grid ticks as `<text class="tick">`, bars as
`<rect>` carrying `data-grow="h"` (horizontal) or `data-grow="v" data-y0="…"`
(vertical, baseline y). Value labels as separate `<text>` revealed after the
bar. Rhythm: draw axes (`drawLine` on `.ln-path` lines) → grow bars staggered
150–300ms → reveal value labels → footnote with source.

```html
<svg viewBox="0 0 600 300">
  <rect id="XX-b1" class="bar" data-grow="h" x="190" y="40"  width="0" height="36"/>
  <text id="XX-v1" x="200" y="63">3.1x</text>
</svg>
```
```js
growBar('XX-b1', 280, 400);        // grows width to 280
reveal(['XX-v1'], 1200, 0);
```

### Agenda / section-arc
Group scenes into agenda sections via `AGENDA` + `sceneAgendaMap` (index of
the section per scene, `null` for standalone scenes like title/appendix). The
sidebar highlights the live section; the topbar shows the scene label. Open
each section with a scene that frames its question before the evidence scenes.

### Stepped walkthrough (talk track)
For a scene the presenter narrates beat-by-beat (demo run-of-show, checklist,
numbered plan): number the rows, give each an id, and let the arrow keys move
a dotted focus frame across the rows **instead of changing scenes**. The press
past the last beat resumes normal navigation.

```css
.beat-focus { outline: 2px dashed var(--accent); outline-offset: 6px; border-radius: 8px; }
```
```js
const WALK_IDX   = scenes.indexOf('sc-demo');
const WALK_BEATS = ['dm-1', 'dm-2', 'dm-3'];
let walkStep = 0;                                   // 0 = no focus, 1..N = row N

function walkFocus(n) {
    WALK_BEATS.forEach((id, i) => {
        const e = document.getElementById(id);
        if (!e) return;
        e.classList.toggle('beat-focus', i === n - 1);
        if (n > 0 && i === n - 1) e.classList.add('visible');  // stepping reveals the beat
    });
    const label = document.getElementById('sceneLabel');
    if (label) label.textContent = n > 0 ? 'Live Demo \u00b7 ' + n + '/' + WALK_BEATS.length : 'Live Demo';
}

function nextScene() {
    if (currentScene === WALK_IDX && walkStep < WALK_BEATS.length) { walkStep++; walkFocus(walkStep); return; }
    goToScene(currentScene + 1);
}
function prevScene() {
    if (currentScene === WALK_IDX && walkStep > 0) { walkStep--; walkFocus(walkStep); return; }
    goToScene(currentScene - 1);
}
```

Rules that make it work:

1. **Route the cursor through `nextScene()`/`prevScene()`** — never the
   keydown handler. The on-screen Prev/Next buttons call the same functions,
   so keyboard and buttons stay in sync.
2. **Reset the cursor in the scene's `animXxx()`** (`walkStep = 0;
   walkFocus(0);` as the first line) — re-entering the scene always starts
   clean, however the presenter left it.
3. Add the focus class to `ANIM_CLASSES` — same invariant as every animated
   class.
4. Update the topbar `sceneLabel` with `· N/M` so the presenter knows where
   they are mid-walkthrough.
5. Finding the scene index with `scenes.indexOf('sc-…')` keeps the pattern
   intact when scenes are inserted or reordered.

### Appendix trio (evidence discipline)
End every data-heavy deck with three scenes:
1. **Ships today** — GA / Dev Preview / Not yet status table
2. **Every number, with conditions** — each claim restated with its caveats
   ("under X workload, Y cache state")
3. **Sources** — grouped list (open-source projects, customer evidence,
   pricing), each with a URL or filing reference

This is what makes the deck defensible in an executive room — figures are
traced, not vibes.

## Animation cookbook

| Helper | Use | Notes |
|---|---|---|
| `reveal(ids, start, step)` | Progressive disclosure of `.rv` elements | The workhorse. ~400ms first beat, 300–600ms per beat. |
| `addCls(id, cls, delay)` | Color/state changes (`highlight`, `lit`, `flowing`) | Class **must** be in `ANIM_CLASSES`. |
| `rmCls(id, cls, delay)` | Undo a state mid-scene (e.g. dim the BEFORE card) | |
| `growBar(id, value, delay)` | SVG bar growth | Needs `data-grow` (`h`/`v`, plus `data-y0` for vertical). |
| `drawLine(id, delay)` | SVG path draw-on | Element needs class `ln-path`; resetScene resets dashoffset. |
| `scheduleInScene(fn, delay)` | Anything custom | **Always** through this — `goToScene` cancels `sceneTimers` on navigation. Never raw `setTimeout` for scene animation. |

Timing rhythm: headline first (200–400ms), body beats 300–600ms apart, punch
line last, footnote after the audience has seen the number. Total scene
animation under ~4s so fast paging doesn't feel laggy.

## resetScene discipline (the invariant that matters)

`resetScene(sceneId)` runs on every navigation and must return the scene to
its resting state. The template loops over the `ANIM_CLASSES` array and resets
SVG geometry (`data-grow` bars back to 0, `.ln-path` dashoffsets back to
hidden). When you introduce a new animated class or any inline-style/SVG
mutation:

1. Add the class to `ANIM_CLASSES` **and** define its resting default in CSS.
2. If you mutate inline styles or SVG attributes (which class removal cannot
   undo), add an explicit reset in `resetScene` keyed by element id.
3. Run `scripts/validate_deck.py` — it fails the build if an added class is
   never cleared.

Why: presenters jump backwards mid-briefing. A scene that only plays forward
correctly will visually corrupt the deck the first time someone pages back.
(The source deck this skill was extracted from shipped with exactly this bug:
bar animations added `.grown`/`.over` that `resetScene` never cleared.)
