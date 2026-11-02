---
name: html-scene-deck
description: >
  Build self-contained single-file HTML presentation decks — a custom
  JavaScript scene engine with animated reveals, agenda sidebar, scene dots,
  presenter drawing overlay, and Red Hat design tokens — then validate and
  deploy them to Kubernetes/OpenShift as a ConfigMap served by nginx via
  kustomize + envsubst. Use this skill whenever the user asks for an HTML
  presentation, web slides, a briefing deck, an executive/customer briefing,
  animated slides, "make me a deck", or wants to serve/present HTML slides
  from a cluster, wrap a deck in a ConfigMap, or deploy a presentation to
  OpenShift — even if they don't say the word "deck".
---

# HTML Scene Deck

Generate, validate, and deploy single-file HTML presentation decks with a
custom scene engine — no frameworks, no bundler, no dependencies. The entire
deck is one portable file that works offline.

## The pipeline

Follow these five steps in order. Each step feeds the next; skipping a step
produces decks that corrupt on stage or silently break in deployment.

```
1. SOURCE  →  2. STRUCTURE  →  3. BUILD  →  4. VALIDATE  →  5. DEPLOY
```

### Step 1 — Source

Gather the deck's content before writing any HTML:

- **The narrative arc**: what the audience must understand by the end, in one
  sentence. Everything else serves it.
- **Claims and numbers**: every figure needs a primary source. Collect them
  now — the deck ends with a sources appendix and per-scene footnotes, and a
  number without provenance gets cut, not guessed.
- **Audience, venue, date**: goes on the title scene's meta line.
- **Honesty framing**: distinguish what ships today (GA), what is preview
  (Dev Preview), and what does not exist. An appendix scene for status keeps
  the body honest and the appendix defensible.

For a Red Hat AI/infrastructure briefing, source from primary material:
project docs, published pricing, recorded keynotes, customer stories. Ask the
user for material rather than inventing figures.

### Step 2 — Structure

Plan the scene list before building. Output a table: scene id (`sc-…`), short
label (2–4 words for dots/topbar), agenda section (or none), and what it
shows. This table becomes three index-aligned JS arrays in the deck:

- `scenes[]` — DOM ids, in presentation order
- `sceneLabels[]` — short names for the dots tooltip and topbar
- `sceneAgendaMap[]` — agenda section index per scene, `null` for standalone

Keep decks at roughly 8–15 scenes for a lightning brief, 25–35 for an
executive deep-dive. Group scenes into agenda sections of 2–5 scenes; open
each section with a scene that frames its question before the evidence.

### Color semantics

Use the full palette — decks that lean only on `--accent` read flat on
stage. The tokens ship in the template (`references/design-tokens.md`);
colorize key spans in scene text, roughly two colors per scene:

- `--green` — secure, validated, blocked, attested, cheap, enforced
- `--yellow` — caution, risk, roadmap/"next beat", honest caveats and
  upstream blockers
- `--blue` — neutral info: platform labels, commands, tech stacks,
  sources, evidence
- `--orange` — hard warnings; `--accent` stays the brand emphasis

The presenter draw stroke follows `--draw-color` (defaults to
`--accent`) — override it in THEME TOKENS when the deck's emphasis
color differs.

Inline spans in copy follow the deck-family pattern
(`<span style="color:var(--green);">…</span>`); `.highlight-green/
-blue/-yellow` are for JS-toggled emphasis only (they carry `!important`,
so never use them for static text that should also animate). Status
tables use `.ok` (green) / `.deny` (red) as-is.

### Step 3 — Build

Copy `assets/deck-template.html` as the starting point — it contains the
working engine, chrome (topbar, progress bar, scene dots, agenda sidebar,
Prev/Next + Draw/Erase/Reset control buttons), theme tokens, particle
background, and presenter drawing overlay. Then:

