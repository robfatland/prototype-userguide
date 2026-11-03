# prototype-userguide — design

A self-funded, standalone prototype of the lightest-lift way to give scientists an AI-usable
**user guide** for ocean-observatory data: publish a curated, AI-readable corpus (`llms.txt` +
plain markdown pages) on GitHub Pages, and show that a foundation model (FM), via Amazon Bedrock,
answers practical data questions well using only that corpus.

**Unofficial.** Not affiliated with, endorsed by, or funded by any observatory program. Every page
links to its primary sources; where this guide and an official source disagree, the official
source wins.

**Status (Nov 2026): working demo.** Seven guide pages live on GitHub Pages —
`shallow-profiler.md` (operations: daily index, profile index / GPI, redux), `ctd.md` (CTD + DO),
`nitrate.md`, `ph.md`, `pco2.md`, `par.md`, `flort.md` — each grounded in a real delivered file,
with impact-rated caveats. The Bedrock client (`client/ask.py`, Sonnet 4.6) answers end to end;
the **full test bank (T1–T18) passes** — all 16 in-scope questions and both out-of-scope checks
(see Results), each error found along the way fed back into the corpus or the client prompt. All
shallow-profiler scalar sensors are now covered. Not yet written: data-access, QC-flags, and
currents pages; the two reference indexes; the Zenodo catalog.


## How it works

- The corpus is a few plain-text files on a public web site. One, `llms.txt`, is a table of
  contents: a short intro plus a list of links, each with one line on what that page answers. The
  rest are the pages.
- The FM can't browse and has no memory between requests — it only sees text we hand it.
- `client/ask.py` does the fetching. It sends `llms.txt` plus the question, exposes one tool
  (`fetch_doc`), lets the FM request the pages it needs (a few rounds), then returns the answer
  with citations.
- A table of contents (not sending every page) lets the corpus grow while each answer reads only
  the pages that matter. No server, no database, no search index — the "intelligence" is the FM;
  the client is ~100 lines.
- Any AI can use the same corpus directly: *"Use https://robfatland.github.io/prototype-userguide/llms.txt
  to answer my questions."* The client just runs the loop under our control so we can measure
  answer quality.
- Safety: `fetch_doc` only fetches from the corpus site, so the FM can't be steered to untrusted
  pages.


## What problem this solves — and what the FM does

Existing observatory docs are **labyrinthine** (hard to navigate) and **unhelpful as a user guide**
(even when found, they don't say which variable to use, what the QC flags mean, or what to
distrust).

- The guide pages are where the missing user-guide content is **written by hand** — that is the
  contribution, and it fixes the "unhelpful" problem. The two reference-index pages are link lists
  into external sites; they address the "labyrinthine" problem.
- The FM's job is narrow: find the right page(s) and answer from them, with citations. **It does
  not supply the expertise** — if a page is thin, the FM fills the gap with guesses, which is
  exactly what the test bank catches.


## Decisions

- **Hosting:** GitHub Pages from `docs/` (with `.nojekyll`, so `.md`/`.txt` serve as plain text).
  No AWS bucket. Corpus root: `https://robfatland.github.io/prototype-userguide/`.
- **Repo:** `robfatland/prototype-userguide`, separate from `argosy` (which publishes its own
  Jupyter Book). The name avoids any program name, to avoid implying affiliation.
- **FM access:** Amazon Bedrock, Converse API, run from the laptop — the only AWS piece.
- **Sources** (summarized and linked, not mirrored): (1) the observatory program website (product
  and instrument pages, DPS PDFs, Data Explorer, ERDDAP, knowledge base); (2) Interactive Oceans
  (instrument pages, Data Portal); (3) the Zenodo `nsf-ooi` community; plus the BGC Best Practices
  guide, `ooi-data-explorations`, and the Discourse forum; (4) **the `argosy` repo** — years of
  hands-on shallow-profiler work (sampling modes, QC findings, exclusion windows), used for
  *practical* knowledge the official docs lack, labeled "project experience" and linked; (5)
  **real delivered files** — each instrument page is grounded in one inspected OOINET NetCDF
  (variable inventory, flag counts, calibration fields, signal levels).


