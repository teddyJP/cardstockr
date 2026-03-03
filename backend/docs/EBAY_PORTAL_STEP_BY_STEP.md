# eBay Developer Portal: set up Marketplace Account Deletion (step-by-step)

Do this **after** your backend is running and reachable at a public HTTPS URL (e.g. via ngrok), and after you’ve set `EBAY_APP_ID`, `EBAY_ACCOUNT_DELETION_TOKEN`, and `EBAY_ACCOUNT_DELETION_ENDPOINT_URL` in `backend/.env`.

To get the exact **Endpoint URL** and **Verification token** to paste below, run:

```bash
cd backend && source venv/bin/activate && python -m scripts.check_ebay_webhook_setup
```

---

## Step 1: Open the Developer Portal

1. Go to **https://developer.ebay.com/**
2. Log in with your eBay developer account.
3. In the top navigation, open **My Account** (or **Dashboard**) and make sure you’re in the right account.

---

## Step 2: Open your app

1. Go to **My Account** → **Application Keys** (or **Applications** / **API Keys** — the exact label can vary).
2. Find and click the app you use for this project (e.g. the one whose Production App ID you put in `EBAY_APP_ID`).
3. You should see **Sandbox** and **Production** keys/tabs for that app.

---

## Step 3: Switch to Production

1. Make sure you’re on the **Production** view for this app (not Sandbox).
2. If there’s a toggle or tab for **Sandbox** vs **Production**, select **Production**.

---

## Step 4: Open Alerts & Notifications

1. On the app’s page, look for a section or link named **Alerts & Notifications** (sometimes under **Production** or **Keyset**).
2. Click **Alerts & Notifications** to open it.

---

## Step 5: Find Marketplace Account Deletion

1. Inside Alerts & Notifications, find the **Marketplace Account Deletion** (or **Account Deletion**) subsection.
2. You should see:
   - A field for **Endpoint URL** (or **Notification endpoint** / **URL**).
   - A field for **Verification token** (or **Verification Token**).

---

## Step 6: Enter the Endpoint URL

1. In **Endpoint URL**, paste the **exact** URL you use in `.env` as `EBAY_ACCOUNT_DELETION_ENDPOINT_URL`.
   - Example: `https://abc123.ngrok-free.app/api/webhooks/ebay/account-deletion`
2. Do not add a trailing slash. Use `https://` (not `http://`).
3. This must be the full URL to your webhook (the same one your backend is configured with).

---

## Step 7: Enter the Verification token

1. In **Verification token**, paste the **exact** value of `EBAY_ACCOUNT_DELETION_TOKEN` from your `backend/.env`.
2. Copy it exactly — no extra spaces or line breaks. It’s the long random string (e.g. 64 characters) you generated with `scripts/generate_ebay_webhook_token.py` or set manually.

---

## Step 8: Save

1. Click **Save** (or **Submit** / **Update**) for the Marketplace Account Deletion section.
2. Wait until the page confirms that your settings were saved.

---

## Step 9: Send Test Notification (this re-enables your keyset)

1. In the same **Marketplace Account Deletion** area, find the button **Send Test Notification** (or **Test** / **Verify**).
2. Click **Send Test Notification**.
3. eBay will send a POST request to your endpoint with a `challengeCode`. Your backend responds with `challengeResponse`; eBay checks it.
4. **Success:** The portal should show a success message, and your production keyset will be re-enabled (often within a short time). You can then use your Production App ID for API calls.
5. **Failure:** Check that:
   - Your backend is running.
   - The endpoint is reachable from the internet (e.g. ngrok is running and the URL in the portal matches your ngrok URL).
   - The verification token in the portal matches `EBAY_ACCOUNT_DELETION_TOKEN` in `.env` exactly.
   - `EBAY_ACCOUNT_DELETION_ENDPOINT_URL` in `.env` matches the URL you entered in the portal.

---

## Step 10: Confirm production access

1. After a successful test, go back to your app’s **Production** keyset / credentials view.
2. The keyset that was previously “disabled” should now show as active/enabled.
3. Use the same **App ID (Client ID)** in `EBAY_APP_ID` for production requests (e.g. `scripts/ingest_ebay_all_pokemon.py` with `EBAY_SANDBOX=false`).

---

## Quick checklist

- [ ] Logged into developer.ebay.com
- [ ] Opened the correct app → **Production**
- [ ] Opened **Alerts & Notifications** → **Marketplace Account Deletion**
- [ ] Pasted **Endpoint URL** (same as `EBAY_ACCOUNT_DELETION_ENDPOINT_URL`)
- [ ] Pasted **Verification token** (same as `EBAY_ACCOUNT_DELETION_TOKEN`)
- [ ] Clicked **Save**
- [ ] Clicked **Send Test Notification**
- [ ] Saw success → production keyset re-enabled
