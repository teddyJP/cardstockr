# Set up cardstockr.com (step-by-step)

Do these in order after purchasing **cardstockr.com**. You need the backend already deployed on Render (e.g. **tcg-tool-api**). If not, complete [HOSTING_CHECKLIST.md](./HOSTING_CHECKLIST.md) first.

---

## Copy-paste reference

| Where | What to enter |
|-------|----------------|
| **Render → Custom Domains** | `api.cardstockr.com` |
| **Namecheap → CNAME Host** | `api` |
| **Namecheap → CNAME Value** | *(paste the CNAME target Render shows, e.g. `tcg-tool-api.onrender.com`)* |
| **Render → EBAY_ACCOUNT_DELETION_ENDPOINT_URL** | `https://api.cardstockr.com/api/webhooks/ebay/account-deletion` |
| **eBay Portal → Endpoint URL** | `https://api.cardstockr.com/api/webhooks/ebay/account-deletion` |
| **Check when live** | https://api.cardstockr.com/health |

---

## Step 1: Add custom domain in Render

1. Go to **[dashboard.render.com](https://dashboard.render.com)** and sign in.
2. Open your **web service** (e.g. **tcg-tool-api**).
3. In the left sidebar, click **Settings**.
4. Scroll to **Custom Domains**.
5. Click **Add Custom Domain**.
6. Enter: **api.cardstockr.com**
7. Click **Save**. Render will show a **CNAME target**, e.g.:
   - `tcg-tool-api.onrender.com`  
   (or similar — copy the exact value Render shows.)
8. **Copy that CNAME target** — you’ll use it in Step 2.

---

## Step 2: Add CNAME in your domain registrar (Namecheap or other)

### If you use Namecheap

1. Go to **[namecheap.com](https://www.namecheap.com)** → **Domain List** → click **cardstockr.com**.
2. Click **Manage** (or **Advanced DNS**).
3. Under **HOST RECORDS** / **DNS Records**, click **Add New Record**.
4. Choose **CNAME Record**:
   - **Host:** `api` (only the subdomain part).
   - **Value:** paste the CNAME target from Step 1 (e.g. `tcg-tool-api.onrender.com`).
   - **TTL:** Automatic (or 300).
5. Save. If there’s an existing record for `api` (e.g. URL Redirect), remove or disable it so the CNAME is the only one.

### If you use another registrar (Cloudflare, Google Domains, Porkbun, etc.)

- Add a **CNAME** record: **Host** = `api`, **Target/Value** = the Render CNAME from Step 1. Save.

---

## Step 3: Wait for DNS and SSL

- DNS can take from a few minutes up to 48 hours (often 5–15 minutes).
- Render will automatically issue an SSL certificate once the CNAME is visible.
- Check: open **https://api.cardstockr.com/health** in your browser. When it returns `{"status":"ok"}`, you’re done with DNS/SSL.

---

## Step 4: Update Render environment variables

1. In **Render** → your web service → **Environment** (left sidebar).
2. Find **EBAY_ACCOUNT_DELETION_ENDPOINT_URL**.
3. Set its value to: **https://api.cardstockr.com/api/webhooks/ebay/account-deletion**
4. Save. Render will redeploy (or you can trigger a deploy).

---

## Step 5: Update eBay Developer Portal

1. Go to **[eBay Developer Portal](https://developer.ebay.com/)** → your app → **Production** → **Alerts & Notifications** → **Marketplace Account Deletion**.
2. **Endpoint URL:** change to **https://api.cardstockr.com/api/webhooks/ebay/account-deletion**
3. **Verification token:** leave unchanged (same as in Render).
4. Click **Save**.
5. Click **Send Test Notification**. When it succeeds, eBay will use the new URL and your production keyset stays in compliance.

---

## Done

- Backend (and eBay webhook) is live at **https://api.cardstockr.com**
- **cardstockr.com** (root) is free for your main site or app later.

If anything doesn’t match (e.g. your Render service has a different name), use the CNAME target and URLs Render and your registrar show.