## Corpus structure (`docs/`)

Three kinds of page, all listed in `llms.txt`:

| Kind | Author | Purpose |
|---|---|---|
| **Guides** | by hand | The practical layer: what's in a file, which variable is the science one, what the QC flags mean, what to distrust, how to get the data. Each claim linked to its source. |
| **Reference indexes** | by hand | Annotated link lists into the program website and Interactive Oceans (summarize, don't copy; some source pages are JavaScript-only and can't be fetched as text). |
| **Dataset catalog** | by script | The Zenodo `nsf-ooi` records (title, author, size, code/docs present, DOI), regenerated from the Zenodo API. |

**Writing rules (learned from the test bank):**

- **Rate every caveat by impact.** `[HIGH]` will mislead an analysis if ignored; `[MEDIUM]`
  matters for some analyses; `[LOW — report to data team]` is a real defect that doesn't block use
  (the delivered product is usable). The rating is what makes a page a *guide* rather than a defect
  list.
- **Inline every `[HIGH]` rule where it applies** — don't rely on the FM following a link to
  another page for it (R5).
- **When two sensors behave similarly but differently, say how they differ explicitly** — or the
  FM may merge them (R5).


## Scope and phasing

The client is generic and fixed; reach grows with the corpus.

- **Done:** all shallow-profiler scalar sensors (CTD + DO, FLORT, nitrate, pH, pCO₂, PAR) and the
  operations page, each grounded in a real Slope Base file.
- **Next:** the remaining general pages — data access, QC flags, currents — and the two reference
  indexes; the Zenodo catalog generator (`tools/zenodo_catalog.py` → `docs/datasets.md`).
- **Later:** other platforms (moorings, gliders) and instrument classes.


## Install and operate the client

Any AI can use the corpus from its URL; this client runs the loop on Bedrock under your control.

**Install (once):**

1. Python 3.9+ with `boto3` (≥ 1.34). A small dedicated env keeps things clean:
   `conda create -n userguide python=3.11 boto3 -y`.
2. `git clone https://github.com/robfatland/prototype-userguide` (or just grab `client/ask.py` —
   one file, no other dependencies).
3. AWS credentials with Bedrock access as a named CLI profile (`aws configure --profile <name>`);
   no keys in code. The caller needs `bedrock:InvokeModel` on the inference profile and its models.
4. In the Bedrock console (your region), confirm the model is available. Newer models use an
   **inference-profile ID**, e.g. `us.anthropic.claude-sonnet-4-6`.
5. Smoke test (a fraction of a cent):
   ```bash
   aws bedrock-runtime converse --profile <name> --region us-west-2 \
     --model-id us.anthropic.claude-sonnet-4-6 \
     --messages '[{"role":"user","content":[{"text":"Reply with exactly: OK"}]}]' \
     --inference-config '{"maxTokens":10}' --query 'output.message.content[0].text'
   ```
   `OK` → access and IAM are fine. `AccessDeniedException` → the IAM policy is missing.

**Operate:**

```bash
python client/ask.py "Which FLORT variable should I use for backscatter?"
python client/ask.py -v "How do I read QARTOD flags?"   # -v: show pages fetched + tokens
```

Settings (environment variables, defaults in brackets): `USERGUIDE_AWS_PROFILE`
[`securecomputing`], `USERGUIDE_AWS_REGION` [`us-west-2`], `USERGUIDE_MODEL_ID`
[`us.anthropic.claude-sonnet-4-6`], `USERGUIDE_BASE_URL`
[`https://robfatland.github.io/prototype-userguide/`].

- **Cost:** ~$0.04–0.08 per query (Sonnet 4.6, third-party-listed $3.30 / $16.50 per M input /
  output tokens; confirm in billing). Prompt caching or the `global.` profile would cut it.
- **Testing unpublished edits:** serve `docs/` locally
  (`python -m http.server -d docs 8000`) and set `USERGUIDE_BASE_URL=http://localhost:8000/`.


## Test bank

