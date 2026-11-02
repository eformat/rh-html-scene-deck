#!/usr/bin/env python3
"""validate_deck.py — deterministic QA for single-file scene-engine decks.

Checks the invariants the deck architecture depends on:

  1. Registry alignment      scenes[] / sceneLabels[] / sceneAgendaMap[] same length
  2. Scene DOM coverage      every scenes[] id exists as an element; no duplicates
  3. Reveal hygiene          every .rv element has an id; every id targeted by
                             reveal/addCls/rmCls/growBar/drawLine/getElementById
                             exists (catches typos before the briefing)
  4. State-reset coverage    every class added by animations is either in
                             ANIM_CLASSES or cleared inside resetScene()
  5. Dispatch coverage       runSceneAnimation handles every scene index
  6. Single-file guarantee   no local (non-https) external references
  7. JS syntax               <script> blocks parse cleanly (node --check)
  8. ConfigMap wrapper       optional: embedded HTML matches the deck file

Usage:
  validate_deck.py deck.html
  validate_deck.py deck.html --configmap deck-cm.yaml

Exit code 0 = clean, 1 = errors, 2 = warnings only.
"""
import argparse
import re
import shutil
import subprocess
import sys
import tempfile

ERRORS = []
WARNINGS = []


def err(msg):
    ERRORS.append(msg)


def warn(msg):
    WARNINGS.append(msg)


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def script_body(html):
    m = re.search(r"<script[^>]*>(.*?)</script>", html, re.S)
    return m.group(1) if m else ""


def js_array(js, name):
    """Extract a `const NAME = [ ... ];` array, returning raw element tokens.
    Handles strings, numbers, null — not just string literals."""
    m = re.search(r"const\s+%s\s*=\s*\[(.*?)\]\s*;" % re.escape(name), js, re.S)
    if not m:
        return None
    content = re.sub(r"//[^\n]*", "", m.group(1))
    # split on top-level commas, respecting quotes
    parts, buf, quote = [], "", None
    for ch in content:
        if quote:
            buf += ch
            if ch == quote:
                quote = None
        elif ch in "'\"":
            quote = ch
            buf += ch
        elif ch == ",":
            parts.append(buf.strip())
            buf = ""
        else:
            buf += ch
    if buf.strip():
        parts.append(buf.strip())
    out = []
    for p in parts:
        q = re.fullmatch(r"'([^']*)'|\"([^\"]*)\"", p)
        out.append((q.group(1) or q.group(2)) if q else p)
    return out


def element_ids(html):
    return set(re.findall(r'id="([^"]+)"', html)) | set(re.findall(r"id='([^']+)'", html))


def brace_block(src, start):
    """Return src[start:end] for the {...} block whose opening brace is the
    first '{' at or after `start`."""
    i = src.find("{", start)
    if i == -1:
        return src[start:]
    depth = 0
    for j in range(i, len(src)):
        if src[j] == "{":
            depth += 1
        elif src[j] == "}":
            depth -= 1
            if depth == 0:
                return src[start : j + 1]
    return src[start:]


def function_block(js, name):
    m = re.search(r"function\s+%s\s*\(" % re.escape(name), js)
    if not m:
        return None
    return brace_block(js, m.start())


def check_registry(js):
    scenes = js_array(js, "scenes")
    labels = js_array(js, "sceneLabels")
    agenda = js_array(js, "sceneAgendaMap")
    if scenes is None:
        err("scenes[] registry not found in script")
        return None, None, None
    if labels is None:
        err("sceneLabels[] registry not found in script")
        labels = []
    if not scenes:
        err("scenes[] is empty — no slides registered")
    if len(scenes) != len(labels):
        err(
            "scenes[] (%d) and sceneLabels[] (%d) lengths differ — "
            "every scene needs a short label for the dots/topbar"
            % (len(scenes), len(labels))
        )
    if agenda is not None and len(agenda) != len(scenes):
        err(
            "sceneAgendaMap[] (%d) and scenes[] (%d) lengths differ — "
            "use null for scenes that belong to no agenda section"
            % (len(agenda), len(scenes))
        )
    dupes = {s for s in scenes if scenes.count(s) > 1}
    if dupes:
        err("duplicate scene ids in scenes[]: %s" % ", ".join(sorted(dupes)))
    return scenes, labels, agenda


def check_scene_dom(html, scenes):
    ids = element_ids(html)
    for s in scenes or []:
        if s not in ids:
            err("scene '%s' is registered in scenes[] but no element has that id" % s)
    scenes_els = re.findall(r'class="scene[^"]*"', html)
    if scenes and len(scenes_els) < len(scenes):
        warn(
            "found %d elements with class 'scene' but %d registered scenes"
            % (len(scenes_els), len(scenes))
        )


def dynamic_target(literal, tail):
    """True when the id string is part of a dynamic concatenation (e.g. 'ag-' + i)."""
    after = tail[literal.end() : literal.end() + 4]
    return after.lstrip().startswith("+")


