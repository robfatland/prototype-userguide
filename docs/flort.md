# 3-wavelength fluorometer (FLORT): a practical user guide

*Unofficial. Part of [prototype-userguide](llms.txt). Every claim cites a source; official sources
take precedence. Worked examples come from one real delivered file (below) — check your own file.*

**Impact ratings.** Not every issue matters equally. Each caveat below is tagged:

- **[HIGH]** — will mislead your analysis if ignored.
- **[MEDIUM]** — matters for some analyses; know it exists.
- **[LOW]** — a system or documentation defect worth **reporting to the data team**, but it does
  not stop you: the delivered L1/L2 products are usable as they are.


## What the instrument is

- **FLORT** = OOI's 3-wavelength fluorometer, a WET Labs (now Sea-Bird) **ECO Triplet**. One unit
  measures three things: **chlorophyll-a fluorescence**, **CDOM fluorescence**, and **optical
  backscatter** (red light). A related 2-wavelength unit, **FLORD**, has no CDOM channel.
  [ION FLO functions](https://cwingard.github.io/ion-functions/api/flo_functions/);
  [OOI fluorometer class](https://oceanobservatories.org/instrument-class/fluor/)
- It sits on moorings, profilers, and gliders. On the Regional Cabled Array shallow profilers it
  rides the profiler from ~200 m to near the surface.
  [Interactive Oceans: Fluorometer](https://interactiveoceans.washington.edu/instruments/fluorometer/)
- **Biofouling protection differs by platform:** fixed instruments have a **wiper**; profilers,
  gliders, and AUVs have **only passive protection** (coating + copper faceplate). Expect more
  fouling drift on profilers. [DPS 1341-00530 §2.3](https://oceanobservatories.org/wp-content/uploads/2023/09/1341-00530_Data_Product_Specification_CHLAFLO_OOI.pdf)


## The three science products (which variable to use)

| You want | Use this variable | Product code / level | Units |
|---|---|---|---|
| Chlorophyll-a (fluorescence estimate) | `fluorometric_chlorophyll_a` | CHLAFLO_L1 | µg L⁻¹ |
| CDOM (fluorescence) | `fluorometric_cdom` | CDOMFLO_L1 | ppb |
| Backscatter (for particles / turbidity) | `optical_backscatter` | **FLUBSCT_L2** | m⁻¹ |

- **[HIGH] Backscatter trap:** `total_volume_scattering_coefficient` (FLUBSCT_**L1**, m⁻¹ sr⁻¹) is the
  raw *angular* scattering at one angle. It is **not** the backscatter coefficient. For analysis
  use `optical_backscatter` (L2). [ION FLO functions](https://cwingard.github.io/ion-functions/api/flo_functions/)
- **[MEDIUM] `optical_backscatter` is total backscatter** (particles + seawater):
  `b_b = b_bp + b_sw/2`. For **particulate** backscatter (what most particle studies want):
  `b_bp = optical_backscatter − seawater_scattering_coefficient / 2`.
  [DPS 1341-00540](https://oceanobservatories.org/wp-content/uploads/2023/09/1341-00540_Data_Product_SPEC_FLUBSCT_OOI.pdf)
- **How L1 is made:** `value = (raw_counts − dark_counts) × scale_factor`, with dark counts and
  scale factor from the factory calibration sheet. Same formula for all three channels.
  [DPS 1341-00530](https://oceanobservatories.org/wp-content/uploads/2023/09/1341-00530_Data_Product_Specification_CHLAFLO_OOI.pdf);
  [DPS 1341-00550](https://oceanobservatories.org/wp-content/uploads/2023/09/1341-00550_Data_Product_Specification_CDOMFLO_OOI.pdf)


## What's in a delivered file (48 variables, sorted)

From a real file: Slope Base shallow profiler, `RS01SBPS-SF01A-3A-FLORTD101`, stream
`flort_d_data_record`, 2018-01-09 → 2018-02-09 (2,180,976 samples, ~1 sample per 1.1 s).

- **Science (use these):** `fluorometric_chlorophyll_a`, `fluorometric_cdom`, `optical_backscatter`.
- **Intermediates:** `total_volume_scattering_coefficient` (L1 backscatter),
  `seawater_scattering_coefficient` (pure-water scattering, needed for `b_bp`).
- **Raw counts (L0):** `raw_signal_chl`, `raw_signal_cdom`, `raw_signal_beta`, `raw_internal_temp`.
- **Calibration fields:** `signal_1/2/3_offset`, `signal_1/2/3_scale_factor`,
  `measurement_wavelength_beta/chl/cdom` (700 / 695 / 460 nm).
- **Co-located CTD (needed for backscatter math):** `sea_water_temperature`,
  `sea_water_practical_salinity`, `int_ctd_pressure`, `depth`.
- **Quality control (two separate systems — see below):** for each science variable,
  `*_qartod_results`, `*_qartod_executed`, `*_qc_executed`, `*_qc_results`.
- **Position, time, bookkeeping:** `lat`, `lon`, `deployment`, `id`; and **six time variables**
  (`time`, `internal_timestamp`, `driver_timestamp`, `port_timestamp`, `ingestion_timestamp`,
  `preferred_timestamp`) plus string dates. **Use `time`.**
- **The only dimension is `obs`** (sample number). Time is a variable, not a coordinate. In
  xarray: `ds = ds.swap_dims({"obs": "time"})`.


## Reading the quality-control flags

There are **two independent QC systems** in the file. Neither deletes data; you decide.
[OOI: Interpreting QC variables](https://oceanobservatories.org/knowledgebase/interpreting-qc-variables-and-results/)

**1. QARTOD — `*_qartod_results` (summary) and `*_qartod_executed` (per test).**

- Summary flag values: **1 pass, 2 not evaluated, 3 suspect (or of high interest), 4 fail,
  9 missing.** The summary is the worst result across the tests run. (File attributes;
  [IOOS QARTOD](https://ioos.noaa.gov/project/qartod))
- `*_qartod_executed` is a string, one digit per test, in the order of its `tests_executed`
  attribute — here `gross_range_test, climatology_test`. Example: `"13"` = gross range **pass**,
  climatology **suspect**.
- **[MEDIUM] "Suspect" is not "bad".** In the example file, the climatology test marked **57% of CDOM**
  samples suspect (1,245,226 of 2,180,976). Treat 3 as "look closer", 4 as "probably bad".

**2. OOI automated QC — `*_qc_executed` and `*_qc_results` (bit masks).**

- Each is an integer whose binary bits stand for tests, lowest bit first: **bit 1 global range,
  bit 2 local range, bit 3 spike, bit 4 trend, bit 5 stuck value, bit 6 gradient.**
  `qc_executed` = which tests ran; `qc_results` bit = 1 means **passed** (and 0 means failed *or
  not run*). [OOI: Interpreting QC variables](https://oceanobservatories.org/knowledgebase/interpreting-qc-variables-and-results/)
- Explicit failures only: `effective = (0xFFFF ^ qc_executed) | qc_results` — any 0 bit in
  `effective` is a test that ran and failed. (Same source.)
- Example file: `qc_executed = 29` (binary 11101 → global range, spike, trend, stuck value ran;
  local range did not).
- **[HIGH] Most "failures" are the stuck-value test, and it is misleading here.** `qc_results = 13`
  (binary 01101 = stuck value failed) on **49% of chlorophyll** samples and **99% of backscatter**
  samples. The stuck-value test flags runs of repeated identical values. For **chlorophyll** that
  is largely what a low-signal, quantized sensor produces (next section). For **backscatter** the
  signal is ~75 counts above dark with ~2,000 distinct values, so quantization doesn't explain a
  99% failure rate — the test's threshold is the likelier cause. OOI itself notes the stuck-value
  thresholds "need to be reviewed". Either way: **don't discard data on stuck-value alone.**
- Note that a 0 bit in `qc_results` means the test **failed or was not run** — always compare
  with `qc_executed` (formula below) before treating a 0 as a failure.
- Genuine-looking failures are rare: global range failed (`28`) on 35 chlorophyll samples; spike
  failed (`25`) on 30.


## What to distrust (and why)

**[HIGH] Low signal → coarse steps (quantization).** Raw output is integer counts, so values come in
fixed steps of one `scale_factor`. In clear or deep water the signal is only a few counts above
dark, so the steps dominate. In the example file (recovered by fitting L1 against raw counts):

| Channel | Dark count | Step (one count) | Counts above dark (median) |
|---|---|---|---|
| Chlorophyll | 48 | **0.0115 µg L⁻¹** | **6** (69% of samples ≤ 10) |
| CDOM | ≈ 46 | 0.135 ppb | ≈ 25 |
| Backscatter (L1) | 48 | 2.29 × 10⁻⁶ m⁻¹ sr⁻¹ | ≈ 75 |

- Chlorophyll raw counts by depth: median **102** at 0–30 m, **60** at 60–100 m, **53–54** below
  100 m — i.e. below ~100 m the chlorophyll signal is essentially dark plus noise. Small negative
  values (minimum −0.046 µg L⁻¹ here) are dark-count noise, not real.
- Practical: smooth or bin before interpreting fine structure (e.g. a Savitzky–Golay filter or
  depth bins), and don't read meaning into steps of one count.

**Chlorophyll from fluorescence is an estimate, not a measurement of chlorophyll.**

- **[HIGH for absolute chlorophyll; LOW for relative patterns]** Factory-calibrated ECO chlorophyll
  overestimates extracted chlorophyll by about a **factor of 2** on average (global analysis). [Roesler et al. 2017, L&O Methods](https://doi.org/10.1002/lom3.10185)
- **[HIGH near the surface in daylight] Daytime quenching:** in bright near-surface light, phytoplankton suppress fluorescence
  (non-photochemical quenching), so daytime surface chlorophyll reads low. Compare night profiles,
  or correct. See the BGC Best Practices guide below.

**[MEDIUM] "CDOM" is really fluorescent DOM (FDOM).** The sensor measures fluorescence (excite 370 nm /
emit 460 nm), which tracks only the fluorescent fraction of colored dissolved organic matter. The
file calls it "CDOM Concentration" in ppb (relative to the factory calibration standard); treat it
as a relative fluorescence index, not a CDOM concentration.
[DPS 1341-00550](https://oceanobservatories.org/wp-content/uploads/2023/09/1341-00550_Data_Product_Specification_CDOMFLO_OOI.pdf);
[BGC Best Practices guide](https://oceanobservatories.org/wp-content/uploads/2025/07/OOI-Biogeochemical-Sensor-Data-Best-Practices-and-User-Guide-Version-1.1.1-with-July-dated-GOOS-Endorsement-Certificate-on-p2-Updated-DOI.pdf)

**[MEDIUM] Backscatter spikes are real particles, not noise.** Large particles (marine snow, zooplankton)
crossing the beam make positive spikes. For the background particle field, take a running
minimum (Briggs et al. 2011, doi:10.1016/j.dsr.2011.09.007); for aggregates, study the spikes.

**[HIGH for long time series] Biofouling drift.** Profiler units have no wiper, so fouling can build over a deployment
(signals creeping up, or a drift in the deep "dark" value). Compare early vs late in a
deployment; check the `deployment` number when stitching files.

**[LOW — report to data team] Calibration fields in the file may be empty.** In the example
file, every `signal_*_offset` and `signal_*_scale_factor` value is **0** — you cannot rebuild L1
from raw counts using the file alone. Low impact for most users: the system delivers L1, and
analysis starts from L1 (or transforms it to L2 and beyond). Use the L1/L2 values as delivered, or look up the instrument's
calibration in OOI's asset-management records
([oceanobservatories/asset-management](https://github.com/oceanobservatories/asset-management)).

**[LOW — report to data team] Backscatter angle: a documentation mismatch.** The file's comment says the default scattering
angle is **117°**; the processing documentation lists **124°** (χ = 1.076) for FLORT-D units.
This affects `b_bp` at the few-percent level. Ask OOI which was applied.
[ION FLO functions](https://cwingard.github.io/ion-functions/api/flo_functions/)


## Shallow profiler specifics

- **[HIGH]** The delivered stream is **continuous**: it includes time parked at the ~200 m platform between
  profiles, not just profiles. In the example file about half the samples are below 150 m.
- To split the stream into individual up-casts, use the RCA **profile index** (start / peak / end
  time of every profile): [OOI-CabledArray/profileIndices](https://github.com/OOI-CabledArray/profileIndices).
- Use the **ascent** (upcast) for science; descent data are generally treated as second-class
  (noisier, and on some profiles interrupted by built-in pauses).


## Further reading

- OOI Biogeochemical Sensor Data **Best Practices & User Guide** (general BGC guidance; QC,
  drift, annotations): [PDF](https://oceanobservatories.org/wp-content/uploads/2025/07/OOI-Biogeochemical-Sensor-Data-Best-Practices-and-User-Guide-Version-1.1.1-with-July-dated-GOOS-Endorsement-Certificate-on-p2-Updated-DOI.pdf)
- Processing specifications: [CHLAFLO](https://oceanobservatories.org/wp-content/uploads/2023/09/1341-00530_Data_Product_Specification_CHLAFLO_OOI.pdf),
  [CDOMFLO](https://oceanobservatories.org/wp-content/uploads/2023/09/1341-00550_Data_Product_Specification_CDOMFLO_OOI.pdf),
  [FLUBSCT](https://oceanobservatories.org/wp-content/uploads/2023/09/1341-00540_Data_Product_SPEC_FLUBSCT_OOI.pdf)
- Processing code: [ION FLO functions](https://cwingard.github.io/ion-functions/api/flo_functions/)
- Community-published binned FLORT products (2014–2026): Zenodo
  [nsf-ooi community](https://zenodo.org/communities/nsf-ooi) — "NSF-OOI Binned Fluorometric
  Chlorophyll-a, FDOM, and Backscatter".
