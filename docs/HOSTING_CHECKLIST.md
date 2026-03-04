# Hosting checklist — do these in order

Use this to get the backend hosted on Render and the eBay webhook working.

---

## Step 1: Put the project on GitHub

Render needs the code in a GitHub repo.

1. **Create a new repo on GitHub**  
   Go to [github.com/new](https://github.com/new). Name it e.g. `tcg-tool`. Don’t add a README (you already have code).

2. **In your project folder, run:**

   ```bash
   cd /Users/teddypiandes/Desktop/tcg-tool
   git init
   git add .
   git commit -m "Add TCG tool backend and Render blueprint"
   git branch -M main
   git remote add origin https://github.com/YOUR_USERNAME/tcg-tool.git
   git push -u origin main
   ```

   Replace `YOUR_USERNAME` with your GitHub username (and the repo name if you used something other than `tcg-tool`).

---

## Step 2: Deploy with Render Blueprint

1. Open **[render.com](https://render.com)** and sign in (e.g. with GitHub).

2. Click **New +** → **Blueprint**.

3. Connect the **tcg-tool** repo (or the one you pushed). Select it and continue.

4. Render will read `render.yaml` and show:
   - 1 database: **tcg-tool-db**
   - 1 web service: **tcg-tool-api**

5. Click **Apply** (or **Create resources**). Render will create the DB and the web service and start the first deploy.

6. Wait for the **web service** to finish deploying (logs will show “Your service is live at …”).

7. Note the **URL** of the web service, e.g. `https://tcg-tool-api.onrender.com` (the name might differ slightly).

---

## Step 3: Add environment variables on Render

1. In the Render **Dashboard**, open the **tcg-tool-api** web service.

2. Go to **Environment** (left sidebar).

3. Add these variables (use **Add Environment Variable**; mark secrets as **Secret** where possible):

   | Key | Value | Notes |
   |-----|--------|--------|
   | `EBAY_APP_ID` | Your Production App ID | From eBay Developer Portal → your app → Production. e.g. `Theodore-TCGTool-PRD-...` |
   | `EBAY_ACCOUNT_DELETION_TOKEN` | (from your local `.env`) | Same value as in `backend/.env` → `EBAY_ACCOUNT_DELETION_TOKEN` |
   | `EBAY_ACCOUNT_DELETION_ENDPOINT_URL` | `https://YOUR-RENDER-URL/api/webhooks/ebay/account-deletion` | Replace `YOUR-RENDER-URL` with your service URL, e.g. `tcg-tool-api.onrender.com` → `https://tcg-tool-api.onrender.com/api/webhooks/ebay/account-deletion` |

4. Click **Save Changes**. Render will redeploy with the new env vars.

---

## Step 4: Confirm the app is up

1. Open **https://YOUR-RENDER-URL/health** (e.g. `https://tcg-tool-api.onrender.com/health`).

2. You should see: `{"status":"ok"}`.

3. If the service was sleeping (free tier), the first load can take 30–60 seconds.

---

## Step 5: Register the webhook in the eBay Developer Portal

1. Go to **[eBay Developer Portal](https://developer.ebay.com/)** → your app → **Production** → **Alerts & Notifications** → **Marketplace Account Deletion**.

2. Set:
   - **Endpoint URL:** `https://YOUR-RENDER-URL/api/webhooks/ebay/account-deletion` (same as in Render).
   - **Verification token:** The same value as `EBAY_ACCOUNT_DELETION_TOKEN` (from your `.env` / Render).

3. Click **Save**.

4. Click **Send Test Notification**.  
   eBay will call your hosted URL. If it succeeds, your production keyset is re-enabled.

---

## Step 6: Run the ingest (optional, from your machine)

After the webhook test passes, you can run the eBay ingest locally (using the same Production App ID and DB if you point to it, or your local DB):

```bash
cd /Users/teddypiandes/Desktop/tcg-tool/backend
source venv/bin/activate
# Use production App ID in .env (EBAY_APP_ID, EBAY_SANDBOX=false)
python -m scripts.ingest_ebay_all_pokemon --max-pages 5
```

---

## Custom domain (e.g. api.cardalpha.com)

To use a project domain instead of `*.onrender.com`, see **[CUSTOM_DOMAIN_AND_NAMING.md](./CUSTOM_DOMAIN_AND_NAMING.md)** for name ideas and step-by-step: buy domain → add in Render Custom Domains → set CNAME at registrar → update `EBAY_ACCOUNT_DELETION_ENDPOINT_URL` and eBay portal.

---

## Quick reference

| Step | Action |
|------|--------|
| 1 | Create GitHub repo, then `git init`, `git add .`, `git commit`, `git remote add origin ...`, `git push` |
| 2 | Render → New + → Blueprint → connect repo → Apply |
| 3 | In Render: tcg-tool-api → Environment → add EBAY_APP_ID, EBAY_ACCOUNT_DELETION_TOKEN, EBAY_ACCOUNT_DELETION_ENDPOINT_URL |
| 4 | Open https://YOUR-RENDER-URL/health → expect `{"status":"ok"}` |
| 5 | eBay Portal → Marketplace Account Deletion → paste URL + token → Save → Send Test Notification |
| 6 | (Optional) Run ingest script locally |
| 7 | (Optional) Custom domain: see CUSTOM_DOMAIN_AND_NAMING.md |
