# html-scene-deck

An agent skill for building **self-contained single-file HTML presentation
decks** — a vanilla-JS scene engine with animated reveals, agenda sidebar,
scene dots, a presenter drawing overlay, and Red Hat dark-theme design
tokens — plus an optional ConfigMap/OpenShift deploy path.

This repo **is** the skill: `SKILL.md` at the root is the entry point the
agent reads.

## Install

Clone into your agents' skills directory (any harness that loads skills from
a directory, e.g. OpenCode):

```bash
git clone <this-repo-url> ~/.agents/skills/html-scene-deck
```

Restart the agent session so it picks the skill up.

## Requirements

- `python3` — to run the deck validator
- A browser — decks are plain HTML, no server needed to present
- For the optional OpenShift deploy path only: `kubectl`, `kustomize`,
  `envsubst`

## Use

### With an agent

Ask for a deck, e.g.:

> Make me a single-file HTML deck for an executive briefing on X — dark
> theme, animated, about 8 slides, with a next-steps and sources appendix.

The agent follows `SKILL.md`: copies `assets/deck-template.html`, writes the
scenes, validates with `scripts/validate_deck.py`, and (optionally) deploys.

### By hand

1. Copy `assets/deck-template.html` to `deck.html` and edit the scenes
   (one `<div class="scene">` per slide; register each scene in the
   `scenes[]` / `sceneLabels[]` arrays).
2. Validate invariants:

   ```bash
   python3 scripts/validate_deck.py deck.html
   ```

### Keyboard & controls

| Input | Action |
|---|---|
| `←` / `→` | Previous / next scene |
| `Home` / `End` | First / last scene |
| `D` / `E` / `R` | Draw mode / erase mode / reset drawings |
| `Esc` | Turn the pen off |
| Button bar | Prev, Next, Draw, Erase, Reset (clickable mirror of the keys) |

### Deploy to OpenShift (optional)

Serves the deck as a ConfigMap consumed by nginx-unprivileged, rendered
with envsubst and built with kustomize:

```bash
cp assets/deploy/* my-deploy/ && cd my-deploy
cp env.example env.local        # edit APP_NAME, NAMESPACE,
                                # CONFIGMAP_NAME, DECK_FILE
./deploy.sh                     # render → build → apply → rollout status
```

See `references/k8s-deploy.md` for details.

## Layout

| Path | What it is |
|---|---|
| `SKILL.md` | Skill instructions (the agent reads this) |
| `assets/deck-template.html` | The deck template: scene engine, draw overlay, button bar |
| `assets/deploy/` | Deploy assets: `deploy.sh`, `env.example`, kustomize/deployment templates |
| `references/` | `design-tokens.md`, `scene-patterns.md`, `k8s-deploy.md` |
| `scripts/validate_deck.py` | Deck invariant checker (standalone) |
| `scripts/make_configmap.py` | ConfigMap manifest generator |
| `evals/` | Eval prompts + the `starter-deck.html` fixture |

## Notes

- Generated decks load Red Hat Display/Mono from Google Fonts and fall back
  to system fonts when offline.
- The deploy flow needs cluster access and is optional — deck building and
  validating need nothing but Python and a browser.
