# Next steps: eBay production webhook & ingest

Use this checklist to re-enable your production keyset and run the eBay ingest.

---

## Why your production keyset is disabled

You **already have** a production keyset (App ID). eBay disables it until you comply with **Marketplace Account Deletion**: they require apps that use production APIs to either subscribe to account-deletion notifications or opt out (if you don’t store user data). Subscribing means:

1. Registering a **webhook endpoint URL** (HTTPS) where eBay can send a verification challenge.
2. Your server responding correctly to that challenge so eBay can confirm you control the URL.
3. After that, eBay **re-enables your production keyset** — you don’t request a new one; the same App ID starts working again.

This app implements the webhook; you only need to expose it and complete the steps below.

### Do I need to host the backend?

**Yes, for ongoing compliance.** eBay must be able to reach your endpoint whenever they send account deletion/closure notifications — not only during the one-time verification test. So:

- **ngrok** is fine to **pass the test** and get your keyset re-enabled (endpoint is reachable while ngrok and your app are running).
- **For real compliance**, the webhook should be **hosted** (deployed) so the URL is always available. If the endpoint is down or only up when you run ngrok, eBay can’t deliver notifications and you may fall out of compliance.

**Recommendation:** Use ngrok to unblock your keyset, then deploy the backend and update the portal + `EBAY_ACCOUNT_DELETION_ENDPOINT_URL` to the deployed URL so the webhook is always live.

---

## 1. Get your Production App ID

1. Go to [eBay Developer Portal](https://developer.ebay.com/) → your app → **Production**.
2. Copy the **App ID (Client ID)** (e.g. `Theodore-TCGTool-PRD-xxxxxxxx`).
3. In `backend/.env`, set:
   ```env
   EBAY_APP_ID=Theodore-TCGTool-PRD-xxxxxxxx
   ```
   (Use your actual App ID.)

---

## 2. Expose the backend on public HTTPS

The webhook must be reachable at a public HTTPS URL. Two options:

### Option A: Quick test with ngrok (recommended first)

1. Start the backend (in one terminal):
   ```bash
   cd backend && source venv/bin/activate && uvicorn app.main:app --host 127.0.0.1 --port 8000
   ```
2. In another terminal, run:
   ```bash
   ngrok http 8000
   ```
3. Copy the **HTTPS** URL ngrok shows (e.g. `https://abc123.ngrok-free.app`).
4. In `backend/.env`, set:
   ```env
   EBAY_ACCOUNT_DELETION_ENDPOINT_URL=https://YOUR_NGROK_URL/api/webhooks/ebay/account-deletion
   ```
   Example: `https://abc123.ngrok-free.app/api/webhooks/ebay/account-deletion`.

**Note:** The ngrok URL changes each time you restart ngrok (on the free tier). Use ngrok to pass the test; for **ongoing compliance** you should deploy (Option B) and point the portal to your hosted URL.

### Option B: Deploy the backend (required for ongoing compliance)

Deploy the FastAPI app so the webhook is always reachable. Use e.g. Render, Fly.io, or Railway. Set:

```env
EBAY_ACCOUNT_DELETION_ENDPOINT_URL=https://YOUR_DEPLOYED_HOST/api/webhooks/ebay/account-deletion
```

---

## 3. Confirm env and get portal values

From `backend/` run:

```bash
source venv/bin/activate && python -m scripts.check_ebay_webhook_setup
```

This script checks that `EBAY_APP_ID`, `EBAY_ACCOUNT_DELETION_TOKEN`, and `EBAY_ACCOUNT_DELETION_ENDPOINT_URL` are set, and prints the **exact** values to enter in the eBay Developer Portal.

---

## 4. Configure eBay Developer Portal

**→ Full click-by-click guide:** [EBAY_PORTAL_STEP_BY_STEP.md](./EBAY_PORTAL_STEP_BY_STEP.md)

Short version: go to [eBay Developer Portal](https://developer.ebay.com/) → your app → **Production** → **Alerts & Notifications** → **Marketplace Account Deletion**. Enter the same **Endpoint URL** as `EBAY_ACCOUNT_DELETION_ENDPOINT_URL` and the same **Verification token** as `EBAY_ACCOUNT_DELETION_TOKEN`, then **Save**.

---

## 5. Send test notification (this re-enables your keyset)

In the same **Marketplace Account Deletion** section, click **Send Test Notification**.

- eBay sends a challenge to your endpoint; this app responds with the correct `challengeResponse`. When eBay accepts it, they **re-enable your production keyset** automatically — no support ticket or extra step.
- If the test succeeds, you can start using the same Production App ID for API calls (e.g. the ingest script).
- If it fails: ensure the backend is running, the URL is HTTPS and reachable from the internet, and the token matches exactly. Check that your tunnel (ngrok) or deployment is up.

---

## 6. Run the eBay ingest

After the test succeeds:

```bash
cd backend && source venv/bin/activate && python -m scripts.ingest_ebay_all_pokemon --max-pages 5
```

Increase `--max-pages` as needed. For a full backfill you can use a higher number or omit it (check the script for defaults).

---

## 7. (Optional) Backfill sets and cards

To populate canonical sets/cards and variants for the UI:

```bash
cd backend && source venv/bin/activate && python -m scripts.backfill_sets_and_cards
```

(Run this after ingest has loaded some sales.)

---

## Quick reference

| Step | What to set / do |
|------|------------------|
| 1 | `EBAY_APP_ID` in `.env` = Production App ID from portal |
| 2 | Expose backend (ngrok or deploy), set `EBAY_ACCOUNT_DELETION_ENDPOINT_URL` in `.env` |
| 3 | Run `python -m scripts.check_ebay_webhook_setup` to confirm and get portal values |
| 4 | In portal: Marketplace Account Deletion → endpoint URL + verification token → Save |
| 5 | Send Test Notification in portal |
| 6 | Run `python -m scripts.ingest_ebay_all_pokemon --max-pages 5` |
