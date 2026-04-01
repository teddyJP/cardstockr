#!/usr/bin/env bash
# Run on your machine after deploy. Usage:
#   ./scripts/test_hosted_api.sh
#   BASE_URL=https://api.cardstockr.com ./scripts/test_hosted_api.sh

set -euo pipefail
BASE_URL="${BASE_URL:-https://api.cardstockr.com}"

echo "==> GET $BASE_URL/health"
curl -sS "$BASE_URL/health" | head -c 200
echo ""
echo ""

echo "==> GET webhook (eBay-style challenge)"
curl -sS "$BASE_URL/api/webhooks/ebay/account-deletion?challenge_code=test123" | head -c 400
echo ""
echo ""

echo "Done. Expect health: {\"status\":\"ok\"} and webhook: {\"challengeResponse\":\"...\"}"
