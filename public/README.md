This folder `public/` contains the AWS backend for the browser-accessible, invite-only public
demo of the user guide. Design + decisions: `../PublicClient.md`. Deploy steps: `DEPLOY.md`.

- `state.py` — shared DynamoDB state helpers (token, frozen flag, per-day spend counter).
- `ask_lambda.py` — request Lambda behind an HTTPS Function URL: freeze → token → $10/day cap →
  Bedrock corpus `ask()` loop → atomic spend update. Only Bedrock calls cost real money, and they
  are gated by the cap.
- `burn_lambda.py` — daily "OOI Prototype User Guide 24 Hour Burn" email (EventBridge schedule).
- `admin.py` — operator CLI: `status`, `freeze`, `unfreeze`, `redo` (rotate token + print link),
  `burn`.
- `DEPLOY.md` — one-time AWS setup (SES verify, DynamoDB, IAM, 2 Lambdas, Function URL, schedule).

The browser page is `../docs/ask.html` (served by GitHub Pages). Account: securecomputing
(084375582624), us-west-2, model Sonnet 4.6, alert email via the `ALERT_EMAIL` env var.
