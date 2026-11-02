"""
ask.py — answer ocean-observatory data questions from the prototype-userguide corpus,
using a foundation model on Amazon Bedrock (Converse API + one tool, fetch_doc).

How it works:
  1. Download the corpus index (llms.txt) and send it to the model with your question.
  2. The model asks (via the fetch_doc tool) for the corpus pages it needs.
  3. This script fetches those pages and sends their text back.
  4. The model answers, citing the pages it used.
fetch_doc only fetches from the corpus site (allowlist) — never arbitrary URLs.

Usage:
    python client/ask.py "How do I read the QC flags in a FLORT file?"
    python client/ask.py --verbose "..."   # show which pages were fetched + token usage

Config (environment variables, all optional):
    USERGUIDE_AWS_PROFILE   AWS CLI profile for Bedrock      (default: securecomputing)
    USERGUIDE_AWS_REGION    Bedrock region                   (default: us-west-2)
    USERGUIDE_MODEL_ID      Bedrock model / inference profile (default: us.anthropic.claude-sonnet-4-6)
    USERGUIDE_BASE_URL      corpus root URL (default: https://robfatland.github.io/prototype-userguide/)
"""

import argparse
import os
import sys
import urllib.error
import urllib.request

import boto3

BASE = os.environ.get("USERGUIDE_BASE_URL",
                      "https://robfatland.github.io/prototype-userguide/").rstrip("/") + "/"
PROFILE = os.environ.get("USERGUIDE_AWS_PROFILE", "securecomputing")
REGION = os.environ.get("USERGUIDE_AWS_REGION", "us-west-2")
MODEL_ID = os.environ.get("USERGUIDE_MODEL_ID", "us.anthropic.claude-sonnet-4-6")

MAX_TOOL_ROUNDS = 6        # cap on fetch rounds per question
MAX_PAGE_CHARS = 60_000    # truncate very long pages
MAX_ANSWER_TOKENS = 2_000

SYSTEM = [{"text": (
    "You answer questions about ocean-observatory (OOI) data for scientists, using ONLY the "
    "prototype-userguide corpus. You are given its index, llms.txt. Fetch the pages you need with "
    "the fetch_doc tool before answering. In the answer: be practical and concise; name which "
    "variables to use; cite the corpus page(s) you used and the primary sources they cite. "
    "Rules: (1) Impact ratings ([HIGH]/[MEDIUM]/[LOW]) must be copied exactly as the page gives "
    "them — never raise, lower, or invent a rating for a statement the page leaves unrated. "
    "(2) Only cite URLs that appear in the corpus pages you fetched; never construct or guess a "
    "URL. (3) Keep the page's qualifiers (dates, 'from 2017 on', 'in the example file', "
    "'project experience'). (4) If the corpus does not cover the question, say so plainly instead "
    "of guessing.")}]

TOOLS = {"tools": [{"toolSpec": {
    "name": "fetch_doc",
    "description": ("Fetch a page from the prototype-userguide corpus. Pass the page's relative "
                    "path (e.g. 'flort.md') or its full URL as listed in llms.txt."),
    "inputSchema": {"json": {
        "type": "object",
        "properties": {"path": {"type": "string",
                                "description": "Relative path or full corpus URL of the page"}},
        "required": ["path"]}}}}]}


def fetch_doc(path):
    """Fetch a corpus page. Accepts a relative path or a full URL under BASE; refuses others."""
    path = (path or "").strip()
    if path.startswith(BASE):
        path = path[len(BASE):]
    if "://" in path or ".." in path or path.startswith("/"):
        return f"ERROR: '{path}' is outside the corpus. Only pages under {BASE} can be fetched."
    url = BASE + path
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "prototype-userguide/ask.py"})
        with urllib.request.urlopen(req, timeout=20) as r:
            return r.read().decode("utf-8", errors="replace")[:MAX_PAGE_CHARS]
    except urllib.error.HTTPError as e:
        return f"ERROR: {url} returned HTTP {e.code} (page may be planned but not yet written)."
    except urllib.error.URLError as e:
        return f"ERROR: could not fetch {url}: {e.reason}"


def ask(question, verbose=False):
    brt = boto3.Session(profile_name=PROFILE, region_name=REGION).client("bedrock-runtime")
    msgs = [{"role": "user", "content": [
        {"text": "Corpus index (llms.txt):\n\n" + fetch_doc("llms.txt")},
        {"text": "Question: " + question}]}]
    tokens_in = tokens_out = 0

    for _ in range(MAX_TOOL_ROUNDS):
        resp = brt.converse(modelId=MODEL_ID, system=SYSTEM, messages=msgs, toolConfig=TOOLS,
                            inferenceConfig={"maxTokens": MAX_ANSWER_TOKENS})
        tokens_in += resp["usage"]["inputTokens"]
        tokens_out += resp["usage"]["outputTokens"]
        out = resp["output"]["message"]
        msgs.append(out)

        if resp["stopReason"] != "tool_use":
            if verbose:
                print(f"[tokens: {tokens_in} in / {tokens_out} out]", file=sys.stderr)
            return "".join(b.get("text", "") for b in out["content"])

        results = []
        for block in out["content"]:
            if "toolUse" in block:
                tu = block["toolUse"]
                page = tu["input"].get("path", "")
                if verbose:
                    print(f"[fetch_doc] {page}", file=sys.stderr)
                results.append({"toolResult": {"toolUseId": tu["toolUseId"],
                                               "content": [{"text": fetch_doc(page)}]}})
        msgs.append({"role": "user", "content": results})

    return "(stopped: too many fetch rounds without a final answer)"


def main():
    ap = argparse.ArgumentParser(description="Ask the prototype-userguide corpus a question.")
    ap.add_argument("question", nargs="+", help="your question")
    ap.add_argument("--verbose", "-v", action="store_true",
                    help="show fetched pages and token usage (on stderr)")
    args = ap.parse_args()
    print(ask(" ".join(args.question), verbose=args.verbose))


if __name__ == "__main__":
    main()
