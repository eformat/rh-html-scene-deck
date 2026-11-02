#!/usr/bin/env python3
"""make_configmap.py — wrap a deck HTML file in a standalone ConfigMap YAML.

Produces the single-document wrapper the deck family ships with:
the HTML embedded as a quoted string
under data.index.html, so `oc apply -f` serves it from any nginx pod
mounting the ConfigMap. For deployments, prefer the kustomize pipeline
in assets/deploy — this wrapper is for sharing or one-off applies.

Usage:
  make_configmap.py deck.html [out.yaml] [--name my-deck-html]
"""
import argparse
import sys

try:
    import yaml
except ImportError:
    sys.exit("PyYAML required: pip install pyyaml")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("deck", help="path to the deck HTML file")
    ap.add_argument("out", nargs="?", help="output YAML path (default: <deck-stem>-html.yaml)")
    ap.add_argument("--name", default=None, help="ConfigMap name (default: <deck-stem>-html)")
    args = ap.parse_args()

    stem = args.deck.rsplit("/", 1)[-1]
    if stem.endswith(".html"):
        stem = stem[: -len(".html")]
    cm_name = args.name or (stem + "-html")
    out_path = args.out or (cm_name + ".yaml")

    with open(args.deck, encoding="utf-8") as f:
        html = f.read()

    doc = {
        "apiVersion": "v1",
        "kind": "ConfigMap",
        "metadata": {"name": cm_name},
        "data": {"index.html": html},
    }
    with open(out_path, "w", encoding="utf-8") as f:
        yaml.safe_dump(doc, f, default_flow_style=False, width=10**6, sort_keys=False)

    print("wrote %s (ConfigMap %s, %d chars of HTML)" % (out_path, cm_name, len(html)))
    print("apply with: kubectl apply -f %s" % out_path)


if __name__ == "__main__":
    main()
