# eBay Marketplace Account Deletion Webhook

Your production API keyset requires a registered **Marketplace Account Deletion** endpoint. This app implements that webhook so you can re-enable the keyset.

**To comply with deletion/closure notifications**, the endpoint must be **hosted** (deployed) so eBay can reach it whenever they send notifications — not only during the one-time test. Using ngrok is fine to pass the test; for ongoing compliance, deploy the backend and register the deployed URL in the portal.

**→ Step-by-step checklist:** [NEXT_STEPS_EBAY_PRODUCTION.md](./NEXT_STEPS_EBAY_PRODUCTION.md)

## What’s in the repo

- **Endpoint:** `POST /api/webhooks/ebay/account-deletion`
- **Config (env):**
  - `EBAY_ACCOUNT_DELETION_TOKEN` – verification token (32–80 chars, random string you choose).
  - `EBAY_ACCOUNT_DELETION_ENDPOINT_URL` – **exact** full HTTPS URL of this endpoint (e.g. `https://your-api.com/api/webhooks/ebay/account-deletion`).

## Steps to get production access

### 1. Deploy the backend to a public HTTPS host

The endpoint must be reachable on the public internet (not localhost). Deploy this FastAPI app to e.g.:

- Render
- Fly.io
- Railway
- Vercel (with an ASGI server)
- AWS (Lambda + API Gateway or ECS)

After deployment you’ll have a base URL, e.g. `https://tcg-tool-api.fly.dev`.

### 2. Set environment variables on the deployed app

In your host’s env config, set:

```env
EBAY_ACCOUNT_DELETION_TOKEN=<generate-a-random-32-to-80-char-string>
EBAY_ACCOUNT_DELETION_ENDPOINT_URL=https://<your-deployed-host>/api/webhooks/ebay/account-deletion
```

Example: if your app is at `https://tcg-tool-api.fly.dev`, then:

```env
EBAY_ACCOUNT_DELETION_ENDPOINT_URL=https://tcg-tool-api.fly.dev/api/webhooks/ebay/account-deletion
```

`EBAY_ACCOUNT_DELETION_TOKEN` must be the same value you’ll enter in the eBay Developer Portal.

### 3. Configure the endpoint in the eBay Developer Portal

1. Open your app → **Production** → **Alerts & Notifications**.
2. Under **Marketplace Account Deletion**:
   - **Endpoint:** `https://<your-deployed-host>/api/webhooks/ebay/account-deletion` (same as `EBAY_ACCOUNT_DELETION_ENDPOINT_URL`).
   - **Verification token:** the same value as `EBAY_ACCOUNT_DELETION_TOKEN`.
3. Save.

### 4. Send test notification

In the portal, click **Send Test Notification**. eBay will POST a challenge to your endpoint; the app responds with `challengeResponse` and the keyset is validated. If the test succeeds, the production keyset is typically re-enabled shortly after.

### 5. (Optional) Test locally with ngrok

To test before deploying:

1. Run the backend: `uvicorn app.main:app --reload`.
2. Run ngrok: `ngrok http 8000`.
3. Use the ngrok HTTPS URL as `EBAY_ACCOUNT_DELETION_ENDPOINT_URL` (e.g. `https://abc123.ngrok.io/api/webhooks/ebay/account-deletion`) and set the same token in the portal, then Send Test Notification.  
   Note: the URL changes when ngrok restarts; for a permanent fix you still need a real deployment.