Each test lists the pages a good answer should draw on and the **must-include facts** (pass = all
present, nothing contradicted, ratings not raised or invented, no URL outside the corpus). "Run"
marks tests executed (see Results). T17–T18 are **out-of-scope** checks: the correct answer says
the corpus doesn't cover it, without guessing. T1–T16 cover all seven pages; seven are cross-page.

| # | Question | Pages | Must include | Run |
|---|---|---|---|---|
| T1 | Which FLORT variable is backscatter, and how do I get particulate backscatter? | flort | `optical_backscatter` (L2); [HIGH] not `total_volume_scattering_coefficient` (L1); `b_bp = optical_backscatter − seawater_scattering_coefficient/2` | R1 |
| T2 | Half my chlorophyll samples fail `qc_results`. Should I drop them? | flort | mostly stuck-value; decode with `qc_executed`; 0 bit = failed *or not run*; [HIGH] don't discard on stuck-value alone | ✓ |
| T3 | Is the CDOM in OOI fluorometer files really a CDOM concentration? | flort | fluorescence → FDOM proxy; ppb relative to factory standard; treat as relative index | ✓ |
| T4 | Can I compare OOI fluorometer chlorophyll with bottle or satellite chlorophyll? | flort | ~2× factory overestimate (Roesler 2017); daytime quenching; low-signal quantization; relative vs absolute | R-Chl |
| T5 | How do I compute mixed layer depth from shallow profiler CTD data? | ctd, shallow-profiler | [HIGH] density is in-situ → compute σ₀ with GSW; split stream with profile index; ascent; fouling windows; threshold/H&T methods; reference-depth caveat | R2 |
| T6 | Salinity at Slope Base drops ~2 PSU for a week one December. Plume or bad data? | ctd | conductivity-cell fouling events (project-experience dates); check temperature unchanged + conductivity QARTOD suspect; salinity can pass its own QC | ✓ |
| T7 | Do I need a separate oxygen download for the shallow profiler? Which variable and units? | ctd | DO is in the CTD stream; `corrected_dissolved_oxygen`; µmol kg⁻¹; duplicate DOCONCF variable | ✓ |
| T8 | How do I pull individual profiles out of a month-long file? What is a GPI? | shallow-profiler | profile index repo + `start/peak/end` (UTC); slicing code; GPI = running profile number, unique per profiler; check empty slices | R3 |
| T9 | How do I find the midnight and noon profiles? | shallow-profiler | #4 and #9 (UTC-day index); [HIGH] identify by long descent (~95 vs ~34 min), not by counting; #4 ≈ 08:30 UTC, #9 ≈ 21:50 UTC | ✓ |
| T10 | Compare nitrate and oxygen profiles for remineralization. | nitrate, ctd, shallow-profiler | `salinity_corrected_nitrate`; µmol L⁻¹ vs µmol kg⁻¹ conversion; match #4/#9 GPIs, ascent, common depth grid; bottle-check caveat | R4 |
| T11 | Why does my corrected nitrate go negative near the surface? | nitrate | T/S correction near true zero; ~1% of values; treat as ≈ 0; don't drop (bias); global-range "failures" = negatives | ✓ |
| T12 | How do I get clean pH and pCO₂ profiles, and can I compute the carbonate system? | ph, pco2 | descents of #4/#9, `peak → end`; ~12–13 readings; off-profile ~190 m samples differ (pH one per profile vs pCO₂ parked); QARTOD screening; pH + pCO₂ poor pair for TA/DIC | R5 |
| T13 | What is the pCO₂ `_cal` file and do I need it? | pco2 | blank measurements, ~1 per 5 days; already applied in the data file; only for diagnosing blank drift | ✓ |
| T14 | Estimate light attenuation and euphotic depth from PAR and relate it to chlorophyll. | par, flort | `par_counts_output`; ignore PAR QARTOD; dark threshold before logs; daylight profiles by local solar time; Kd from ln(PAR); surface not reached; quenching interaction | R6 |
| T15 | Every PAR sample is flagged as failed. Is the PAR data bad? | par | QARTOD runs on raw counts → fails all; calibrated variable has no QARTOD; [HIGH] ignore that flag; negatives = darkness | ✓ |
| T16 | Does the profiler always reach the surface? How does that affect MLD and surface PAR? | ctd, par, shallow-profiler | shallowest point often 5–20 m (~15 m in the Jan example); check reference depth before MLD threshold; extrapolate surface PAR | ✓ |
| T17 | *(out of scope)* How do I get ADCP current data for the Slope Base shallow profiler? | — | says the corpus doesn't yet cover currents (planned page); no invented variable names or URLs | ✓ |
| T18 | *(out of scope)* What are typical oxygen values at 2,000 m on the Axial Base deep profiler? | — | says the corpus covers shallow profilers only; no guessed values | ✓ |


