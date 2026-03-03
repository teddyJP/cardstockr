from fastapi import APIRouter

from app.api import ebay_webhooks
from app.api.v1 import cards, metrics, sets as sets_api, status as status_api, targets


router = APIRouter()

# eBay webhooks (for production keyset: Marketplace Account Deletion)
router.include_router(ebay_webhooks.router, prefix="/webhooks/ebay", tags=["ebay-webhooks"])

# v1 namespace
router.include_router(cards.router, prefix="/v1/cards", tags=["cards"])
router.include_router(metrics.router, prefix="/v1/metrics", tags=["metrics"])
router.include_router(sets_api.router, prefix="/v1/sets", tags=["sets"])
router.include_router(targets.router, prefix="/v1/targets", tags=["targets"])
router.include_router(status_api.router, prefix="/v1/status", tags=["status"])

