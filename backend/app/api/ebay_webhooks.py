"""
eBay Marketplace Account Deletion webhook.

Required for production API keyset: register the endpoint URL and verification token
in the eBay Developer Portal (Alerts & Notifications → Marketplace Account Deletion).
eBay sends a challenge (GET with ?challenge_code=... or POST with JSON challengeCode);
we respond with challengeResponse = SHA256(challengeCode + token + endpointURL).
"""

import hashlib

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.core.config import get_settings

router = APIRouter()


def _challenge_response(challenge_code: str):
    """Compute challengeResponse for eBay verification. Returns JSONResponse on error."""
    settings = get_settings()
    token = getattr(settings, "ebay_account_deletion_token", "") or ""
    endpoint_url = getattr(settings, "ebay_account_deletion_endpoint_url", "") or ""
    if not token or not endpoint_url:
        return JSONResponse(
            status_code=503,
            content={"error": "ebay_account_deletion_token and ebay_account_deletion_endpoint_url must be set"},
        )
    data = (challenge_code + token + endpoint_url).encode("utf-8")
    challenge_response = hashlib.sha256(data).hexdigest()
    return {"challengeResponse": challenge_response}


@router.get("/account-deletion", response_model=None)
async def ebay_account_deletion_get(challenge_code: str | None = None):
    """
    eBay verification uses GET with ?challenge_code=... . Respond with challengeResponse.
    """
    if not challenge_code:
        return {"status": "ok"}
    return _challenge_response(challenge_code)


@router.post("/account-deletion", response_model=None)
async def ebay_account_deletion_post(request: Request):
    """
    Receives eBay verification (POST JSON) and account deletion/closure notifications.
    Must be publicly reachable over HTTPS for production keyset to be enabled.
    """
    try:
        body = await request.json()
    except Exception:
        body = {}
    challenge_code = body.get("challengeCode")

    if challenge_code:
        return _challenge_response(challenge_code)

    # Real deletion/closure event – acknowledge quickly; we don't store eBay user data
    return {"status": "ok"}
