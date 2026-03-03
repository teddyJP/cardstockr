"""Generate a random 32–80 character string for EBAY_ACCOUNT_DELETION_TOKEN."""
import secrets

token = secrets.token_urlsafe(48)  # 48 bytes -> 64 chars base64url
print(token)
