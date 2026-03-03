# Hosting the backend for eBay deletion/closure compliance

To comply with eBay’s Marketplace Account Deletion requirement, your webhook must be reachable 24/7 at a public HTTPS URL. That means hosting the backend (not only running it locally with ngrok).

You need:

1. **A host** that runs your FastAPI app and gives you a stable HTTPS URL.
2. **A database** (Postgres) that the app can use. The webhook itself only needs env vars, but the app loads config and may use the DB at startup, so provide a `DATABASE_URL`.

**What’s in the repo:** The project includes deployment configs so you can host with minimal setup:

- **`render.yaml`** (repo root) — Render Blueprint: one-click deploy with Postgres + web service. Connect the repo in Render and add secrets when prompted.
- **`backend/Procfile`** — Used by Render (if not using the Blueprint) and Railway: `web: uvicorn ... --port $PORT`.
- **`backend/fly.toml`** — Fly.io app config; deploy with `fly deploy` from `backend/` after `fly launch` and setting secrets.
- **Database URL handling** — The app accepts `postgres://` or `postgresql://` from hosts and normalizes for SQLAlchemy.

---

## Option 1: Render — one-click with Blueprint (recommended)

The repo includes a **Blueprint** at the **repo root**: `render.yaml`. It defines a free Postgres database and a Python web service (`backend/`) with health check and the right start command.

