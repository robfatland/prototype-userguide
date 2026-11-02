# prototype-userguide — design

A self-funded, standalone prototype of the lightest-lift way to give scientists an AI-usable
**user guide** for ocean-observatory data: publish a curated, AI-readable corpus (`llms.txt` +
plain markdown pages) on GitHub Pages, and show that a foundation model (FM), reached through
Amazon Bedrock, answers practical data questions well using only that corpus.

**Unofficial.** Not affiliated with, endorsed by, or funded by any observatory program. Every
page links to its primary sources; where this guide and an official source disagree, the official
source wins.

Status (Nov 2026): **working demo.** Corpus live on GitHub Pages with three guide pages:
`shallow-profiler.md` (operations, daily index, profile index / GPI, redux), `ctd.md` (CTD + DO),
`nitrate.md`, and `flort.md` — each grounded in real delivered files / verified data, with
impact-rated caveats. Bedrock client (`client/ask.py`, Sonnet 4.6 via profile `securecomputing`)
answers end-to-end; tests R1–R4 passed (R4: first multi-page synthesis), with every error fed back
into the corpus or the client prompt. v1 in progress: pH, pCO₂, PAR next. Remaining v0 pages (data access, QC flags, currents,
reference indexes, Zenodo catalog) not yet written.


## How to install and operate a Python Client

You don't need our client at all — any AI that can read a URL can use the corpus (see "How it
works" below). This client exists to run the loop under your control, on Amazon Bedrock.

**Install (once):**

1. **Python 3.9+** with `boto3` (≥ 1.34, for the Converse API). Any env works; a small dedicated
   one keeps things clean:
   ```bash
   conda create -n userguide python=3.11 boto3 -y   # or: python -m venv .venv && pip install boto3
   conda activate userguide
   ```