## Results

Format: question → pages fetched → tokens → verdict → fixes. "R-Chl" and the "R2a/R3b" sub-runs
are variants recorded where useful.

**R1 (T1, FLORT).** *Which variable for backscatter, and should I drop QC-failed samples?*
Fetched `flort.md`; 7,186 / 898 tokens. **Good:** `optical_backscatter` (L2) with the [HIGH] L1
warning and `b_bp` formula; "don't discard on stuck-value alone"; ratings + citations carried;
added shallow-profiler caveats unprompted. **Errors:** (1) said a 0 bit means "ran and failed"
(should be "failed *or not run*"); (2) the page wrongly blamed quantization for backscatter's
99% stuck-value rate. **Fixes:** `flort.md` separates chlorophyll (quantization) from backscatter
(threshold) and states the 0-bit rule.

**R-Chl (T4, FLORT).** *Which chlorophyll variable, and what to expect?* Fetched `flort.md`;
7,312 / 993 tokens. **Good:** `fluorometric_chlorophyll_a` (L1); the ~2× overestimate (Roesler
2017), NPQ, quantization, biofouling, and stuck-value caveats, all impact-rated and cited.
No corpus fix needed.

**R2 (T5, CTD).** *Mixed layer depth from CTD.*
- *R2a (page not yet published — accidental robustness test):* `ctd.md` → HTTP 404; the FM
  reported the 404, answered from the index summary only, refused to guess, but offered one
  unverified OOI URL. Lessons: never point `llms.txt` at an unpublished page; forbid citing URLs
  not in the corpus.
- *R2b (page live):* 6,555 / 1,369 tokens. **Good:** [HIGH] in-situ-density warning + GSW σ₀
  recipe; split the stream; ascent only; fouling windows; sensible workflow. **Errors:** two
  [MEDIUM] caveats promoted to [HIGH]; no MLD *method* in the corpus. **Fix:** `ctd.md` gains an
  MLD section (de Boyer Montégut 2004, Holte & Talley 2009, reference-depth caveat, the argosy
  Zenodo MLD set).

**R3 (T8, shallow-profiler).** *Pull profiles from a month-long nitrate file; why two per day?*
Fetched `shallow-profiler.md`; 6,342 / 1,037 tokens. **Good:** nitrate on #4/#9; the [HIGH]
"don't count" rule; profile-index URL + slicing code; GPI as the cross-sensor key.
**Errors:** dropped the "from 2017 on" qualifier; rating drift. **Fix:** stricter client prompt
(exact ratings, corpus-only URLs, keep qualifiers).
- *R3b (stricter prompt):* qualifier kept; the FM still rated the duty-cycle claim [HIGH] — and
  it was right; the page under-rated it. Fix: rate it [HIGH] on the page. Lesson: when a rating
  keeps "drifting", check the page before blaming the model.

**R4 (T10, nitrate + CTD).** *Nitrate vs oxygen for remineralization.* Fetched `nitrate.md`,
`ctd.md`, `shallow-profiler.md`; 13,374 / 1,888 tokens. **Very good — first multi-page
synthesis:** correct variables; µmol L⁻¹ ↔ µmol kg⁻¹ with in-situ density; match #4/#9 GPIs,
ascent, common depth grid; bottle-check; near-zero negatives; CTD-fouling dependence; oxygen lag;
σ₀. **Error:** a [LOW] item folded under a [HIGH] heading. No corpus fix.

