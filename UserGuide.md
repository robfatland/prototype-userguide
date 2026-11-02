# prototype-userguide — design

A self-funded, standalone prototype of the lightest-lift way to give scientists an AI-usable
**user guide** for ocean-observatory data: publish a curated, AI-readable corpus (`llms.txt` +
plain markdown pages) on GitHub Pages, and show that a foundation model (FM), reached through
Amazon Bedrock, answers practical data questions well using only that corpus.

**Unofficial.** Not affiliated with, endorsed by, or funded by any observatory program. Every
page links to its primary sources; where this guide and an official source disagree, the official
source wins.

Status: **v0 in progress** — repo + Pages skeleton live; corpus pages and client not yet written.


## What problem does this solve — and what does the FM do?

Existing observatory documentation has two problems: it is **labyrinthine** (hard to find your way
through) and **unhelpful as a user guide** (even when found, it doesn't tell a scientist which
variable to use, what the QC flags mean, or what to distrust).

- **`llms.txt` links to our own pages, not to program web pages.** Only the two *reference
  index* pages are mostly link lists into external sites — those address the **labyrinth**
  problem.
- **The guide pages are where the missing user-guide content gets written** — which variable is
  the science variable, what the flags mean, what to distrust, how to get the data. That addresses
  the **unhelpful** problem, and **we solve it by writing that content, not the FM.**
- **The FM's job is narrower:** find the right page(s) and answer from them, with citations.
- **If a guide page is thin, the FM will fill gaps with general knowledge or guesses.** Catching
  that is exactly what the test bank is for: every wrong or unsupported answer points to a page
  that needs writing or fixing.


## How it works (plain words)

- **The corpus is a small set of text files on a public web site.** One of them, `llms.txt`, is a
  table of contents: a short intro, then a list of links, each with one line saying what that page
  answers. The other files are the pages it points to.
- **The FM (the AI model) cannot browse on its own.** It only sees the text we hand it in a
  request. It has no memory of the corpus between requests.
- **The client is a short program that does the fetching for the FM.** It runs on your laptop. It
  talks to the web site (to get pages) and to Bedrock (to talk to the FM).
- **Step 1:** the client downloads `llms.txt` and sends it to the FM along with your question, so
  the FM knows what pages exist and what each one covers.
- **Step 2:** the client also tells the FM it has one tool, `fetch_doc`, which can get any page on
  the list. The FM reads the table of contents and asks for the pages it thinks it needs, e.g.
  "fetch `flort.md`".
- **Step 3:** the client sees that request, downloads the page, and sends its text back to the FM.
  This can repeat a few times (the FM may ask for two or three pages).
- **Step 4:** once the FM has what it needs, it writes the answer, naming the pages (and the
  original sources they cite) it used.
- **Why not just send every page every time?** We could while the corpus is tiny. The table of
  contents lets the corpus grow large while each answer reads only the few pages that matter.
- **Why this is the "lightest lift":** no server to run, no database, no search index. The web site
  is static files; the "intelligence" is the FM; the client is ~50 lines.
- **Any AI can use the same corpus.** A scientist can skip our client entirely and tell their own
  AI: *"Use https://robfatland.github.io/prototype-userguide/llms.txt to answer my questions."*
  Our client exists to show the pattern working end to end and to test answer quality.
- **Safety rule in the client:** `fetch_doc` only fetches from the corpus site, never arbitrary
  URLs, so the FM can't be steered into reading untrusted pages.


## Decisions

- **Hosting:** GitHub Pages, from this repo's `docs/` folder (with `.nojekyll`, so `.md` and `.txt`
  files are served as plain text). No AWS bucket. Corpus URL:
  `https://robfatland.github.io/prototype-userguide/llms.txt`.
- **Repo:** `robfatland/prototype-userguide` — separate from `argosy` (argosy's Pages site is its
  Jupyter Book, and this guide serves a different, broader audience). Name avoids any program name
  to avoid implying affiliation.
- **FM access:** Amazon Bedrock, Converse API, from the client on the laptop. The only AWS piece.
- **Sources** (the corpus summarizes and links to these; it does not mirror them):
  1. The observatory program website (data product pages, instrument pages, DPS PDFs, Data
     Explorer, ERDDAP, knowledge base).
  2. Interactive Oceans (instrument pages, Data Portal).
  3. The Zenodo `nsf-ooi` community (25+ records).
  Also: BGC Best Practices & User Guide, `ooi-data-explorations`, the program's Discourse forum.