2. **Get the client:** `git clone https://github.com/robfatland/prototype-userguide` (or just
   download `client/ask.py` — it's one file, no other dependencies).
3. **AWS credentials** with Bedrock access, configured as a named AWS CLI profile
   (`aws configure --profile <name>`). Never put keys in code.
4. **Model access:** in the Bedrock console, in your region, make sure the model is available to
   your account. Newer models are invoked by **inference-profile ID** (e.g.
   `us.anthropic.claude-sonnet-4-6`).
5. **Check it works** (a few tokens, a fraction of a cent):
   ```bash
   aws bedrock-runtime converse --profile <name> --region us-west-2 \
     --model-id us.anthropic.claude-sonnet-4-6 \
     --messages '[{"role":"user","content":[{"text":"Reply with exactly: OK"}]}]' \
     --inference-config '{"maxTokens":10}' --query 'output.message.content[0].text'
   ```
   `OK` back = model access and IAM are fine. `AccessDeniedException` = your IAM identity needs
   `bedrock:InvokeModel` on the inference profile and its models.

**Operate:**

```bash
cd prototype-userguide
python client/ask.py "Which FLORT variable should I use for backscatter?"
python client/ask.py -v "How do I read QARTOD flags?"     # -v: show pages fetched + tokens
```

Settings (environment variables; defaults in brackets):

| Variable | Meaning | Default |
|---|---|---|
| `USERGUIDE_AWS_PROFILE` | AWS CLI profile | `securecomputing` |
| `USERGUIDE_AWS_REGION` | Bedrock region | `us-west-2` |
| `USERGUIDE_MODEL_ID` | model / inference profile | `us.anthropic.claude-sonnet-4-6` |
| `USERGUIDE_BASE_URL` | corpus root | `https://robfatland.github.io/prototype-userguide/` |

Cost: a typical question uses ~5–10k input tokens and ~1k output — a few cents with Sonnet.
To test unpublished corpus edits, serve `docs/` locally (`python -m http.server -d docs 8000`) and
set `USERGUIDE_BASE_URL=http://localhost:8000/`.


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


## How it works

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
  4. **Hands-on project experience: the `argosy` repo**
     ([robfatland/argosy](https://github.com/robfatland/argosy)) — years of working with
     shallow-profiler data: sensor sampling modes, QC findings, exclusion windows, filtering
     choices. Used as a source of *practical* knowledge the official docs lack, labeled as
     project experience (not official) and linked.
  5. **Real delivered files** (OOINET source NetCDF): each instrument guide is grounded in one
     inspected file — variable inventory, flag counts, calibration fields, signal levels.


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
  3-wavelength fluorometer (FLORT, **done**); the Zenodo catalog. Test bank ≈ 15 questions,
  including the three that motivated this:
  - "What current data exist, and at which sites?"
  - "Is there code that takes downloaded velocity data from a shallow profiler to currents?"
  - "How do I interpret a delivered FLORT dataset — which variables, which QC flags, what to
    distrust?"
- **v1 (PROPOSED — awaiting go-ahead):** the rest of the shallow-profiler sensor suite, one guide
  page each, same recipe as FLORT (inspect one real delivered Slope Base file + DPS/ION + argosy
  experience; impact-rate every caveat; 3–4 test questions per page):
  1. `ctd.md` — CTD incl. dissolved oxygen (foundation: depth, T, S, density, DO feed every other
     sensor's corrections). Source file ~480 MB.
  2. `nitrate.md` — SUNA nitrate. Source file ~50 MB.
  3. `ph.md` — pH (SAMI). Source file ~2 MB.
  4. `pco2.md` — pCO₂ (SAMI), incl. its separate calibration-record stream. Source file ~2 MB.
  5. `par.md` — PAR. Source file ~560 MB.
- **Later:** remaining v0 pages, other platforms (moorings, gliders), other instrument classes.
  Each new guide page also documents a concrete gap.


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
- [x] v1 `ctd.md` (CTD + DO) written, grounded in a real file; R2 passed.
- [x] v1 `nitrate.md` written (deployment-6 file); R4 cross-page test passed.
- [ ] v1 `par.md`.
- [ ] Report to data team (LOW): nitrate instrument clock fields (`internal_timestamp`,
      `date_of_sample`) lag `time` by weeks–months from ~Oct 2018 in deployment 6.
- [ ] Verify: SUNA accuracy/drift wording ("offsets of a few µmol L⁻¹") against the BGC Best
      Practices nitrate chapter.
- [x] Client system prompt: exact ratings, corpus-only URLs, keep qualifiers (after R2a/R2b/R3).
- [x] `shallow-profiler.md` written (platform, phases + verified durations, daily index in the
      UTC day, profile index / GPI + slicing code, redux convention, UTC); R3 passed.
- [ ] Re-run R2/R3 with the new system prompt to confirm rating drift is gone.
- [x] argosy `SensorTable.md`: PCO2W corrected to Sunburst SAMI-CO2 (verified from the delivered
      variables: 434/620 nm absorbances + blanks).
- [ ] argosy fixes still open: `plume/ColumbiaPlumePlan.md` gives oo latitude 44.66 (code uses
      44.374); `Sharding.md` says daily index 8 has an extended descent (2024 index shows only #4
      and #9 do).
- [x] v1 `ph.md`, `pco2.md` written (deployment-6 files; sampling verified per sample).
- [ ] Verify: pH scale and reference temperature of PHWATER_L2 (from the pH DPS); the "pH + pCO₂
      is a poor pair for TA/DIC" statement (cite a carbonate-system error-propagation source).
- [ ] Report to data team (LOW): pH `phsen_thermistor_temperature` labeled V but holds °C;
      `internal_timestamp` zero in pH and pCO₂ files.
- [ ] Process rule: never batch a page write and its `git commit`; verify the page is tracked and
      served (HTTP 200) before adding it to `llms.txt`.
- [ ] Draft the v0 test bank (≈ 15 questions).
- [ ] Remaining v0 pages: data access, QC flags, currents, two reference indexes.
- [ ] `tools/zenodo_catalog.py` → `docs/datasets.md`.


## Open questions

- Which FM (and whether to compare two).
- The full v0 test bank (≈ 15 questions).


## Results

### FLORT backscatter query

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

**R2a (CTD, page missing — accidental robustness test).** *"I want to compute mixed layer depth
from shallow profiler CTD data at Slope Base. Which variables should I use, and what pitfalls
should I watch for?"* — asked while `ctd.md` was listed in `llms.txt` but not yet published (a
write/commit race; fixed).

- Fetched: `ctd.md` → HTTP 404. Tokens: 3,315 in / 827 out.
- Verdict: **good failure behavior.** Reported the 404, answered only from the index summary,
  refused to guess variable names, said so plainly. One flaw: offered an unverified OOI URL
  (`/data-product/ctdpff/`) as a fallback.
- Lesson: an index entry must never point at an unpublished page; and the system prompt should
  forbid citing URLs that aren't in the corpus.

**R2b (CTD, same question, page live).**

- Fetched: `ctd.md` only. Tokens: 6,555 in / 1,369 out.
- Verdict: **good.** Correct variables; the [HIGH] in-situ-density warning with the GSW σ₀ recipe;
  split the stream with profileIndices; ascent only; conductivity-fouling windows; stuck-value
  warning; sensible 6-step workflow; cited sources.
- Errors: promoted two [MEDIUM] caveats to [HIGH] (rating drift). Gap: no MLD *method* guidance
  in the corpus, so the answer stopped at "apply your MLD algorithm".
- Fixes: `ctd.md` gains an MLD section (de Boyer Montégut 2004 threshold; Holte & Talley 2009
  hybrid; reference-depth caveat; the argosy hand-labeled MLD set on Zenodo).

**R3 (shallow-profiler operations).** *"I have a month-long nitrate file from the Slope Base
shallow profiler. How do I pull out the individual nitrate profiles, and why do I only see two per
day?"*

- Fetched: `shallow-profiler.md` only. Tokens: 6,342 in / 1,037 out.
- Verdict: **good.** Correct "nitrate runs on #4 and #9"; the [HIGH] "don't find #4/#9 by
  counting" warning with the long-descent test; profile-index URL + slicing code; GPI as the
  cross-sensor key; pointed to redux as optional.
- Errors: dropped the "from 2017 on" qualifier; attached a [HIGH] rating to a statement the page
  leaves unrated (second instance of rating drift, after R2b).
- Fixes: client system prompt now requires ratings copied exactly (never raised/lowered/invented),
  only URLs present in fetched pages, and page qualifiers kept (dates, "in the example file",
  "project experience").
- **R3b (re-run with the stricter prompt):** "from 2017 onward" now kept ✓; the FM still rated
  the duty-cycle statement [HIGH]. Judgment: the FM was right that it is high-impact — the gap
  was the page leaving it unrated. Fix: `shallow-profiler.md` now rates it [HIGH]. Lesson: when
  the FM consistently "drifts" a rating, check whether the page under-rates the claim before
  blaming the model.

**R4 (nitrate + CTD, cross-page synthesis).** *"I want to compare nitrate and dissolved oxygen
profiles from the Slope Base shallow profiler to study remineralization. Which variables do I
use, how do I match them up, and what should I watch out for?"*

- Fetched: `nitrate.md`, `ctd.md`, `shallow-profiler.md` (chosen by the FM). Tokens: 13,374 in /
  1,888 out (~10 cents).
- Verdict: **very good — first multi-page synthesis.** Correct variables from both instruments;
  the µmol L⁻¹ vs µmol kg⁻¹ conversion with in-situ density (the right density for a volume
  conversion); restrict CTD to the same #4/#9 GPIs, slice both by `start→peak`, bin to a common
  depth grid; bottle-check caveat; near-zero negatives; nitrate inherits CTD fouling; oxygen lag;
  σ₀ for density surfaces; stuck-value warning; use `time`.
- Errors: minor rating slip — the [LOW] instrument-clock issue was folded under a [HIGH] "Time"
  heading. No factual errors found.
- Fixes: none needed to the corpus.



### FLORT Chlor-a query


`(environ-name) username$ python client/ask.py -v "from an ooinet flort data product that I downloaded: what data variable should I use for scientific interpretation from the triplet fluorometer chlorophyll-a? And what should I expect concerning the nature of the data?"`


fetch_doc = `https://robfatland.github.io/prototype-userguide/flort.md`


[tokens: 7312 in / 993 out]


#### Variable to use for chlorophyll-a


Use **`fluorometric_chlorophyll_a`** (product code **CHLAFLO_L1**, units µg L⁻¹). This is the science-ready L1 variable. Do **not** use the raw count variable `raw_signal_chl` (L0), and do **not** confuse it with the backscatter intermediates.


---


#### What to expect — key caveats (in priority order)


##### [HIGH] It is a fluorescence *estimate*, not a direct chlorophyll measurement — and it runs ~2× high
Factory-calibrated ECO Triplet (FLORT) chlorophyll fluorescence overestimates extracted chlorophyll by roughly **a factor of 2 on average** globally (Roesler et al. 2017, *L&O Methods*, doi:10.1002/lom3.10185). This matters for absolute values; relative spatial/temporal patterns are still useful.

##### [HIGH] Daytime near-surface values read *low* due to non-photochemical quenching (NPQ)
In bright near-surface light, phytoplankton suppress fluorescence. Daytime near-surface chlorophyll is systematically underestimated. Compare night profiles or apply an NPQ correction.

##### [HIGH] Low signal → coarse quantization steps
Raw output is integer counts; one count = **0.0115 µg L⁻¹** per step. In the deep or in clear water the signal is only a handful of counts above dark (median ~6 counts above dark in the example file; below ~100 m the signal is essentially dark + noise). Small **negative values** (e.g. −0.046 µg L⁻¹) are dark-count noise, not real chlorophyll. **Smooth or bin the data** (e.g. Savitzky–Golay filter or depth bins) before interpreting fine structure.

##### [HIGH for long deployments] Biofouling drift
Profiler and moored instruments without a wiper accumulate biofouling over a deployment, causing a slow upward drift in signal. Compare early vs. late deployment periods and use the `deployment` variable when stitching files.

##### [HIGH] Stuck-value QC failures are misleading — don't discard on that basis alone
The OOI automated QC `*_qc_results` bit-mask flags ~49% of chlorophyll samples as "stuck-value failures." This is largely an artifact of the low-signal quantization (repeated identical integer count values), not genuinely bad data. Use `qc_executed` alongside `qc_results` to distinguish tests that ran-and-failed from tests that simply didn't run.

---

#### Quick practical checklist

| Step | Action |
|---|---|
| Variable | `fluorometric_chlorophyll_a` |
| Absolute calibration | Expect ~2× overestimate vs. extracted Chl; apply Roesler et al. 2017 if needed |
| NPQ | Exclude or correct daytime near-surface data |
| Low signal / quantization | Bin or smooth; treat negatives as zero |
| QC flags | QARTOD summary flag 4 = probably bad; flag 3 = "look closer". Ignore stuck-value-only failures |
| Biofouling | Compare early vs. late deployment |

---

**Source:** [FLORT page, prototype-userguide](https://robfatland.github.io/prototype-userguide/flort.md), citing OOI DPS 1341-00530 (CHLAFLO), Roesler et al. 2017 (*L&O Methods*), ION FLO processing functions, and the OOI Biogeochemical Sensor Data Best Practices & User Guide v1.1.1.
