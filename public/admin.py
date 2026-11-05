#!/usr/bin/env python
"""
admin.py — operator CLI for the public user-guide demo. Edits the DynamoDB state directly
(run locally with AWS creds for the securecomputing account).

Commands:
  python admin.py status              show spend today, token (last 4), frozen state
  python admin.py freeze              lock the site: returns "offline", no Bedrock calls
  python admin.py unfreeze            re-enable the site
  python admin.py redo                expire the current token, mint a new one, print the link
  python admin.py burn                send the daily-burn email now (for testing)

Env: OOI_UG_TABLE, OOI_UG_REGION, OOI_UG_SITE_URL (the browser page URL, for the printed link).
"""

import argparse
import os
import secrets

import state


def new_token():
    # e.g. ooi-7Kd9-F2aQ-x1Mn : readable-ish, ~60 bits, URL-safe.
    g = lambda: secrets.token_urlsafe(3)[:4]
    return "ooi-" + "-".join(g() for _ in range(3))


def cmd_status(_):
    cfg = state.get_config()
    d = state.get_day()
    tok = cfg.get("token") or "(none)"
    print(f"frozen:        {bool(cfg.get('frozen'))}")
    print(f"token (last4): …{tok[-4:] if tok != '(none)' else tok}")
    print(f"spend today:   ${float(d.get('spend_usd', 0)):.2f}")
    print(f"answered today:{int(d.get('n_ok', 0))}  "
          f"over-cap:{int(d.get('n_overcap', 0))}  bad-token:{int(d.get('n_badtoken', 0))}")


def cmd_freeze(_):
    state.set_frozen(True)
    print("FROZEN — the site now returns 'temporarily offline' and will not call Bedrock.")


def cmd_unfreeze(_):
    state.set_frozen(False)
    print("UNFROZEN — the site is live again.")


def cmd_redo(_):
    tok = new_token()
    state.set_token(tok)
    site = os.environ.get("OOI_UG_SITE_URL", "https://robfatland.github.io/prototype-userguide/ask.html")
    sep = "&" if "?" in site else "?"
    print("New token minted; the previous token is now dead.")
    print(f"token: {tok}")
    print(f"link to email:\n  {site}{sep}token={tok}")


def cmd_burn(_):
    import burn_lambda
    r = burn_lambda.handler({}, None)
    print("sent daily-burn email:", r)


def main():
    ap = argparse.ArgumentParser(description="Admin CLI for the public user-guide demo.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name, fn, help_ in [
            ("status", cmd_status, "show spend/token/frozen"),
            ("freeze", cmd_freeze, "lock the site"),
            ("unfreeze", cmd_unfreeze, "unlock the site"),
            ("redo", cmd_redo, "expire + reissue the token, print the link"),
            ("burn", cmd_burn, "send the daily-burn email now")]:
        sp = sub.add_parser(name, help=help_)
        sp.set_defaults(func=fn)
    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