## Corpus structure (`docs/`)

Three kinds of page, all listed in `llms.txt`:

| Kind | Who writes it | Purpose |
|---|---|---|
| **Guides** | curated by hand | The missing practical layer: what's in a delivered file, which variable is the science variable, what the QC flags mean, what to distrust, how to get the data. Each claim links to its source. |
| **Reference indexes** | curated by hand | Link lists into the program website and Interactive Oceans, with one-line summaries (summarize, don't copy). Needed because some source pages render only with JavaScript and can't be fetched as text. |
| **Dataset catalog** | generated by script | The Zenodo `nsf-ooi` records (title, author, size, whether code/docs are included, related repos, DOI), regenerated from the Zenodo API. |

**Writing rule — rate every caveat by impact on data use.** Many issues are built into data use;
some matter, many don't. Each caveat in a guide page carries a tag:

- **[HIGH]** will mislead an analysis if ignored (e.g. using L1 angular scattering as
  backscatter; discarding data on a misleading QC test).
- **[MEDIUM]** matters for some analyses (e.g. total vs particulate backscatter).
- **[LOW — report to data team]** a real system/documentation defect, but it doesn't block use
  because the delivered product is usable (e.g. empty L1 calibration fields — worth an inquiry to
  the data team, but researchers start from the delivered L1, not from raw counts).

The rating is what makes a page a *user guide* rather than a defect list: it tells the scientist
what to act on now and what to merely know about.


## Scope and phasing

The goal is a scientist's user guide. The client is generic and doesn't change; reach grows with
the corpus. So phases are defined by corpus coverage, each with a test bank of questions.

- **v0:** data access routes; QARTOD / QC flags; currents (velocity products, ADCP); the
  3-wavelength fluorometer (FLORT); the Zenodo catalog. Test bank ≈ 15 questions, including the
  three that motivated this:
  - "What current data exist, and at which sites?"
  - "Is there code that takes downloaded velocity data from a shallow profiler to currents?"
  - "How do I interpret a delivered FLORT dataset — which variables, which QC flags, what to
    distrust?"
- **Later:** one instrument guide at a time (CTD, dissolved oxygen, pH, pCO₂, nitrate, PAR, …),
  each adding test questions. Each new guide page also documents a concrete gap.


## Client (`client/ask.py`) — design sketch

```python
import boto3, urllib.request

BASE = "https://robfatland.github.io/prototype-userguide/"
MODEL_ID = "<a Bedrock model / inference-profile ID enabled in your account>"
REGION = "us-west-2"

brt = boto3.client("bedrock-runtime", region_name=REGION)

def fetch_doc(path):
    """Fetch a corpus page. Allowlisted to BASE only (no arbitrary URLs)."""
    if "://" in path or ".." in path:
        return "ERROR: path outside corpus"
    with urllib.request.urlopen(BASE + path.lstrip("/"), timeout=20) as r:
        return r.read().decode("utf-8")[:50_000]

TOOLS = {"tools": [{"toolSpec": {
    "name": "fetch_doc",
    "description": "Fetch a page from the user-guide corpus by the relative path listed in llms.txt.",
    "inputSchema": {"json": {"type": "object",
                             "properties": {"path": {"type": "string"}},
                             "required": ["path"]}}}}]}

SYSTEM = [{"text": "Answer ocean-observatory data questions using ONLY the corpus. Read llms.txt, "
                   "fetch the pages you need, cite page names and their sources, and say so if "
                   "the corpus does not cover the question."}]

def ask(question):
    msgs = [{"role": "user", "content": [
        {"text": "llms.txt:\n" + fetch_doc("llms.txt")},
        {"text": question}]}]
    for _ in range(6):                                   # cap tool-use rounds
        resp = brt.converse(modelId=MODEL_ID, system=SYSTEM, messages=msgs, toolConfig=TOOLS)
        out = resp["output"]["message"]
        msgs.append(out)
        if resp["stopReason"] != "tool_use":
            return "".join(b.get("text", "") for b in out["content"])
        results = [{"toolResult": {"toolUseId": b["toolUse"]["toolUseId"],
                                   "content": [{"text": fetch_doc(b["toolUse"]["input"]["path"])}]}}
                   for b in out["content"] if "toolUse" in b]
        msgs.append({"role": "user", "content": results})
    return "(stopped: too many tool rounds)"
```

Usage: `python client/ask.py "What current data exist at shallow profiler sites?"`


## Prerequisites (Bedrock)

1. **Model access:** enable the chosen FM in the Bedrock console (`us-west-2`). Newer models are
   invoked by **inference-profile ID** (e.g. a `us.`-prefixed ID) — copy the exact ID into
   `MODEL_ID`.
2. **IAM:** the caller needs `bedrock:InvokeModel` (used by Converse) on that model / profile. Use
   the existing AWS CLI profile; no keys in code.
3. **Python:** only `boto3`. Use a small dedicated env (e.g. `userguide`), not a large analysis env.
4. **Cost:** Pages is free; Bedrock is per-token — a test-bank run is cents.


## Build steps

1. ~~Create repo `robfatland/prototype-userguide`; enable Pages from `docs/`.~~ (done)
2. Write v0 guide pages + reference indexes in `docs/`; list them in `docs/llms.txt`.
3. Write the Zenodo catalog generator (`tools/zenodo_catalog.py`) → `docs/datasets.md`.
4. Write `client/ask.py`; enable Bedrock model access; run the test bank.
5. Record results below; fix corpus gaps; repeat.
6. Bonus: give the same `llms.txt` URL to a consumer AI (ChatGPT, Claude, Kiro) and compare.


## Prototype build to-dos

**Verify (corpus accuracy — before relying on the FLORT page):**

- [ ] Roesler et al. 2017 DOI `10.1002/lom3.10185` and the "factor of 2" summary.
- [ ] Daytime-quenching wording (and whether the BGC Best Practices guide is the right cite).
- [ ] CDOM ppb calibration-standard wording ("relative to the factory calibration standard").
- [ ] `oceanobservatories/asset-management` link and that FLORT calibrations are findable there.
- [ ] Generality: FLORT findings come from ONE file (SB, deployment 4, Jan 2018). Spot-check a
      second deployment/site (all-zero calibration fields; stuck-value failure rates).

**Report to data team (LOW-impact defects found so far):**

- [ ] FLORT: `signal_*_offset` / `signal_*_scale_factor` all zero in a delivered file.
- [ ] FLORT: backscatter angle 117° (file comment) vs 124° / χ = 1.076 (ION/DPS) — which applied?

**Build:**

- [x] AWS profile `securecomputing` (account 084375582624), `us-west-2`, model
      `us.anthropic.claude-sonnet-4-6` — test call OK; no IAM or console changes needed.
- [x] `client/ask.py` written; first FLORT question run (see Results).
- [ ] Run the remaining FLORT questions; record results.
- [ ] Draft the v0 test bank (≈ 15 questions).
- [ ] Remaining v0 pages: data access, QC flags, currents, two reference indexes.
- [ ] `tools/zenodo_catalog.py` → `docs/datasets.md`.


## Open questions

- Which FM (and whether to compare two).
- The full v0 test bank (≈ 15 questions).


## Results

Format: question → pages fetched → tokens → verdict → corpus fixes made.

**R1 (FLORT).** *"I downloaded a FLORT file from a shallow profiler. Which variable should I use
for backscatter, and should I throw out samples whose qc_results show a failed test?"*

- Fetched: `flort.md` only. Tokens: 7,186 in / 898 out (a few cents).
- Verdict: **good.** Correct variable (`optical_backscatter`, L2) with the [HIGH] L1 warning and
  the `b_bp` formula; correct "don't discard on stuck-value alone"; carried impact ratings;
  cited page + primary sources; added relevant shallow-profiler caveats unprompted.
- Errors: (1) FM stated a 0 bit in `qc_results` "means the test ran and failed" (should be
  "failed or not run"). (2) Corpus weakness surfaced: the page attributed stuck-value failures to
  quantization, which fits chlorophyll but not backscatter (~75 counts above dark, 99% failures).
- Fixes: `flort.md` now separates chlorophyll (quantization) from backscatter (likely threshold),
  and states the 0-bit = "failed or not run" rule explicitly.
