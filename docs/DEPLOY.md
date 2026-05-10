# Deploy — Hugging Face Spaces (Docker SDK)

Single Space serving FastAPI + the Vite-built React frontend behind one URL.

## How it's wired

- **`Dockerfile`** — multi-stage. Node 20 builds `frontend/dist/`; Python 3.12 installs deps via `uv` and copies the built frontend in.
- **`README.md` frontmatter** — declares `sdk: docker` and `app_port: 7860`. The frontmatter is what makes the repo a valid Space.
- **`app/main.py`** — mounts `frontend/dist/` at `/` after the API routers, with an SPA fallback so client-side routes resolve.
- **`AUTO_INGEST_ON_STARTUP=true`** — set by the Dockerfile. Lifespan auto-runs `ingest_corpus` if the passages table is empty (Spaces' free-tier filesystem is ephemeral, so the DB is wiped on every cold start).

## One-time setup

1. Create the Space at <https://huggingface.co/new-space>:
   - **SDK**: Docker
   - **Hardware**: CPU basic (free)
   - **Name**: e.g. `decade-ai-challenge`
2. Add Space secrets (Settings → Variables and secrets → New secret):
   - `OPENAI_API_KEY` — your key
   - `CHAT_ACCESS_TOKEN` — long random string; users paste this into the frontend gate
   - `ADMIN_TOKEN` — different long random string; for `/api/admin/*`
3. Set an OpenAI usage hard cap on platform.openai.com before sharing the URL.

## Deploying

The Space is its own git remote. Push the repo to it:

```sh
git remote add space https://huggingface.co/spaces/<user>/decade-ai-challenge
git push space main
```

HF builds the Docker image and starts the container. First build is ~5-8 min (npm install + uv sync); subsequent builds are faster thanks to layer caching. Watch the build log in the Space's "Logs" tab.

## After deploy

- Hit `https://<user>-decade-ai-challenge.hf.space/api/health` — should return `{"status":"ok"}`.
- Visit the root URL — the React app loads, `AccessGate` prompts for `CHAT_ACCESS_TOKEN`.
- The corpus auto-ingests on first boot. To force a re-ingest after editing `convictions/`:

  ```sh
  curl -X POST https://<user>-decade-ai-challenge.hf.space/api/admin/ingest \
    -H "X-Admin-Token: $ADMIN_TOKEN"
  ```

## Cost

- Space: $0/mo (free tier).
- OpenAI: per-call, billed separately. Cap usage on platform.openai.com.

## Cold starts

The free tier sleeps after ~48h of inactivity. First request after sleep takes ~30-60s (container boot + lifespan: migrate → empty-DB ingest → BM25 build). Subsequent requests are instant.
