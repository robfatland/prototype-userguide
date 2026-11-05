"""
state.py — shared DynamoDB state helpers for the public user-guide demo.

One table (default name `ooi-ug-state`, override with env OOI_UG_TABLE) holds a handful of
single-row items keyed by `k`:

  k="config"  → token (str), frozen (bool)
  k="day#<YYYY-MM-DD>" → spend_usd (Decimal), n_ok, n_overcap, n_badtoken,
                          tokens_in, tokens_out, overcap_notified (bool)

Used by the ask Lambda, the daily-burn Lambda, and admin.py. Region defaults to us-west-2.
"""

import os
import datetime
from decimal import Decimal

import boto3

TABLE = os.environ.get("OOI_UG_TABLE", "ooi-ug-state")
REGION = os.environ.get("OOI_UG_REGION", "us-west-2")

_ddb = boto3.resource("dynamodb", region_name=REGION)
_t = _ddb.Table(TABLE)


def today_key(now=None):
    now = now or datetime.datetime.now(datetime.timezone.utc)
    return "day#" + now.strftime("%Y-%m-%d")


def get_config():
    r = _t.get_item(Key={"k": "config"}).get("Item")
    return r or {"k": "config", "token": None, "frozen": False}


def set_token(token):
    _t.update_item(Key={"k": "config"},
                   UpdateExpression="SET #tok = :v",
                   ExpressionAttributeNames={"#tok": "token"},
                   ExpressionAttributeValues={":v": token})


def set_frozen(flag):
    _t.update_item(Key={"k": "config"},
                   UpdateExpression="SET frozen = :v",
                   ExpressionAttributeValues={":v": bool(flag)})


def get_day(key=None):
    key = key or today_key()
    r = _t.get_item(Key={"k": key}).get("Item")
    if not r:
        return {"k": key, "spend_usd": Decimal("0"), "n_ok": 0, "n_overcap": 0,
                "n_badtoken": 0, "tokens_in": 0, "tokens_out": 0,
                "overcap_notified": False}
    return r


def add_spend(usd, tokens_in, tokens_out, key=None):
    """Atomically add a completed Bedrock call's cost to today's counter; returns new spend."""
    key = key or today_key()
    r = _t.update_item(
        Key={"k": key},
        UpdateExpression=("ADD spend_usd :c, n_ok :one, tokens_in :ti, tokens_out :to_"),
        ExpressionAttributeValues={
            ":c": Decimal(str(usd)), ":one": 1,
            ":ti": int(tokens_in), ":to_": int(tokens_out)},
        ReturnValues="UPDATED_NEW")
    return r["Attributes"]["spend_usd"]


def bump_counter(name, key=None):
    """Increment a named counter (n_overcap / n_badtoken) for today."""
    key = key or today_key()
    _t.update_item(Key={"k": key},
                   UpdateExpression=f"ADD {name} :one",
                   ExpressionAttributeValues={":one": 1})


def mark_overcap_notified(key=None):
    """Set the once-per-day over-cap-notified flag; return True if WE set it (was unset)."""
    key = key or today_key()
    try:
        _t.update_item(
            Key={"k": key},
            UpdateExpression="SET overcap_notified = :t",
            ConditionExpression="attribute_not_exists(overcap_notified) OR overcap_notified = :f",
            ExpressionAttributeValues={":t": True, ":f": False})
        return True
    except _ddb.meta.client.exceptions.ConditionalCheckFailedException:
        return False