def targeted_ids(js):
    """All element ids the animation code addresses, split into static and dynamic."""
    static, dynamic = set(), set()
    # the $() shorthand is a common alias for getElementById
    has_dollar = bool(re.search(r"function\s+\$\s*\(\s*id\s*\)", js)) or bool(
        re.search(r"const\s+\$\s*=\s*\(?\s*(?:id\s*=>|function)", js)
    )
    patterns = [
        r"getElementById\('([^']+)'\)",
        r"getElementById\(\"([^\"]+)\"\)",
        r"\breveal\(\s*\[([^\]]*)\]",
        r"\baddCls\(\s*'([^']+)'",
        r"\brmCls\(\s*'([^']+)'",
        r"\bgrowBar\(\s*'([^']+)'",
        r"\bdrawLine\(\s*'([^']+)'",
    ]
    if has_dollar:
        patterns.append(r"\$\('([^']+)'\)")
    for pat in patterns:
        for m in re.finditer(pat, js):
            raw = m.group(1)
            if dynamic_target(m, js):
                dynamic.add(raw.rstrip("'-"))
                continue
            # group(1) is already unquoted for single-id patterns; reveal-style
            # arrays carry quotes, so extract quoted parts when present
            parts = re.findall(r"'([^']+)'|\"([^\"]+)\"", raw)
            if parts:
                for a, b in parts:
                    if a or b:
                        static.add(a or b)
            else:
                v = raw.strip().strip("'\"")
                if v:
                    static.add(v)
    # reveal([...]) arrays
    for m in re.finditer(r"\breveal\(\s*\[([^\]]*)\]", js):
        for a, b in re.findall(r"'([^']+)'|\"([^\"]+)\"", m.group(1)):
            if a or b:
                static.add(a or b)
    return static, dynamic


def enclosing_tag(html, elem_id):
    """The full opening tag containing id='elem_id' (class may precede the id)."""
    return re.search(r"<[a-zA-Z][^>]*\bid=[\"']%s[\"'][^>]*>" % re.escape(elem_id), html, re.S)


def check_ids(html, js, scenes):
    ids = element_ids(html)
    static, dynamic = targeted_ids(js)
    known_dynamic_prefixes = tuple(p for p in ("ag-", "agc-") if any(d.startswith(p) for d in dynamic))
    for i in sorted(static):
        if i in ids:
            continue
        if any(i.startswith(p) for p in known_dynamic_prefixes):
            continue
        err(
            "animation code targets id '%s' but no element has it — the call "
            "silently no-ops; fix the id or drop the call" % i
        )
    # .rv hygiene: every reveal target should be marked .rv so it starts hidden
    revealed = set()
    for m in re.finditer(r"\breveal\(\s*\[([^\]]*)\]", js):
        for a, b in re.findall(r"'([^']+)'|\"([^\"]+)\"", m.group(1)):
            if a or b:
                revealed.add(a or b)
    for i in sorted(revealed & static):
        tag = enclosing_tag(html, i)
        if tag and not re.search(r'class="[^"]*\brv\b|class=\'[^\']*\brv\b', tag.group(0)):
            warn(
                "id '%s' is revealed via reveal() but its element lacks class .rv "
                "— it will be visible before its beat" % i
            )
    # bare .visible has no CSS rule of its own in this architecture — it only
    # takes effect on .rv elements (via .rv.visible). Flag addCls('visible')
    # targeting elements without .rv, which is a no-op on stage.
    for m in re.finditer(r"\baddCls\(\s*'([^']+)'\s*,\s*'visible'", js):
        i = m.group(1)
        if i.startswith("'") or i not in ids:
            continue
        tag = enclosing_tag(html, i)
        if tag and not re.search(r'class="[^"]*\brv\b|class=\'[^\']*\brv\b', tag.group(0)):
            warn(
                "addCls('%s','visible') targets an element without class .rv — "
                ".visible only takes effect via the .rv.visible rule, so this "
                "is a no-op; use .rv on the element or animate opacity directly" % i
            )


CHROME_RECEIVERS = (
    "document.body",
    "documentElement",
    "drawCanvas",
    "drawCtx",
    "dotsContainer",
    "sidebar",
    "querySelectorAll('.scene-dot')",
    'querySelectorAll(".scene-dot")',
    "querySelectorAll('.scene')",
    'querySelectorAll(".scene")',
    "querySelector('#topbar",
    'querySelector("#topbar',
)


def added_classes(js):
    """(class, match_end, context, via) for every class animation or chrome code can add."""
    out = []
    for m in re.finditer(r"\baddCls\(\s*'[^']+'\s*,\s*'([^']+)'", js):
        out.append((m.group(1), m.end(), js[max(0, m.start() - 200) : m.start()], "addCls"))
    for m in re.finditer(r"classList\.add\(\s*'([^']+)'\s*[,)]", js):
        out.append(
            (m.group(1), m.end(), js[max(0, m.start() - 200) : m.start()], "classList.add")
        )
    return out


