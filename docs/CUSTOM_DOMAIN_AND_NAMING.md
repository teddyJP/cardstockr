# Custom domain and naming ideas

Use a project-focused domain (e.g. for the API and later the app) and connect it to your Render deployment.

**Example:** **cardstockr.com** — “cardstock” is the paper trading cards are printed on; the “r” gives it a modern product feel. Brandable and fits TCG.

---

## Domain name ideas

Here are some options that fit a TCG/collectibles pricing and market-data product (PriceCharting-style, fair value, trends):

| Name | Rationale |
|------|-----------|
| **cardalpha.com** | “Alpha” = edge in investing; suggests data-driven, smart card decisions. Short and memorable. |
| **cardpulse.com** | Live market pulse, real-time feel. Good if you emphasize current prices and activity. |
| **cardscope.com** | Scope into the market—research, visibility. |
| **tcgvault.com** | Vault of TCG data; trust and depth. |
| **cardlens.com** | Lens on the market—clarity and insight. |
| **faircard.com** | Direct “fair value” angle; might be taken. |
| **cardindex.io** | Index of cards/prices; data/product feel. |
| **deckvalue.com** | Straightforward “value your deck” message. |

**Recommendation:** **cardalpha.com** is strong—short, professional, and the “alpha” angle fits a tool that helps people make better card decisions. Check availability at [namecheap.com](https://www.namecheap.com), [cloudflare.com/products/registrar](https://www.cloudflare.com/products/registrar/), or [porkbun.com](https://porkbun.com).

---

## Subdomain layout

A common setup:

- **api.yourdomain.com** → backend (Render web service). Use this for the eBay webhook and all API calls.
- **yourdomain.com** (or **www.yourdomain.com**) → frontend (later, e.g. Vite app on Render or Vercel).

Example with **cardalpha.com**:

- `https://api.cardalpha.com` → backend
- `https://api.cardalpha.com/health` → health check
- `https://api.cardalpha.com/api/webhooks/ebay/account-deletion` → eBay webhook URL
- `https://cardalpha.com` → future frontend

---

## Connect the domain to Render

### 1. Buy the domain

Register the domain at a registrar (Namecheap, Cloudflare, Google Domains, Porkbun, etc.).

### 2. Add custom domain in Render

1. In **Render Dashboard**, open your **web service** (e.g. **tcg-tool-api**).
2. Go to **Settings** → **Custom Domains**.
3. Click **Add Custom Domain**.
4. Enter the hostname you want (e.g. **api.cardalpha.com**).
5. Render will show the **CNAME target** (e.g. `tcg-tool-api.onrender.com`). Leave this open.

### 3. Point DNS at your registrar

At your domain registrar’s DNS settings for your domain (e.g. **cardstockr.com**):

- **Type:** CNAME  
- **Name/Host:** `api` (for api.yourdomain.com).  
- **Value/Target:** the CNAME Render gave you (e.g. `tcg-tool-api.onrender.com`).

For **api.cardstockr.com** you only need the CNAME for `api`. Save the record; propagation can take a few minutes up to 48 hours.

#### Namecheap (step-by-step)

1. Log in at [namecheap.com](https://www.namecheap.com) → **Domain List** → click your domain (e.g. **cardstockr.com**).
2. Click **Manage** (or **Advanced DNS**).
3. Under **HOST RECORDS** (or **DNS Records**), click **Add New Record**.
4. Add a **CNAME Record**:
   - **Type:** CNAME  
   - **Host:** `api` (only the subdomain; Namecheap may show it as `api` or `api.cardstockr.com` depending on UI).  
   - **Value:** paste the Render CNAME target (e.g. `tcg-tool-api.onrender.com`).  
   - **TTL:** Automatic (or 300).  
5. Remove or leave any existing **URL Redirect** on `api` if it conflicts.  
6. Save. After a few minutes (up to 48 hours), Render will see the CNAME and issue SSL; **https://api.cardstockr.com** will work.

### 4. SSL (HTTPS)

Render provides free SSL for custom domains. After the CNAME is correct, Render will issue a certificate; the site will be available at `https://api.cardalpha.com`.

### 5. Update env and eBay portal

1. **Render** → your web service → **Environment**  
   Set:
   - `EBAY_ACCOUNT_DELETION_ENDPOINT_URL` = `https://api.cardstockr.com/api/webhooks/ebay/account-deletion`  
   (or `https://api.yourdomain.com/...` if you use a different domain.)

2. **eBay Developer Portal** → **Marketplace Account Deletion**  
   - **Endpoint URL:** `https://api.cardstockr.com/api/webhooks/ebay/account-deletion`  
   - **Verification token:** unchanged  
   Save, then run **Send Test Notification** again so eBay uses the new URL.

---

## Optional: Add domain to the Blueprint

If you manage the app with the `render.yaml` Blueprint, you can add the custom domain so it survives Blueprint sync:

```yaml
# In services[0] (your web service):
services:
  - type: web
    runtime: python
    name: tcg-tool-api
    # ...
    domains:
      - api.cardstockr.com
```

Then run **Apply** in the Blueprint. The domain still must be added in the Render UI once (and DNS set) as in steps 2–3 above.

---

## Summary (e.g. cardstockr.com)

| Step | Action |
|------|--------|
| 1 | Buy the domain (e.g. cardstockr.com on Namecheap). |
| 2 | In Render: your web service → **Settings** → **Custom Domains** → Add **api.cardstockr.com**; copy the CNAME target. |
| 3 | In Namecheap: **Domain List** → **Manage** → **Advanced DNS** → Add CNAME: Host **api**, Value = Render’s CNAME target. |
| 4 | Wait for DNS/SSL (minutes to 48h); then set **EBAY_ACCOUNT_DELETION_ENDPOINT_URL** and eBay portal to **https://api.cardstockr.com/api/webhooks/ebay/account-deletion**. |

Using **api.cardstockr.com** for the backend keeps **cardstockr.com** free for your app or marketing site later.
