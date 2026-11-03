# prototype-userguide

A self-funded prototype of the lightest-lift way to give scientists an AI-usable **user guide**
for ocean-observatory data: a curated, AI-readable corpus (`llms.txt` + plain markdown pages)
published on GitHub Pages, plus a small client that lets a foundation model (via Amazon Bedrock)
answer questions from it.

**Unofficial.** Not affiliated with, endorsed by, or funded by any observatory program. Pages link
to their primary sources; official sources take precedence.

- Corpus (live): https://robfatland.github.io/prototype-userguide/llms.txt
- Use it with any AI: *"Use https://robfatland.github.io/prototype-userguide/llms.txt to answer my
  questions about ocean-observatory data."*

## Layout

- `UserGuide.md` — design: how it works, decisions, corpus structure, phasing, client sketch,
  prerequisites, build steps, results.
- `docs/` — the published corpus (GitHub Pages source). `docs/llms.txt` is the index.
- `PublicClient.md` — design for a browser-accessible, invite-only (token) version of the client,
  with per-day budget caps and a cost estimate. Not built.
- `client/ask.py` — the Bedrock client. Needs `boto3` and AWS credentials with Bedrock access:
  `python client/ask.py -v "Which FLORT variable should I use for backscatter?"`
  (defaults: profile `securecomputing`, region `us-west-2`, model
  `us.anthropic.claude-sonnet-4-6`; override with `USERGUIDE_AWS_PROFILE`, `USERGUIDE_AWS_REGION`,
  `USERGUIDE_MODEL_ID`).
- `tools/` — *(planned)* `zenodo_catalog.py`, generates `docs/datasets.md`.
