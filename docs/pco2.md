# pCO₂ (PCO2W, SAMI-CO2): a practical user guide

*Unofficial. Part of [prototype-userguide](llms.txt). Every claim cites a source; official sources
take precedence. Worked examples come from one real delivered file (below) — check your own file.
"Project experience" items come from the [argosy](https://github.com/robfatland/argosy) project.
Read [Shallow profiler operations](shallow-profiler.md) first (profiles, daily index, GPI).*

**Impact ratings:** **[HIGH]** will mislead your analysis if ignored · **[MEDIUM]** matters for
some analyses · **[LOW — report to data team]** a defect worth reporting, but usable as is.


## What the instrument is

- **PCO2W** = OOI's water pCO₂ sensor class; on the shallow profiler it is a Sunburst
  **SAMI-CO2**: seawater CO₂ equilibrates across a gas-permeable membrane with a pH-indicator
  solution, and the instrument reads the indicator's color by absorbance at **434 and 620 nm**.
  pCO₂ comes from those absorbances, referenced to **blank** measurements, and the sample
  temperature. (Verified from the delivered variables: `absorbance_ratio_434/620`,
  `pco2w_a_absorbance_blank_434/620`.)
- Equilibration takes minutes, so the profiler **stops** at set depths for each reading.
- *Not to be confused with* the infrared (NDIR) pCO₂ sensors on some surface buoys.


## The science product (which variable to use)

| You want | Use this variable | Product code / level | Units |
|---|---|---|---|
| pCO₂ of seawater | `pco2_seawater` | PCO2WAT_L1 | µatm |

- Temperature for the calculation is the instrument's own thermistor:
  `pco2w_thermistor_temperature` (CO2THRM_L1, °C).
- **[MEDIUM] Units are µatm (partial pressure).** Converting to fCO₂ or CO₂ concentration, or
  comparing with air-sea flux products, needs temperature, salinity, and pressure — use a
  carbonate-system package (e.g. PyCO2SYS) rather than hand formulas.


## What's in a delivered file (37 variables) — and the second "cal" stream

Data file: Slope Base shallow profiler, `RS01SBPS-SF01A-4F-PCO2WA101`, stream
`pco2w_a_sami_data_record`, deployment 6, 2018-07-10 → 2019-06-14 (9,451 samples, 1.7 MB).

- **Science:** `pco2_seawater` (L1).
- **Inputs:** `absorbance_ratio_434`, `absorbance_ratio_620` (raw, L0), `light_measurements`
  (14-value array), `pco2w_a_absorbance_blank_434/620` (the blanks applied),
  `pco2w_thermistor_temperature`, `thermistor_raw`.
- **Position:** `depth`, `int_ctd_pressure`, `lat`, `lon`.
- **Instrument health:** `pco2_battery_volts`, `voltage_battery`, `record_type`,
  `record_length`, `checksum`, `unique_id`.
- **Quality control:** `pco2_seawater_qartod_*` and `*_qc_*` (pCO₂, absorbances, thermistor).
- **Time:** `time`, `port_timestamp`, `driver_timestamp`, `ingestion_timestamp`,
  `internal_timestamp`, `preferred_timestamp`, `record_time`. **Use `time`.**
- **[LOW — report to data team]** `internal_timestamp` is all zeros; `record_time` uses a 1904
  epoch. Harmless if you use `time`.

**The `..._sami_data_record_cal` stream:** a separate, small file (83 records in deployment 6,
about **one every 5 days**) holding the instrument's **blank** measurements. You do **not** need
it for normal use — the blanks are already applied and carried in the data file. It is useful
only for diagnosing the instrument (e.g. blank drift over a deployment).


## When pCO₂ is measured (sampling)

Verified in the example file by placing every sample in the profile cycle:

- **[HIGH] The pCO₂ profiles are the descents of profiles #4 and #9 only** (from 2017 on): 6,837
  samples on 568 such descents, **median 12 readings per descent**, about **one per 10 m from
  ~10 m to ~110 m**, sparser below. See [Shallow profiler operations](shallow-profiler.md) to find
  #4/#9.
- **[HIGH] ~2,600 more samples are taken while the profiler is parked at the ~190 m platform**
  (between profiles). They are **not profiles** — but they form a useful **near-platform pCO₂ time
  series**. Separate them before profile work.
- Cut profiles with `peak → end` (descent) from the profile index.
- **[MEDIUM]** Like pH, pCO₂ is a **descent** measurement while CTD/FLORT/nitrate are ascent —
  match on GPI and accept (or account for) the ~1 h offset.


## Reading the quality-control flags

Decode as in the [FLORT guide](flort.md#reading-the-quality-control-flags). In the example file:

- **QARTOD** (gross range + climatology): 8,480 pass, 732 suspect (7.7%), **160 fail (1.7%)** —
  a higher fail rate than the other shallow-profiler sensors. **Remove fails (4) before use.**
- **OOI QC bit masks:** everything passed (`qc_results = qc_executed` on every sample) — the OOI
  automated tests did not catch what QARTOD flags here. **[MEDIUM] Rely on QARTOD for pCO₂.**
- Range in the example file: 263–1,114 µatm (higher values at depth are expected: deep water here
  is CO₂-rich and oxygen-poor).


## What to distrust (and why)

**[HIGH] QARTOD fails.** At 1.7% of samples, the fail rate is high enough to matter for profile
statistics. Drop them; look at suspects in profile context.

**[MEDIUM] Equilibration and stop timing.** Each reading is taken at a stop; if equilibration was
incomplete (e.g. after a large change in pCO₂ between stops), the value lags toward the previous
depth's water. Treat sharp jumps between adjacent stops with care.

**[MEDIUM] Drift, blanks, and reagent.** Long deployments need a check against discrete samples
(annual cruise bottles). Blank drift is visible in the `_cal` stream. See the BGC Best Practices
guide (carbonate chapter) and the community example below.

**[MEDIUM] Coarse vertical resolution.** ~12 readings per descent; don't interpolate across
large gaps at depth.


## Combining pCO₂ with pH

pH is measured on the same #4/#9 descents — see the [pH guide](ph.md). The pH + pCO₂ pair is a
poor choice for computing alkalinity or DIC (errors amplify); pair one of them with an alkalinity
estimate instead.


## Further reading

- OOI Biogeochemical Sensor Data **Best Practices & User Guide** (carbonate system chapter): [PDF](https://oceanobservatories.org/wp-content/uploads/2025/07/OOI-Biogeochemical-Sensor-Data-Best-Practices-and-User-Guide-Version-1.1.1-with-July-dated-GOOS-Endorsement-Certificate-on-p2-Updated-DOI.pdf)
- Community example of QC'd carbonate data: Zenodo [nsf-ooi community](https://zenodo.org/communities/nsf-ooi)
  — "10 Years of Quality Controlled Carbonate Measurements … Coastal Endurance Array".
- [Shallow profiler operations](shallow-profiler.md) · [pH](ph.md) · [CTD + oxygen](ctd.md)