**R5 (T12, pH + pCO₂).** *Clean pH/pCO₂ profiles and the carbonate system.* Fetched `ph.md`,
`pco2.md`; 9,205 / 1,409 tokens. **Mostly good:** descents of #4/#9 (`peak → end`); QARTOD
screening; "rely on QARTOD" for pCO₂; PyCO2SYS with the [MEDIUM] "poor pair for TA/DIC" caveat.
**Errors (corpus-caused):** merged the two off-profile 190 m patterns; missed the [HIGH]
"don't count" rule (only linked, not inlined). **Fixes:** inline that rule in ph/pco2/nitrate;
contrast the two off-profile patterns explicitly.

**R6 (T14, PAR + FLORT).** *Light attenuation / euphotic depth, related to chlorophyll.* Fetched
`par.md`, `flort.md`; 11,744 / 2,147 tokens. **Very good — strongest synthesis:** PAR name trap;
ignore PAR QARTOD; dark threshold before logs; daylight profiles by local solar time; Kd fit +
euphotic depth with caveats; and the cross-sensor insight that the daylight profiles needed for Kd
are where chlorophyll is quenched. Ratings correct. **Error:** answer truncated at the 2,000-token
output limit. **Fix:** `ask.py` limit raised to 4,000 with a truncation notice.

**R7 (data-access, resolution trap + ordering).** *"I pulled shallow profiler CTD data through
Data Explorer for a mixed layer study and the profiles look weirdly smooth. Also, how do I get
the raw full-resolution data?"* Fetched `data-access.md`, `ctd.md`; 10,972 / 1,181 tokens.
**Good:** diagnosed the [HIGH] 1-minute-binning resolution trap (≈3 m vertical bins smear the
MLD structure); routed to OOINET order / Gold Copy for full resolution; added the in-situ-density
MLD pitfall and the σ₀ recipe unprompted; correct variables and citations. No corpus fix.

