"""
ask_lambda.py — the public demo's request handler (AWS Lambda, behind a Function URL).

Flow per request:
  1. If the site is FROZEN -> return "offline", no Bedrock.
  2. If the token is missing/wrong -> return "bad token", count it, no Bedrock.
  3. If today's spend is already >= DAILY_CAP_USD -> return "busy today", count it, no Bedrock;
     send the one-time over-cap email the first time it trips.
  4. Otherwise run the corpus ask() loop against Bedrock, then add the call's cost to today's
     spend counter. (Cap is checked BEFORE the call; a single call can nudge slightly past the
     cap, which is fine — the next request is refused.)

The only unbounded cost is Bedrock tokens, and it is gated by the daily cap. Frozen / bad-token
requests return before any Bedrock call (micro-cost only).

Env: OOI_UG_TABLE, OOI_UG_REGION, OOI_UG_MODEL_ID, OOI_UG_BASE_URL, DAILY_CAP_USD,
     ALERT_EMAIL, PRICE_IN_PER_MTOK, PRICE_OUT_PER_MTOK.
"""

import json
import os
import urllib.error
import urllib.request

import boto3

import state

MODEL_ID = os.environ.get("OOI_UG_MODEL_ID", "us.anthropic.claude-sonnet-4-6")
BASE_URL = os.environ.get("OOI_UG_BASE_URL",
                          "https://robfatland.github.io/prototype-userguide/").rstrip("/") + "/"
REGION = os.environ.get("OOI_UG_REGION", "us-west-2")
DAILY_CAP = float(os.environ.get("DAILY_CAP_USD", "10"))
ALERT_EMAIL = os.environ.get("ALERT_EMAIL", "")
PRICE_IN = float(os.environ.get("PRICE_IN_PER_MTOK", "3.30"))     # $/M input tokens
PRICE_OUT = float(os.environ.get("PRICE_OUT_PER_MTOK", "16.50"))  # $/M output tokens

MAX_TOOL_ROUNDS = 6
MAX_PAGE_CHARS = 60_000
MAX_ANSWER_TOKENS = 2_000

_brt = boto3.client("bedrock-runtime", region_name=REGION)
_ses = boto3.client("ses", region_name=REGION)

SYSTEM = [{"text": (
    "You answer questions about ocean-observatory (OOI) data for scientists, using ONLY the "
    "prototype-userguide corpus. You are given its index, llms.txt. Fetch the pages you need with "
    "the fetch_doc tool before answering. Be practical and concise; name which variables to use; "
    "cite the corpus page(s) you used and their primary sources. Copy the pages' impact ratings "
    "([HIGH]/[MEDIUM]/[LOW]) exactly; never invent or change one. Only cite URLs that appear in "
    "the fetched pages. If the corpus does not cover the question, say so plainly.")}]

TOOLS = {"tools": [{"toolSpec": {
    "name": "fetch_doc",
    "description": "Fetch a page from the user-guide corpus by its relative path from llms.txt.",
    "inputSchema": {"json": {"type": "object",
                             "properties": {"path": {"type": "string"}},
                             "required": ["path"]}}}}]}


def fetch_doc(path):
    path = (path or "").strip()
    if path.startswith(BASE_URL):
        path = path[len(BASE_URL):]
    if "://" in path or ".." in path or path.startswith("/"):
        return f"ERROR: '{path}' is outside the corpus."
    try:
        req = urllib.request.Request(BASE_URL + path,
                                     headers={"User-Agent": "ooi-ug-public/ask"})
        with urllib.request.urlopen(req, timeout=20) as r:
            return r.read().decode("utf-8", errors="replace")[:MAX_PAGE_CHARS]
    except urllib.error.HTTPError as e:
        return f"ERROR: {path} returned HTTP {e.code}."
    except urllib.error.URLError as e:
        return f"ERROR: could not fetch {path}: {e.reason}"


