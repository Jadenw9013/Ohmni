# Deploying the Ohmni demo

Two hosts, because the two halves have genuinely different shapes.

| Piece | Host | Why |
| --- | --- | --- |
| `apps/web` (static ES modules, no build step) | Vercel | Nothing to run; a CDN is the right answer. |
| `scripts/demo_server.py` | Fly.io | A long-lived HTTP server with in-memory job state, worker threads that run for minutes per design, a workspace lock, a persistent volume, and `kicad-cli` subprocesses. None of that fits a serverless function. |

The browser only ever talks to the Vercel origin. `vercel.json` rewrites
`/api/*` to the Fly app, so requests stay same-origin and the frontend needs no
CORS and no API base URL.

**The app name in `fly.toml` and the rewrite destination in `vercel.json` must
agree.** They are both `ohmni-demo` / `https://ohmni-demo.fly.dev` today. If you
take a different Fly app name, change the rewrite in the same commit — Vercel
rewrites cannot read environment variables, so this coupling is static.

## Backend, on Fly

```sh
fly launch --no-deploy --copy-config --name ohmni-demo
fly volumes create ohmni_data --size 1 --region sjc
fly secrets set ALLOWED_ORIGINS=https://<your-app>.vercel.app
fly secrets set ANTHROPIC_API_KEY=sk-ant-...        # optional, see below
fly deploy
```

Then confirm the two things that actually matter:

```sh
curl https://ohmni-demo.fly.dev/health                 # {"status":"ready",...}
fly ssh console -C "kicad-cli --version"               # 10.0.5
```

The second check is not ceremony. Ohmni refuses to publish a board that no
external checker saw: with no `kicad-cli`, `require_eda_check` turns an
UNAVAILABLE ERC into a failed job, and **every** design fails with
`eda_tool_failed`. That is why the image is built `FROM kicad/kicad:10.0.5`
rather than from a slim Python base, and why the version is pinned — ERC and
DRC verdicts are read out of KiCad's own JSON, so the checker version is part
of the result, and 10.0.5 is the version this repository's verdicts were
verified against.

`ALLOWED_ORIGINS` only restricts browsers that reach the Fly URL directly;
through the Vercel rewrite every request is same-origin. Leaving it unset
allows any origin, which is worth avoiding on a public URL.

### Running the same image locally

Worth doing before a deploy, because it exercises the parts a unit test cannot:
the volume handover, the privilege drop, and ERC and DRC against the KiCad in
the image rather than the one on your machine.

```sh
docker build -t ohmni-demo .
docker volume create ohmni_data
docker run --rm -p 8080:8080 -v ohmni_data:/data ohmni-demo
```

The image is ~2.7 GB, nearly all of it the KiCad base layer. Docker Desktop is
not required — a Docker inside WSL works, building from `/mnt/c/...`.

## Frontend, on Vercel

Import the repository and keep **Root Directory at the repository root** —
Vercel reads `vercel.json` from the root directory, and the rewrite lives
there. `outputDirectory: "apps/web"` is what makes the site serve from
`apps/web`; the page references `/styles.css` and `/app.js` at the origin root,
so serving any other directory yields a 404 page with no CSS.

- Framework preset: **Other**
- Build command: none (there is no root `package.json`; nothing is bundled)
- Output directory: comes from `vercel.json`

Verify after the first deploy:

```sh
curl -I  https://<your-app>.vercel.app/            # 200, text/html
curl -s  https://<your-app>.vercel.app/api/health  # proxied from Fly
```

If `/api/health` fails while the Fly URL answers directly, the rewrite and the
Fly app name have drifted apart.

## Deploy both halves together

The frontend validates the exact shape of every API response
(`apps/web/client-contract.js`). A Vercel deploy from one commit against a Fly
deploy from another can therefore fail closed with `api_ui_mismatch` even
though both halves are individually healthy. Ship them from the same commit.

## Model-proposed design (optional)

With no `ANTHROPIC_API_KEY` the server is the deterministic fixture demo and
nothing else — the free-text request shape is rejected exactly as it always
was, and the page shows no request box.

Setting the secret enables `AnthropicProvider`. Three things follow:

- `/api/health` reports `"free_text": true`, which is how the page knows it may
  offer an input at all. A server that cannot answer a request never shows one.
- `/api/brief` and `/api/demo` both accept `{"request": "...", ...identity}`
  alongside the fixture id, bounded to 10–2000 printable characters.
- The Describe stage shows a request box, and the Agree stage labels the
  resulting brief as a model proposal rather than an authored example.

The model proposes requirements, an architecture and a circuit. Every verdict
after that is still decided by the deterministic verifier, KiCad, the router and
the manufacturing profile, and placement stays inside the authored sensor-board
layout policy — a proposal outside it is refused, not placed by guesswork.

## Known limits of this deployment

- **Two concurrent designs.** `JobStore(max_active_jobs=2)`; a third request is
  refused with `job_start_unavailable` (503) rather than queued.
- **One machine, kept warm.** `min_machines_running = 1`: a cold start is a new
  process and therefore a new `server_instance_id`, which open browsers
  correctly treat as a stale generation and resolve with a reload. A stop would
  also kill any design running in a worker thread.
- **One volume, one region.** Job artifacts and the project database live on
  `ohmni_data`; a second machine would get its own empty volume.
- **A design takes minutes,** dominated by routing and DRC. The API is
  asynchronous (202 plus polling), so no single request runs long enough to hit
  a proxy timeout.