**R8 (ascent vs descent counterpoint).** *"Is descent data useless? Which sensors actually use
it?"* Fetched `shallow-profiler.md`, `ph.md`, `pco2.md`, `nitrate.md`; 16,211 / 1,095 tokens.
**Good:** ascent for the 8 continuous sensors (sensors on top of the pod enter undisturbed water
from below); **descent is the primary data for pH and pCO₂** (`peak → end`); nitrate the mixed
case (#4/#9 but ascent); clean per-sensor summary table; the off-profile ~190 m caveat. No corpus
fix.

**Batch run of the remaining tests (T2, T3, T6, T7, T9, T11, T13, T15, T16, T17, T18).** All
**passed** — every must-include fact present, ratings copied correctly, no invented URLs, no
rating drift. Highlights and notes:

- **T2 (FLORT QC):** correctly stated 0 bit = "failed *or not run*" — the R1 error is fixed and
  the stricter prompt held.
- **T3 (CDOM):** FDOM proxy, ppb relative to factory standard, "not a reportable concentration".
- **T6 (salinity drop):** diagnosed conductivity-cell fouling, gave the temperature-unchanged /
  conductivity-suspect checks and the December precedent.
- **T7 (oxygen):** DO in the CTD stream, `corrected_dissolved_oxygen`, µmol kg⁻¹, duplicate noted.
- **T9 (midnight/noon):** #4/#9 by long descent not by counting; profile-index code; UTC times.
- **T11 (negative nitrate):** correction artifact near true zero, treat as ≈0, don't drop.
- **T13 (`_cal` file):** blanks, ~1/5 days, already applied, only for diagnostics.
- **T15 (PAR all-failed):** ignore PAR QARTOD (runs on raw counts); use `par_counts_output`;
    negatives = darkness.
- **T16 (surface reach):** profiler stops ~15 m; truncates shallow MLD; extrapolate surface PAR.
- **T17 (out of scope — currents):** declined cleanly, pointed to Data Explorer; hit the same
    `currents.md` 404 (the index lists a still-planned page — remove or write it).
- **T18 (out of scope — deep profiler):** declined cleanly; correctly inferred the `RS03AXPD`
    deep-profiler designator and pointed to official sources, without guessing oxygen values.

**Test bank: 16 of 16 in-scope + both out-of-scope all pass.** No corpus fixes required from this
batch. Remaining nit: `llms.txt` lists `currents.md` as a planned page that 404s (T17) — either
write it or drop the entry so nothing in the index points at a missing page.


## To-dos

**Build / corpus:**
- [x] Run the full test bank (T1–T18): all pass; no corpus fixes needed from the final batch.
- [ ] Remove or write `currents.md` — `llms.txt` lists it but it 404s (surfaced by T17).
- [x] `data-access.md` written (ordering from OOINET; access routes; the [HIGH] 1-minute
      resolution trap for SP data); R7 passed. shallow-profiler.md gained the ascent-from-below
      rationale + descent counterpoint (R8 passed) and names Duprey & Ruef.
- [ ] Remaining general pages: QC flags, currents; the two reference indexes.
- [ ] **Next instrument data = the ADCP(s) on the shallow profiler platform** (the scalar/HSD+LSD
      sensor suite is now fully covered — end of the available scalar plethora). The ADCPs are
      *vector* instruments (velocity profiles), not yet sharded by argosy, so this needs new
      inspection work before a `currents.md` can be grounded in a real file. Verify how many ADCPs
      (one or two) and their orientation/range. Ties to the currents page and the argosy VectorData
      effort.
- [ ] **Public browser client (invite-only):** design in `PublicClient.md`. Lambda + token
      allow-list + daily budget cap. Build is ~1–2 days when wanted.
- [ ] `tools/zenodo_catalog.py` → `docs/datasets.md`.
- [ ] Delete the ~1.5 GB of downloaded source files under `~/ooi/sb/ooinet/scalar/2018_*` once no
      longer needed (kept for now for second-file spot-checks).

**Verify (corpus accuracy):**
- [ ] Roesler et al. 2017 DOI `10.1002/lom3.10185` and the "factor of 2" claim.
- [ ] Daytime-quenching and CDOM-ppb-standard wording vs the BGC Best Practices guide.
- [ ] `oceanobservatories/asset-management` link (FLORT calibrations findable there).
- [ ] pH scale and reference temperature of PHWATER_L2 (pH DPS); the "pH + pCO₂ poor pair for
      TA/DIC" claim (cite an error-propagation source).
- [ ] SUNA accuracy/drift wording ("offsets of a few µmol L⁻¹") vs the BGC guide.
- [ ] Generality: findings come from single files (mostly SB, deployment 4 or 6). Spot-check a
      second deployment/site for the all-zero calibration fields and stuck-value rates.

**Report to data team (LOW defects found):**
- [ ] FLORT: `signal_*_offset` / `signal_*_scale_factor` all zero; backscatter angle 117° (file)
      vs 124° (ION/DPS).
- [ ] PAR: QARTOD runs on raw counts → fails 100%; calibrated `par_counts_output` has no QARTOD;
      nine engineering vars + `par_measured` entirely fill.
- [ ] Nitrate: `internal_timestamp` / `date_of_sample` lag `time` by weeks–months (deployment 6).
- [ ] pH: `phsen_thermistor_temperature` labeled V but holds °C; zero `internal_timestamp` in pH
      and pCO₂ files.

**argosy fixes (in the argosy repo):**
- [x] `SensorTable.md`: PCO2W corrected to Sunburst SAMI-CO2.
- [ ] `plume/ColumbiaPlumePlan.md` oo latitude 44.66 → 44.374; `Sharding.md` daily-index-8
      extended-descent claim (2024 index shows only #4/#9).

**Process:**
- [x] Client prompt hardening; 4k output limit + truncation notice.
- [ ] Never batch a page write with its `git commit`; verify the page is tracked and served
      (HTTP 200) before adding it to `llms.txt`.


## Open questions

- Which FM (and whether to compare two).
- Test bank: Rob to add the questions scientists actually get stuck on.