1. Set the `<title>` and topbar brand mark.
2. Author one `<div class="scene" id="sc-…">` per slide, replacing the two
   example scenes. Follow `references/scene-patterns.md` — it has copy-paste
   skeletons for title, cards, comparison, animated diagram, bar chart,
   stepped walkthrough, and appendix scenes, plus the animation cookbook
   (`reveal`, `growBar`, `drawLine`).
3. Register every scene in `scenes[]`/`sceneLabels[]`/`sceneAgendaMap[]`,
   index-aligned.
4. Write one `animXxx()` function per scene and dispatch it in
   `runSceneAnimation()` — one `case` per index.
5. If you introduce any new animated class or inline-style/SVG mutation, add
   it to `ANIM_CLASSES` and extend `resetScene()`. This is the deck's single
   most important invariant: state that survives backward navigation corrupts
   the deck in front of an audience.
6. Retheme only in the `THEME TOKENS` block (`references/design-tokens.md`
   documents every token; Red Hat branding is the default).
7. Respect the **vertical rhythm** invariant (`references/scene-patterns.md`):
   title block top, footnote pinned bottom, content band centered between —
   the template's `.scene-content` / `.footnote` auto-margin rules do this
   automatically. Only opt a scene out when one element grows to fill the
   slide (embedded player, full-height ladder). Titles hug the top and
   footnotes align at the same bottom line on every slide; content must never
   scrunch against either edge.

Single-file guarantee: styles, fonts (Google Fonts link is the one allowed
external reference), scripts, and SVG are all inline. No local file
references — the file must work offline and inside a ConfigMap.

### Step 4 — Validate

Run the validator before handing the deck over:

```bash
python3 scripts/validate_deck.py deck.html
```

It checks the invariants that actually break decks: registry alignment, scene
DOM coverage, animation targets that silently no-op, animation state that is
never cleared (state leaks), dispatch coverage, single-file references, and
JS syntax. Fix every error; warnings (`.rv` hygiene) are worth reviewing.
If a ConfigMap wrapper exists, validate it too:

```bash
python3 scripts/validate_deck.py deck.html --configmap deck-cm.yaml
```

Optionally smoke-test in a browser (open the file, arrow through all scenes
forwards and backwards, check for visual debris from leaked state).

### Step 5 — Deploy

To serve the deck from Kubernetes/OpenShift, use the kustomize + envsubst
pipeline in `assets/deploy/` — full details in
`references/k8s-deploy.md`:

```bash
cp assets/deploy/env.example assets/deploy/env.local   # edit: app, namespace, deck path
assets/deploy/deploy.sh
```

Pipeline: envsubst renders the templates → kustomize builds the ConfigMap
(content-hashed, so every deck change triggers a rolling update) →
`kubectl apply -k` → rollout status. The nginx-unprivileged pod serves the
deck on port 8080; view with `kubectl port-forward` or an OpenShift route.

For sharing or one-off applies without kustomize, emit the standalone
ConfigMap wrapper the deck family ships with:

```bash
python3 scripts/make_configmap.py deck.html    # → <deck-stem>-html.yaml
```

## Reference map

| Need | Read |
|---|---|
| Scene skeletons, animation cookbook, resetScene discipline | `references/scene-patterns.md` |
| Theme tokens, retheming, breakpoints | `references/design-tokens.md` |
| Kustomize + envsubst deploy, ConfigMap wrapper | `references/k8s-deploy.md` |
| Structural QA | `scripts/validate_deck.py` (run, don't read) |
| ConfigMap wrapper emitter | `scripts/make_configmap.py` |
| MP4 → Arcade-style zoomable demo (camera + spotlight, companion skill) | `~/.agents/skills/arcade-demo/` (`references/arcade-anatomy.md`) |

## Design lineage

This pipeline reverse-engineers a working deck family (self-contained
executive-briefing decks with a custom vanilla-JS scene engine, canvas
particle background, and a drawing overlay with Prev/Next/Draw/Erase/Reset
control buttons — no frameworks). The
template encodes their proven patterns; the validator encodes the failure
modes they shipped with. When in doubt, prefer the pattern that survives a
presenter paging backwards.