1. Push your code to **GitHub**.
2. Go to [render.com](https://render.com) → **New +** → **Blueprint**.
3. Connect the repo that contains `tcg-tool` and select it. Render will detect `render.yaml`.
4. Click **Apply**. Render creates a Postgres database and the web service, and links `DATABASE_URL` automatically.
5. When prompted (or in **Dashboard** → your web service → **Environment**), add these as **secret** or **environment** variables:
   - `EBAY_APP_ID` — your Production App ID
   - `EBAY_ACCOUNT_DELETION_TOKEN` — same value as in your local `.env`
   - `EBAY_ACCOUNT_DELETION_ENDPOINT_URL` — `https://<your-service-name>.onrender.com/api/webhooks/ebay/account-deletion`  
     (Replace `<your-service-name>` with the name Render gives the web service, e.g. `tcg-tool-api`.)
6. After the first deploy, open `https://<your-service-name>.onrender.com/health` to confirm. Then in **eBay Developer Portal** → Marketplace Account Deletion, enter that endpoint URL and the same token → **Save** → **Send Test Notification**.

**Note:** On the free tier the service may spin down when idle; the webhook still works when eBay calls it. For always-on, use a paid plan.

---

## Option 1b: Render — manual Web Service (no Blueprint)

Render can run your backend from GitHub and give you a URL like `https://tcg-tool-api.onrender.com`. It has a free tier and optional Postgres.

### 1. Prepare the repo

- Push your code to GitHub (if you haven’t already).
- Ensure `backend/requirements.txt` and `backend/app/` are in the repo. You don’t need to change code.

### 2. Create a Web Service on Render

1. Go to [render.com](https://render.com) and sign in (e.g. with GitHub).
2. **Dashboard** → **New +** → **Web Service**.
3. Connect the repo that contains `tcg-tool` (or the backend).
4. Configure the service:
   - **Name:** e.g. `tcg-tool-api`
   - **Region:** pick one close to you
   - **Root Directory:** set to `backend` (so Render runs from the folder that has `app/` and `requirements.txt`)
   - **Runtime:** Python 3
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
     - Render sets `PORT` (often 10000). Using `$PORT` is required.
5. **Advanced** → add environment variables (see “Env vars” below).
6. Create the service. Render will build and deploy. Your URL will be like `https://tcg-tool-api.onrender.com`.

### 3. Database on Render

- **New +** → **PostgreSQL**. Create a database, then copy the **Internal Database URL** (or External if you’ll run ingest from your machine).
- In your Web Service → **Environment** → add:
  - `DATABASE_URL` = that Postgres URL (use the one Render shows for the DB, e.g. `postgresql://user:pass@host/dbname` — if it’s `postgres://`, change to `postgresql://` for SQLAlchemy).

### 4. Env vars on the Web Service

In the Web Service → **Environment**, set:

| Key | Value |
|-----|--------|
| `DATABASE_URL` | From Render Postgres (Internal URL) |
| `EBAY_APP_ID` | Your Production App ID |
| `EBAY_SANDBOX` | `false` |
| `EBAY_GLOBAL_ID` | `EBAY_US` |
| `EBAY_ACCOUNT_DELETION_TOKEN` | Same as in your local `.env` (the long random string) |
| `EBAY_ACCOUNT_DELETION_ENDPOINT_URL` | `https://YOUR-RENDER-URL.onrender.com/api/webhooks/ebay/account-deletion` |

Replace `YOUR-RENDER-URL` with your actual service URL (e.g. `tcg-tool-api` → `https://tcg-tool-api.onrender.com/api/webhooks/ebay/account-deletion`).

### 5. After deploy

- Open `https://YOUR-RENDER-URL.onrender.com/health` — you should see `{"status":"ok"}`.
- In eBay Developer Portal → **Alerts & Notifications** → **Marketplace Account Deletion**, set:
  - **Endpoint URL:** `https://YOUR-RENDER-URL.onrender.com/api/webhooks/ebay/account-deletion`
  - **Verification token:** same as `EBAY_ACCOUNT_DELETION_TOKEN`
- Save, then **Send Test Notification**. Your production keyset will re-enable when the test succeeds.

**Note:** On the free tier, the service may spin down after inactivity; the first request after that can be slow. The webhook will still work when eBay calls it (eBay’s retries help). For always-on, use a paid plan.

---

## Option 2: Railway

Railway runs apps from GitHub and provides Postgres and a public URL.

1. Go to [railway.app](https://railway.app), sign in with GitHub.
2. **New Project** → **Deploy from GitHub repo** → select your repo.
3. Set **Root Directory** to `backend` (or the directory that contains `app` and `requirements.txt`).
4. Railway will detect Python. Set **Start Command** to: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
5. Add a **Postgres** plugin to the project; Railway will set `DATABASE_URL` automatically.
6. In your backend service, **Variables** → add the same env vars as in the table above. Set `EBAY_ACCOUNT_DELETION_ENDPOINT_URL` to `https://YOUR-RAILWAY-URL/api/webhooks/ebay/account-deletion` (Railway gives you a public URL in the service settings; you can add a custom domain later).
7. Deploy. Then in the eBay portal, use that URL and your token, Save, and Send Test Notification.

---

## Option 3: Fly.io (Docker)

The repo has `backend/Dockerfile` and `backend/fly.toml` (app name `tcg-tool-api`, health check on `/health`). You can change the app name when you run `fly launch`.

1. Install [flyctl](https://fly.io/docs/hacks/install-flyctl/) and run `fly auth login`.
2. From the **backend** directory: `fly launch` (use the existing `fly.toml` or let Fly create one). Choose app name and region if prompted.
3. Add Postgres: `fly postgres create`, then `fly postgres attach <postgres-app-name>` (or set `DATABASE_URL` with `fly secrets set DATABASE_URL=...`).
4. Set secrets:  
   `fly secrets set EBAY_APP_ID=... EBAY_ACCOUNT_DELETION_TOKEN=... EBAY_ACCOUNT_DELETION_ENDPOINT_URL=https://YOUR-APP.fly.dev/api/webhooks/ebay/account-deletion`  
   (and `DATABASE_URL` if not attached). `EBAY_SANDBOX` and `EBAY_GLOBAL_ID` are in `fly.toml` already.
5. Deploy: `fly deploy`. Your URL will be `https://YOUR-APP.fly.dev`.
6. In the eBay portal, set the endpoint URL to `https://YOUR-APP.fly.dev/api/webhooks/ebay/account-deletion`, same token, Save, Send Test Notification.

---

## Summary

| Step | What to do |
|------|------------|
| 1 | Pick a host (Render / Railway / Fly.io) and deploy the backend from `backend/` with Postgres. |
| 2 | Set env vars on the host, including `EBAY_ACCOUNT_DELETION_ENDPOINT_URL` = **your hosted base URL** + `/api/webhooks/ebay/account-deletion`. |
| 3 | In eBay Developer Portal → Marketplace Account Deletion, enter that URL and your verification token → Save → **Send Test Notification**. |
| 4 | After success, your production keyset is re-enabled and you comply with deletion/closure notifications as long as the endpoint stays live. |

The webhook endpoint (`/api/webhooks/ebay/account-deletion`) only needs the env vars; it doesn’t need to store data. Keeping the backend hosted and the URL registered in the portal is what satisfies eBay’s requirement.