def check_state_reset(js):
    anim_classes = js_array(js, "ANIM_CLASSES") or []
    reset = function_block(js, "resetScene") or ""
    cleared = set(re.findall(r"classList\.remove\(\s*'([^']+)'", reset))
    cleared |= set(re.findall(r"querySelectorAll\('\.([^'\s,.]+)", reset))
    cleared |= set(anim_classes)
    seen = set()
    for cls, end, ctx, via in added_classes(js):
        if (cls, ctx) in seen:
            continue
        seen.add((cls, ctx))
        if cls in ("active", "done"):
            continue  # engine chrome, rewritten by goToScene
        if any(r in ctx for r in CHROME_RECEIVERS):
            continue  # one-time chrome wiring or body-level mode, not scene state
        # self-cleaning chrome: removed by a nearby setTimeout (e.g. button flashes)
        after = js[end : end + 300]
        if "setTimeout" in after and ("remove" in after or cls in after):
            continue
        if cls not in cleared:
            err(
                "class '%s' is added by %s but never cleared — add it to "
                "ANIM_CLASSES or strip it in resetScene(), or state leaks "
                "when the presenter jumps backwards" % (cls, via)
            )


def check_dispatch(js, scenes):
    disp = function_block(js, "runSceneAnimation")
    if disp is None:
        err("runSceneAnimation() dispatcher not found")
        return
    cases = sorted({int(n) for n in re.findall(r"case\s+(\d+)\s*:", disp)})
    if not cases:
        warn("runSceneAnimation uses no case labels — cannot verify dispatch coverage")
        return
    n = len(scenes or [])
    missing = [i for i in range(n) if i not in cases]
    if missing:
        err(
            "runSceneAnimation has no case for scene index(es) %s — those scenes will be static"
            % ", ".join(map(str, missing))
        )
    extra = [c for c in cases if c >= n]
    if extra:
        err("runSceneAnimation has cases beyond the last scene index: %s" % ", ".join(map(str, extra)))
    for fn in re.findall(r"case\s+\d+\s*:\s*(\w+)\(\)", disp):
        if not re.search(r"function\s+%s\s*\(" % re.escape(fn), js):
            err("runSceneAnimation calls %s() which is not defined" % fn)


def check_single_file(html):
    for m in re.finditer(r'(?:src|href)\s*=\s*["\']([^"\']+)["\']', html):
        url = m.group(1)
        if url.startswith(("https://", "http://", "data:", "#", "mailto:")):
            if url.startswith("http://"):
                warn("insecure http reference: %s" % url)
            continue
        if url.startswith("font-family") or url.endswith((".woff", ".woff2")):
            continue
        err("external file reference breaks the single-file guarantee: %s" % url)


def check_js_syntax(html):
    js = script_body(html)
    if not js.strip():
        err("no <script> block found")
        return
    if not shutil.which("node"):
        warn("node not available — skipped JS syntax check")
        return
    with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8") as f:
        f.write(js)
        tmp = f.name
    try:
        r = subprocess.run(["node", "--check", tmp], capture_output=True, text=True, timeout=30)
        if r.returncode != 0:
            err("script block fails node --check:\n%s" % r.stderr.strip()[:800])
    finally:
        import os

        os.unlink(tmp)


def check_configmap(cm_path, html_path):
    try:
        import yaml
    except ImportError:
        warn("PyYAML not available — skipped ConfigMap check")
        return
    html = read(html_path)
    docs = list(yaml.safe_load_all(read(cm_path)))
    cm = next((d for d in docs if isinstance(d, dict) and d.get("kind") == "ConfigMap"), None)
    if cm is None:
        err("no ConfigMap document found in %s" % cm_path)
        return
    data = cm.get("data") or {}
    if "index.html" not in data:
        err("ConfigMap has no 'index.html' key (nginx serves the key name as the file name)")
        return
    embedded = data["index.html"]
    if embedded.strip() != html.strip():
        warn(
            "ConfigMap 'index.html' differs from %s (%d vs %d chars) — regenerate the ConfigMap"
            % (html_path, len(embedded), len(html))
        )
    else:
        print("  configmap: embedded HTML matches %s" % html_path)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("deck", help="path to the deck HTML file")
    ap.add_argument("--configmap", help="optional ConfigMap YAML wrapping the deck")
    args = ap.parse_args()

    html = read(args.deck)
    js = script_body(html)

    scenes, labels, agenda = check_registry(js)
    check_scene_dom(html, scenes)
    check_ids(html, js, scenes)
    check_state_reset(js)
    check_dispatch(js, scenes)
    check_single_file(html)
    check_js_syntax(html)
    if args.configmap:
        check_configmap(args.configmap, args.deck)

    n = len(scenes or [])
    print("deck: %s — %d scene(s), %d label(s)" % (args.deck, n, len(labels or [])))
    for e in ERRORS:
        print("ERROR:", e)
    for w in WARNINGS:
        print("WARN: ", w)
    if ERRORS:
        print("\nFAIL — %d error(s), %d warning(s)" % (len(ERRORS), len(WARNINGS)))
        sys.exit(1)
    if WARNINGS:
        print("\nPASS with warnings — %d warning(s)" % len(WARNINGS))
        sys.exit(2)
    print("\nPASS — all invariants hold")


if __name__ == "__main__":
    main()
