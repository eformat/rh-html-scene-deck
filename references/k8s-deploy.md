# K8s / OpenShift Deploy Pipeline

The deck is a single HTML file; serving it from Kubernetes/OpenShift means:
nginx-unprivileged + the deck in a ConfigMap, orchestrated with kustomize,
parameterized with envsubst.

## Pipeline

```
envsubst templates → build/ → kubectl apply -k build/ → rollout status
```

All assets live in `assets/deploy/`:

| File | Role |
|---|---|
| `deployment.template.yaml` | nginx-unprivileged:alpine, port 8080, tiny resources, ConfigMap mounted read-only at `/usr/share/nginx/html` |
| `kustomization.template.yaml` | `namespace` + `configMapGenerator` for the deck |
| `env.example` | Variables: `APP_NAME`, `NAMESPACE`, `CONFIGMAP_NAME`, `DECK_FILE` |
| `deploy.sh` | Renders templates via envsubst, copies the deck, applies, waits for rollout |

## Usage

```bash
cp assets/deploy/env.example assets/deploy/env.local   # edit values
assets/deploy/deploy.sh                                # or: deploy.sh path/to/env-file
```

`deploy.sh` then:

1. Sources the env file (`set -u` guards required variables)
2. Renders both templates with `envsubst '$APP_NAME $NAMESPACE $CONFIGMAP_NAME'`
   — substituting only the referenced variables, never the whole environment
3. Copies the deck HTML into `build/index.html`
4. `kubectl apply -k build/`
5. `kubectl -n $NAMESPACE rollout status deployment/$APP_NAME`

View it:

```bash
kubectl -n $NAMESPACE port-forward deploy/$APP_NAME 8080:8080
# open http://localhost:8080
# OpenShift: oc create route edge --service=$APP_NAME -n $NAMESPACE
```

## Why kustomize's configMapGenerator

The generator appends a **content hash** to the ConfigMap name
(`my-deck-html-2c2dcb5kgg`) and kustomize automatically rewrites the
Deployment's volume reference to the hashed name. Every deck change therefore
changes the ConfigMap name → the ReplicaSet updates → nginx picks up the new
deck with a rolling update. No manual restart, no stale HTML.

The generator's `files:` entry is `index.html=index.html` — the key **must**
be `index.html` because nginx serves the ConfigMap key as the file name.
`scripts/validate_deck.py` checks this if you validate with `--configmap`.

## The deployment shape

The template mirrors a typical deck deployment:

- `docker.io/nginxinc/nginx-unprivileged:alpine` — unprivileged user, works
  on OpenShift without SCC tweaks
- Container port **8080** (the image's listen port; don't change without a
  custom nginx.conf)
- Requests 50m/64Mi, limits 100m/128Mi — a static file needs almost nothing
- Volume `html` mounted read-only at `/usr/share/nginx/html`
- Optional: add the `kueue.x-k8s.io/queue-name` annotation to the pod
  template if the target cluster schedules via Kueue

## Standalone ConfigMap wrapper (alternative)

For sharing or one-off applies without kustomize, emit the single-document
wrapper the deck family ships with:

```bash
python3 scripts/make_configmap.py deck.html            # → <deck-stem>-html.yaml
kubectl apply -f deck-html.yaml
```

This produces a ConfigMap with the HTML embedded as a quoted string under
`data.index.html`. Verify the wrapper stays in sync with the deck file:

```bash
python3 scripts/validate_deck.py deck.html --configmap deck-html.yaml
```

A warning means the ConfigMap is stale — regenerate it. (Prefer the kustomize
pipeline for anything deployed; the wrapper is an interchange format.)
