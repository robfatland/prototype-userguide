# PublicClient — a browser-accessible, invite-only demo of the user-guide client

Status: **DESIGN. Nothing built.** A design for turning the local `client/ask.py` into a small web
page that OOI program participants can try in a browser, without installing anything — while
keeping it a prototype and keeping a bot from running up a Bedrock bill.

**Unofficial**, same as the rest of this repo. This is a demo for a handful of invited people, not
a production service.


## What we have now, and the one hard problem

Today: a static corpus on GitHub Pages + a local Python client (`ask.py`) that holds AWS
credentials and calls Bedrock. There is no server and no public endpoint.

To put it in a browser, exactly one thing must change: **the AWS credentials cannot live in the
browser.** Anything shipped to a browser is readable by anyone who opens it, so the Bedrock call
has to happen on a small server we control, and the browser talks to that server. That server is
the only new moving part — and it's where both the cost and the abuse risk live.

The abuse risk is concrete: an open "ask a question" box on the internet is an open spigot on a
pay-per-token API. Someone (or a bot) can hammer it and run up a bill. So the design is really
two questions: **(1) where does the Bedrock call run, and (2) how do we let in only invited people
without a heavyweight login.**


## Authentication: invite tokens (what you asked for), explained simply

You said you'd prefer a **temporary token system** over email/GitHub login. That's the right call
for a small invited demo, and here's what it means in plain terms.

- A **token** is just a long random string, e.g. `ooi-7Kd9-F2aQ-x1Mn`. You generate a handful,
  one per invitee (or a few shared ones), and send them out ("here's the link, here's your
  access code").
- To use the demo, a visitor pastes their token into a box (or it's baked into the link you send:
  `.../ask?token=ooi-7Kd9-...`). The server checks the token against a short allow-list before it
  ever calls Bedrock. No token, no answer.
- "Temporary" = each token has an **expiry date** (e.g. "good through the AGU meeting") and can be
  **revoked** by deleting it from the list. If one leaks, you remove it; the others keep working.
- This is **not** real user accounts. There are no passwords, no emails, no "sign in with GitHub."
  The token *is* the credential. That's appropriate because the stakes are low (a demo) and the
  audience is small and known.

Why this is enough here, and where it's weak (honest version):

- **Enough because:** the only thing we're protecting is a small token budget, the audience is
  invited, and a leaked token costs dollars, not data. There's no private data behind this.
- **Weak because:** a token shared in a public place (pasted into a chat, committed to a repo) is
  usable by anyone who sees it until it's revoked. We mitigate with (a) expiry, (b) a **hard
  per-token and per-day spend cap** (below) so even a leaked token can't run up more than a set
  amount, and (c) easy revocation.

**Two cheap backstops that matter more than the token itself:**

1. **A global daily budget ceiling.** Independent of tokens, the server refuses to call Bedrock
   once the day's spend (counted in tokens) crosses a set limit, e.g. $5/day. This is the real
   protection against a surprise bill — it caps the blast radius no matter what leaks. AWS
   **Budgets** can also alert/stop at the account level as a second net.
- **A rate limit per token** (e.g. N questions per hour) so one token can't be hammered.

If you later want zero standing exposure, the heaviest-but-simplest option is to not host it
continuously at all — see "Option C."


## Three ways to host it (cheapest/simplest first)

All three keep the corpus on GitHub Pages unchanged; only the "call Bedrock on a server" part
differs.

### Option A — Serverless function (recommended)
A single small cloud function (AWS **Lambda**) behind an HTTPS endpoint (**Lambda Function URL**,
or API Gateway). The browser page (also static, can live on GitHub Pages) POSTs
`{question, token}` to it; the function checks the token + budget, runs the same `ask()` loop
against Bedrock, returns the answer.

- **Pros:** no server to keep running; you pay only per request; the AWS credentials live only in
  the function's IAM role, never in the browser; scales to zero when idle (≈ $0 when nobody's
  using it).
- **Cons:** a little AWS plumbing (one function, one role, one URL); cold-start adds ~1 s to the
  first call.
- **Token list + budget counter:** a tiny DynamoDB table or even a JSON file in S3. Spend counter
  is a single number updated per call.

### Option B — Tiny always-on server
A small container or micro-VM (e.g. AWS App Runner, a $5/mo Lightsail/VPS, or Fly.io) running a
~50-line FastAPI app wrapping `ask.py`.

