"""
Check eBay account-deletion webhook env and print values for the eBay Developer Portal.

Run from backend/:  python -m scripts.check_ebay_webhook_setup
"""
import os
import sys

# Load .env from backend root
backend_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_root not in sys.path:
    sys.path.insert(0, backend_root)
os.chdir(backend_root)

from app.core.config import get_settings


def main() -> None:
    s = get_settings()
    ok = True

    if not s.ebay_app_id:
        print("Missing EBAY_APP_ID in .env (use your Production App ID from eBay Developer Portal).")
        ok = False
    else:
        print(f"EBAY_APP_ID is set (starts with ...{s.ebay_app_id[-8:]})")

    if not s.ebay_account_deletion_token:
        print("Missing EBAY_ACCOUNT_DELETION_TOKEN in .env (run scripts/generate_ebay_webhook_token.py to generate one).")
        ok = False
    else:
        print(f"EBAY_ACCOUNT_DELETION_TOKEN is set ({len(s.ebay_account_deletion_token)} chars)")

    if not s.ebay_account_deletion_endpoint_url:
        print("Missing EBAY_ACCOUNT_DELETION_ENDPOINT_URL in .env.")
        print("  → If using ngrok: run 'ngrok http 8000' and set this to https://YOUR_NGROK_URL/api/webhooks/ebay/account-deletion")
        ok = False
    else:
        print(f"EBAY_ACCOUNT_DELETION_ENDPOINT_URL is set: {s.ebay_account_deletion_endpoint_url}")

    if not ok:
        print("\nFix the items above, then run this script again.")
        sys.exit(1)

    print("\n--- Copy these into eBay Developer Portal (Production → Alerts & Notifications → Marketplace Account Deletion) ---\n")
    print("Endpoint URL:")
    print(s.ebay_account_deletion_endpoint_url)
    print("\nVerification token:")
    print(s.ebay_account_deletion_token)
    print("\nThen click Save and 'Send Test Notification'.")


if __name__ == "__main__":
    main()
