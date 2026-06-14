# Deploy — tax API (Hostinger KVM) + frontend (Netlify)

Backend runs as a Docker container on the shared VPS (`69.62.110.81`, user `dev`), reverse-proxied
by the **existing host Caddy** with auto-TLS. Frontend is on **Netlify**. Deploys are git-build over
SSH, mirroring `ai_booking`: push to `main` → GitHub Actions SSHes in → the VPS `git pull`s and
rebuilds the container.

## Already done
- DNS: `tax-api.portfolio-plus.com` → `69.62.110.81` (GoDaddy A record).
- Firestore `recipts-ai`: deny-all rules + 4 composite indexes deployed; Cloudinary PDF/ZIP delivery enabled.

---

## One-time setup

> Order matters: **push `main` to GitHub first** (so the repo isn't empty), then do the VPS steps.

### 0. Push the repo (local machine)
```bash
brew install gh && gh auth login            # interactive
git push -u origin main
```
Confirm CI goes green in the repo's Actions tab.

### 1. Caddy vhost (on the VPS)
Append to `/etc/caddy/Caddyfile`:
```
tax-api.portfolio-plus.com {
    reverse_proxy localhost:8001
}
```
```bash
sudo systemctl reload caddy
```
(Caddy auto-issues the Let's Encrypt cert on the first HTTPS hit — same as `worker`.)

### 2. Deploy key + clone the repo (on the VPS)
A **read-only deploy key** lets the box `git fetch` the private repo:
```bash
ssh-keygen -t ed25519 -f ~/.ssh/ai-cpa-deploy -N "" -C "ai-cpa-deploy"
cat ~/.ssh/ai-cpa-deploy.pub
```
Add that public key in GitHub → repo **`tamirSida/ai-cpa`** → Settings → **Deploy keys** → Add (leave "Allow write access" **off**). Then map it to a host alias in `~/.ssh/config`:
```
Host github-ai-cpa
    HostName github.com
    User git
    IdentityFile ~/.ssh/ai-cpa-deploy
    IdentitiesOnly yes
```
Clone via the alias (so `origin` uses the deploy key — the deploy workflow does `git fetch origin main`):
```bash
mkdir -p /home/dev/apps && cd /home/dev/apps
git clone git@github-ai-cpa:tamirSida/ai-cpa.git ai-cpa
```

### 3. Prod `.env` (on the VPS) — `/home/dev/apps/ai-cpa/backend/.env`
Gitignored, so create it by hand. Same as your local `backend/.env` except `CORS_ORIGINS` (the Netlify URL) and `ENV=prod`:
```
FIREBASE_PROJECT_ID=recipts-ai
GOOGLE_APPLICATION_CREDENTIALS=secrets/firebase-sa.json
OPENAI_API_KEY=sk-...
OPENAI_COMMAND_MODEL=gpt-4.1-mini
OPENAI_VISION_MODEL=gpt-4.1-mini
CLOUDINARY_URL=cloudinary://...
CORS_ORIGINS=["https://<your-site>.netlify.app"]
ANNUAL_LIMIT_ILS=122833
ENV=prod
RECEIPT_SIGNING_P12_PATH=secrets/receipt-signing.p12
RECEIPT_SIGNING_P12_PASSWORD=<your signing password>
```

### 4. Secrets (on the VPS) — `/home/dev/apps/ai-cpa/backend/secrets/`
scp from your local machine over Tailscale (reuse your existing local cert + password, or regenerate):
```bash
scp backend/secrets/firebase-sa.json backend/secrets/receipt-signing.p12 \
    dev@<tailscale-host>:/home/dev/apps/ai-cpa/backend/secrets/
# then on the VPS:
chmod 600 /home/dev/apps/ai-cpa/backend/secrets/*
```

### 5. GitHub repo secrets (tax repo → Settings → Secrets and variables → Actions)
The runner→VPS SSH key (NOT the deploy key from step 2 — different key):
- `VPS_HOST` = `69.62.110.81`
- `VPS_USER` = `dev`
- `VPS_SSH_KEY` = the **private** key whose public half is in the VPS `~/.ssh/authorized_keys` (the same key `ai_booking`'s deploy uses).

### 6. Netlify (frontend)
- New site from `tamirSida/ai-cpa`, **base directory `frontend`**. `frontend/netlify.toml` (committed)
  already pins Node 22, the build command, and an `ignore` rule that **skips the build on backend-only
  commits** — you only set the base directory + env vars in the UI.
- Env vars: the four `NEXT_PUBLIC_FIREBASE_*` (the `recipts-ai` web config) + `NEXT_PUBLIC_API_BASE_URL=https://tax-api.portfolio-plus.com/api`.
- Deploy → note the site URL → put it in `CORS_ORIGINS` in the VPS `.env` (step 3) and in **Firebase Console → Authentication → Settings → Authorized domains**.

---

## First deploy + verify
Deploy is **gated on CI**: `deploy.yml` runs automatically only after the **"CI" workflow succeeds on
`main`**, and only when the backend changed in that commit. For the **first** deploy, trigger it
manually (the `workflow_run` trigger won't fire until the deploy workflow already exists on `main`):
> Actions tab → **"Deploy API to VPS"** → **Run workflow**.

Then verify:
```bash
curl -i https://tax-api.portfolio-plus.com/healthz     # → 200 over valid TLS (liveness)
curl -i https://tax-api.portfolio-plus.com/readyz      # → 200 (the container can reach Firestore)
```
Then open the Netlify site → Google sign-in → onboarding → issue a receipt. Two checks:
- A bank-transfer receipt PDF shows «מסמך ממוחשב חתום דיגיטלית»; a cash one shows the hand-sign note.
- `docker compose -f docker-compose.prod.yml ps api` on the VPS shows `healthy`.

## Ongoing
Push to `main` → **CI** runs (tests + FE build). If green, the **API redeploys only when `backend/**`
(or the compose/deploy workflow) changed**, and **Netlify rebuilds only when `frontend/**` changed** —
each side ignores the other's commits. A red CI never deploys. First VPS image build is slow
(WeasyPrint apt+pip); later builds use cached layers.

## Notes
- Two distinct keys: **VPS_SSH_KEY** (runner → VPS) and the read-only **deploy key** (VPS → GitHub). Don't mix them up.
- The backend-change gate compares the latest commit (`HEAD^..HEAD`); single-commit pushes (the usual case) are exact. Use the manual **Run workflow** to force a deploy regardless.
