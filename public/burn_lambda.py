"""
burn_lambda.py — the daily "24 Hour Burn" email (AWS Lambda on an EventBridge daily schedule).

Reads yesterday's day-counter from DynamoDB, emails the summary via SES with the exact subject
"OOI Prototype User Guide 24 Hour Burn", and leaves a fresh (zero) counter for the new window
(a new day# item is created lazily by the ask Lambda, so nothing to reset explicitly).

Env: OOI_UG_TABLE, OOI_UG_REGION, DAILY_CAP_USD, ALERT_EMAIL, OOI_UG_LAUNCH_DATE (YYYY-MM-DD).
Schedule it ~00:05 UTC so it reports the day that just ended.
"""

import datetime
import os
from decimal import Decimal

import boto3

import state

REGION = os.environ.get("OOI_UG_REGION", "us-west-2")
DAILY_CAP = float(os.environ.get("DAILY_CAP_USD", "10"))
ALERT_EMAIL = os.environ.get("ALERT_EMAIL", "")
LAUNCH = os.environ.get("OOI_UG_LAUNCH_DATE", "")

_ses = boto3.client("ses", region_name=REGION)
_ddb = boto3.resource("dynamodb", region_name=REGION)


def _cumulative():
    """Sum spend + days across all day# items (small table scan; fine at this scale)."""
    t = _ddb.Table(state.TABLE)
    total = Decimal("0")
    days = 0
    resp = t.scan(ProjectionExpression="k, spend_usd")
    for it in resp.get("Items", []):
        if str(it.get("k", "")).startswith("day#"):
            total += it.get("spend_usd", Decimal("0"))
            days += 1
    return total, days


def handler(event, context):
    # Report the day that just ended (yesterday UTC).
    y = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=1)
    key = "day#" + y.strftime("%Y-%m-%d")
    d = state.get_day(key)
    cfg = state.get_config()
    spend = float(d.get("spend_usd", 0))
    n_ok = int(d.get("n_ok", 0))
    n_over = int(d.get("n_overcap", 0))
    n_bad = int(d.get("n_badtoken", 0))
    tin = int(d.get("tokens_in", 0))
    tout = int(d.get("tokens_out", 0))
    status = "FROZEN" if cfg.get("frozen") else "ACTIVE"
    tok = cfg.get("token") or "(none)"
    tok_tail = tok[-4:] if tok and tok != "(none)" else tok
    cum, days = _cumulative()

    lines = [
        f"Spend, last 24h: ${spend:.2f} of ${DAILY_CAP:.2f} cap",
        f"Questions answered: {n_ok} ({n_over + n_bad} blocked: {n_over} over-cap, {n_bad} bad-token)",
        f"Bedrock tokens: {tin:,} in / {tout:,} out",
        f"Status: {status}",
        f"Current token (last 4): …{tok_tail}",
        f"Cumulative since launch: ${float(cum):.2f} over {days} day(s)"
        + (f" (launched {LAUNCH})" if LAUNCH else ""),
        "",
        "— counter resets now for the next 24h window.",
    ]
    body = "\n".join(lines)

    if ALERT_EMAIL:
        _ses.send_email(
            Source=ALERT_EMAIL, Destination={"ToAddresses": [ALERT_EMAIL]},
            Message={"Subject": {"Data": "OOI Prototype User Guide 24 Hour Burn"},
                     "Body": {"Text": {"Data": body}}})
    return {"ok": True, "reported": key, "spend": spend}
