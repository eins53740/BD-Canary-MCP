# Configuration (.env)
CANARY_WRITER_ENABLED (default auto‑enabled if URL+token present): set false to temporarily pause writes.
CANARY_SAF_BASE_URL, CANARY_VIEWS_BASE_URL: base URLs (no trailing slash required).
CANARY_API_TOKEN: Canary API token.
CANARY_CLIENT_ID: client identity used by SAF.
CANARY_HISTORIANS: comma‑separated historian targets.

CANARY_RATE_LIMIT_RPS: max requests per second (default 500).
CANARY_QUEUE_CAPACITY: in‑memory queue to absorb bursts.
CANARY_MAX_BATCH_TAGS: number of tags per request batch (default 100).
CANARY_MAX_PAYLOAD_BYTES: guardrail for payload size (default 1 MB).
CANARY_REQUEST_TIMEOUT_SECONDS: per‑request timeout (default 10s).
CANARY_RETRY_ATTEMPTS: number of retry attempts after the initial send (default 6).
CANARY_RETRY_BASE_DELAY_SECONDS, CANARY_RETRY_MAX_DELAY_SECONDS: exponential backoff with jitter.
CANARY_CIRCUIT_CONSECUTIVE_FAILURES, CANARY_CIRCUIT_RESET_SECONDS: circuit breaker thresholds.

CANARY_SESSION_TIMEOUT_MS: SAF session timeout hint in milliseconds (default 120000).
CANARY_KEEPALIVE_IDLE_SECONDS: idle seconds before sending keepAlive (default 30).
CANARY_KEEPALIVE_JITTER_SECONDS: random jitter added to keepAlive timing (default 10).

CANARY_DATASET_PREFIX: base dataset name (e.g., Secil).
CANARY_DATASET_OVERRIDE: set to Test to force writes into a test dataset.

# Production Server
CANARY_SERVER_URL: https://scunscanary.secil.pt/
CANARY_SERVER_URL: 172.21.2.103

# Deployment:
Set/verify .env variables. Secrets like CANARY_API_TOKEN should come from your secrets store and not be committed.
Restart the service so new configuration loads.
Confirm startup logs show the Canary client initialised and CDC enabled if desired.
Validation (smoke)
Unit quick check: uv run pytest -m unit -q
Canary client integration harness (no external Canary required): uv run pytest tests/integration/test_cdc_to_canary_client.py -q
Confirm uns_meta.canary_dlq exists: SELECT to_regclass('uns_meta.canary_dlq'); returns non‑NULL.

Write smoke tests:
Direct write (Path A) using the Canary client:

uv run python scripts/canary_write_smoke.py \
  --path Test/Smoke/DeviceA/Temperature \
  --prop description="Smoke test {timestamp}" \
  --dry-run
Remove --dry-run to send the request. Metrics summary prints on completion; expect Failures=0 and dead_letter_total=0.


Canary Request Basics:
Endpoint: POST /api/v1/storeData
Base URL: CANARY_SAF_BASE_URL (e.g., https://host:port/api/v1)
Authentication: obtain sessionToken via POST /api/v1/getSessionToken using CANARY_API_TOKEN and include it in requests. The service manages this automatically via the SAF session manager.
Body (properties‑only diffs):
sessionToken (if SAF session used)
properties: { <canary_tag_id>: [[timestamp, "key=value", 192], ...], ... }
Example payload snippet:
{
  "sessionToken": "<token>",
  "properties": {
    "Secil.Portugal.Cement.Kiln.Temperature": [
      ["2025-01-01T12:00:00.000000Z", "engUnit=°C", 192],
      ["2025-01-01T12:00:00.000000Z", "displayHigh=1800", 192]
    ]
  }
}