def _answer(question):
    """Run the corpus loop; return (text, tokens_in, tokens_out)."""
    msgs = [{"role": "user", "content": [
        {"text": "Corpus index (llms.txt):\n\n" + fetch_doc("llms.txt")},
        {"text": "Question: " + question}]}]
    tin = tout = 0
    for _ in range(MAX_TOOL_ROUNDS):
        resp = _brt.converse(modelId=MODEL_ID, system=SYSTEM, messages=msgs, toolConfig=TOOLS,
                             inferenceConfig={"maxTokens": MAX_ANSWER_TOKENS})
        tin += resp["usage"]["inputTokens"]
        tout += resp["usage"]["outputTokens"]
        out = resp["output"]["message"]
        msgs.append(out)
        if resp["stopReason"] != "tool_use":
            return "".join(b.get("text", "") for b in out["content"]), tin, tout
        results = []
        for b in out["content"]:
            if "toolUse" in b:
                tu = b["toolUse"]
                results.append({"toolResult": {"toolUseId": tu["toolUseId"],
                                               "content": [{"text": fetch_doc(tu["input"].get("path", ""))}]}})
        msgs.append({"role": "user", "content": results})
    return "(stopped: too many fetch rounds)", tin, tout


def _reply(status, body):
    return {"statusCode": status,
            "headers": {"Content-Type": "application/json",
                        "Access-Control-Allow-Origin": "*",
                        "Access-Control-Allow-Headers": "content-type",
                        "Access-Control-Allow-Methods": "POST, OPTIONS"},
            "body": json.dumps(body)}


def _overcap_email(spend):
    if not ALERT_EMAIL or not state.mark_overcap_notified():
        return
    _ses.send_email(
        Source=ALERT_EMAIL, Destination={"ToAddresses": [ALERT_EMAIL]},
        Message={"Subject": {"Data": "OOI Prototype User Guide — daily cap reached"},
                 "Body": {"Text": {"Data":
                     f"The ${DAILY_CAP:.2f} daily cap was reached (spend ${float(spend):.2f}). "
                     "The site is now returning 'busy, try tomorrow' and will not call Bedrock "
                     "again until the counter resets at the next daily window. No action needed; "
                     "use `admin.py freeze` to hard-off."}}})


def handler(event, context):
    # CORS preflight
    method = (event.get("requestContext", {}).get("http", {}).get("method", "POST"))
    if method == "OPTIONS":
        return _reply(200, {"ok": True})

    try:
        body = json.loads(event.get("body") or "{}")
    except Exception:
        return _reply(400, {"error": "bad request"})
    token = (body.get("token") or "").strip()
    question = (body.get("question") or "").strip()

    cfg = state.get_config()
    if cfg.get("frozen"):
        return _reply(200, {"blocked": "frozen",
                            "message": "The demo is temporarily offline."})
    if not token or token != cfg.get("token"):
        state.bump_counter("n_badtoken")
        return _reply(200, {"blocked": "badtoken",
                            "message": "This link's access code is no longer active — "
                                       "contact the sender for a new link."})
    if not question:
        return _reply(400, {"error": "empty question"})

    day = state.get_day()
    if float(day.get("spend_usd", 0)) >= DAILY_CAP:
        state.bump_counter("n_overcap")
        _overcap_email(day.get("spend_usd", 0))
        return _reply(200, {"blocked": "overcap",
                            "message": "The demo has reached today's usage limit; "
                                       "please try again tomorrow."})

    text, tin, tout = _answer(question)
    cost = tin / 1e6 * PRICE_IN + tout / 1e6 * PRICE_OUT
    new_spend = state.add_spend(cost, tin, tout)
    if float(new_spend) >= DAILY_CAP:
        _overcap_email(new_spend)
    return _reply(200, {"answer": text,
                        "tokens": {"in": tin, "out": tout},
                        "spend_today_usd": round(float(new_spend), 4)})