- **Pros:** conceptually simplest if you've run a web app before; no cold starts.
- **Cons:** it runs (and bills a flat monthly fee) 24/7 even when idle; you patch/maintain it.

### Option C — No hosting: a local client with a shared token (lightest "lift", least convenient)
Keep `ask.py` as-is but have invitees run it with a **shared, budget-capped token** that maps to
*your* AWS usage via a thin relay you run only during the demo. In practice this collapses into
Option A anyway, so A is the honest recommendation. Mentioned only to show the spectrum.

**Recommendation: Option A.** It's the one that is genuinely near-zero cost when idle, keeps
credentials server-side, and matches "a prototype for a few invited people."


## Shape of the thing (Option A)

```
Browser (static page on GitHub Pages)
   │  POST {question, token}   (HTTPS)
   ▼
Lambda Function URL  ── checks token (allow-list) ──► reject if unknown/expired
   │                 ── checks daily budget ───────► reject if over cap
   │                 ── checks per-token rate ─────► reject if too fast
   ▼
ask() loop  ──fetch corpus pages (GitHub Pages)──►  ──Bedrock Converse──►  Claude Sonnet
   │
   ▼  answer + which pages used
Browser renders the answer
```

- The `ask()` logic is lifted almost verbatim from `client/ask.py` — same `fetch_doc` allow-list,
  same system prompt, same tool loop. The only additions are the three gate checks and reading
  the token list / budget counter.
- The browser page is ~50 lines of HTML/JS: a text box, a "token" field, a "ask" button, and a
  div that shows the answer. No framework needed.


## Cost per month (estimate)

Two parts: **hosting** (near zero) and **model usage** (the only real cost, and it's capped).

**Hosting (Option A), assuming a light demo:**

| Piece | Rate | Typical demo month | Cost |
|---|---|---|---|
| GitHub Pages (corpus + page) | free | — | **$0** |
| Lambda (compute) | free tier 1M req/mo, then ~$0.20/M | hundreds of calls | **~$0** |
| Lambda Function URL / data out | pennies | — | **~$0** |
| DynamoDB or S3 (token list + counter) | free tier / pennies | tiny | **~$0** |

So **hosting ≈ $0–1/month** for a demo. It genuinely scales to zero when idle.

**Model usage (Bedrock, Claude Sonnet 4.6)** — the part to watch. From the test bank, a typical
question is **~7–12k input + ~1–2k output tokens ≈ $0.04–0.08 per question** (US-profile rate
$3.30 / $16.50 per M in/out; confirm in billing).

| Scenario | Questions/month | Model cost |
|---|---|---|
| Quiet demo (a few people poke at it) | ~100 | **~$5–8** |
| Active week around AGU | ~500 | **~$25–40** |
| **If uncapped and a bot finds it** | unbounded | **the reason for the daily cap** |

**With a $5/day global budget ceiling**, the worst case is bounded: ~$150/month even if it's
hammered every day, and realistically far less because the demo isn't used daily. Set the cap to
your comfort (e.g. $2/day → ≤ ~$60/month worst case). **Recommend: daily cap + an AWS Budgets
alert at a monthly number you choose, so you're never surprised.**

Rough all-in for a real demo month: **likely $5–20, capped well below $100.** Prompt caching of
the (unchanging) corpus pages would cut the input-token cost further if usage grows.


## What building it would take (Option A)

1. Lift `ask()` into a Lambda handler; add three gates (token allow-list, daily budget, per-token
   rate). (~half a day)
2. Token store + spend counter in DynamoDB or an S3 JSON. Generate ~10 invite tokens with expiry.
   (~couple hours)
3. Minimal HTML/JS ask page (static; can sit in `docs/` on Pages). (~couple hours)
4. IAM role for the Lambda (`bedrock:InvokeModel` + table access); Function URL; CORS so the Pages
   origin can call it. (~couple hours)
5. AWS Budgets alert on the account; set the daily cap in code. (~1 hour)
6. Test with the test-bank questions through the browser; hand tokens to a couple of invitees.

Call it **~1–2 days**. No new services beyond AWS Lambda + DynamoDB/S3 (both free-tier for this
scale), on top of the Bedrock access we already use.


## Open questions

- Account: run this in `securecomputing` (084375582624), same as the client? Confirm.
- Daily spend cap value, and token expiry window (through AGU? a fixed date?).
- How many invite tokens, and shared vs one-per-person (one-per-person makes revocation and
  "who used what" cleaner).
- Model: keep Sonnet 4.6, or offer Haiku as a cheaper default for the public demo?
