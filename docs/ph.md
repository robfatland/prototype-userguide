# pH (PHSEN, SAMI-pH): a practical user guide

*Unofficial. Part of [prototype-userguide](llms.txt). Every claim cites a source; official sources
take precedence. Worked examples come from one real delivered file (below) — check your own file.
"Project experience" items come from the [argosy](https://github.com/robfatland/argosy) project.
Read [Shallow profiler operations](shallow-profiler.md) first (profiles, daily index, GPI).*

**Impact ratings:** **[HIGH]** will mislead your analysis if ignored · **[MEDIUM]** matters for
some analyses · **[LOW — report to data team]** a defect worth reporting, but usable as is.


## What the instrument is

- **PHSEN** = OOI's pH sensor class; on the shallow profiler it is a Sunburst **SAMI-pH**: a
  pump injects a pH-sensitive dye (indicator) into a seawater sample, and the instrument measures
  the dye's color by light absorbance at **434 and 578 nm**. pH comes from the absorbance ratio,
  the sample temperature, and salinity.
  [OOI pH instrument class](https://oceanobservatories.org/instrument-class/ph/);
  [Interactive Oceans: pH sensors](https://interactiveoceans.washington.edu/instruments/ph/)
- Each measurement is a **pump-and-wait cycle**, not a continuous reading — so the profiler
  **stops** at set depths for it.


## The science product (which variable to use)

| You want | Use this variable | Product code / level | Units |
|---|---|---|---|
| pH | `ph_seawater` | PHWATER_L2 | pH units |

- The L2 product uses **salinity from a nearby CTD** (`sea_water_practical_salinity`, carried in
  the file) and the instrument's own **thermistor temperature** (`phsen_thermistor_temperature`).
  (File comment.)
- **[MEDIUM] Know the pH scale and temperature before comparing with bottle data.** Check the
  processing specification for which pH scale is reported and at what temperature, then convert
  your comparison data to match (e.g. with PyCO2SYS).


## What's in a delivered file (32 variables)

From a real file: Slope Base shallow profiler, `RS01SBPS-SF01A-2D-PHSENA101`, stream
`phsen_data_record`, deployment 6, 2018-07-10 → 2019-06-14 (7,990 samples; a whole deployment in
2.4 MB).

- **Science:** `ph_seawater` (L2).
- **Inputs to the calculation:** `phsen_thermistor_temperature`, `sea_water_practical_salinity`,
  `int_ctd_pressure`, `depth`.
- **Raw optics (arrays per sample):** `signal_intensity_434`, `signal_intensity_578` (23 values
  each), `ph_light_measurements` (92), `reference_light_measurements` (16); thermistor counts
  `thermistor_start` / `thermistor_end`.
- **Instrument health:** `phsen_battery_volts`, `voltage_battery`, `record_type`,
  `record_length`, `checksum`, `unique_id`.
- **Quality control:** `ph_seawater_qartod_*`, `ph_seawater_qc_*`.
- **Time and bookkeeping:** `time`, `port_timestamp`, `driver_timestamp`, `ingestion_timestamp`,
  `internal_timestamp`, `preferred_timestamp`, `record_time`, `deployment`, `lat`, `lon`, `id`.
  **Use `time`.**
- **[LOW — report to data team] Label and clock defects:** `phsen_thermistor_temperature` is
  labeled in **volts** but holds **°C** (7–17 in the example file); `internal_timestamp` is all
  zeros; `record_time` (1904 epoch) holds one constant value. All harmless if you use `time` and
  read the thermistor values as °C.


## When pH is measured (sampling)

Verified in the example file by placing every sample in the profile cycle:

- **[HIGH] The pH profiles are the descents of profiles #4 and #9 only** (from 2017 on): 6,270
  samples on 479 such descents, **median 13 readings per descent**, about **one reading per 10 m
  from ~10 m to ~110 m**, sparser below. See [Shallow profiler operations](shallow-profiler.md) to
  find #4/#9.
- **[HIGH] The other ~1,700 samples are single readings at ~190 m** — one per ordinary profile,
  at the bottom of its descent. They are **not profiles**. Treat them as a near-platform time
  series (up to 7 per day; ~5 per day in the example file), or drop them before profile work. *(Consistent with argosy,
  `SensorTable.md`.)*
- Cut profiles with `peak → end` (descent) from the profile index — **not** `start → peak`.
- **[MEDIUM]** pH is measured on **descent**, while the CTD, FLORT, and nitrate science data are
  ascent. When pairing pH with other variables, match on GPI and use the *same* phase where
  possible (e.g. the pH file's own temperature, salinity, and depth), or accept the ~1 h ascent →
  descent time offset.


## Reading the quality-control flags

Decode as in the [FLORT guide](flort.md#reading-the-quality-control-flags). In the example file:

- **QARTOD** (gross range + climatology): 7,074 pass, **848 suspect (10.6%)**, **13 fail**.
- **OOI QC bit masks:** global range failed on 78 samples; stuck value on ~20; otherwise passed.
- **[HIGH] Impossible values are present.** The example file spans pH **4.2 to 9.4**; open-ocean
  seawater over 0–200 m here is roughly 7.5–8.2. Screen with the QARTOD fail/suspect flags *and*
  a plausible-range check before use.


## What to distrust (and why)

**[HIGH] Out-of-range spikes.** Reagent-based measurements fail occasionally (bubbles, reagent
problems, pump faults) and produce single wild values. Use QARTOD flags plus a range check; look at
whole profiles, not single points.

**[MEDIUM] Coarse vertical resolution.** ~13 readings per descent, ~10 m apart near the surface:
fine for the pH profile shape, too coarse to resolve thin layers. Don't interpolate across big
gaps at depth.

**[MEDIUM] Drift and calibration.** Indicator-dye pH sensors are relatively stable, but a
deployment-long record should still be checked against discrete samples (annual cruise bottles).
See the BGC Best Practices guide (carbonate chapter) and the community example below.

**[MEDIUM] Inherits CTD problems.** The calculation uses CTD salinity; during conductivity-cell
fouling events (see [CTD guide](ctd.md)) pH is affected too, though less strongly than nitrate.


## Combining pH with pCO₂

The same profiles (#4 and #9) carry pCO₂ on the same descent stops — see the
[pCO₂ guide](pco2.md). With two carbonate-system parameters plus T and S you can compute the rest
of the carbonate system (e.g. with PyCO2SYS), but **[MEDIUM] the pH + pCO₂ pair is a poor choice
for computing alkalinity or DIC** — small errors in either are strongly amplified. Prefer pairing
one of them with an alkalinity estimate (e.g. from a regional salinity relationship).


## Further reading

- [OOI pH instrument class](https://oceanobservatories.org/instrument-class/ph/) ·
  [Interactive Oceans: pH sensors](https://interactiveoceans.washington.edu/instruments/ph/)
- OOI Biogeochemical Sensor Data **Best Practices & User Guide** (carbonate system chapter): [PDF](https://oceanobservatories.org/wp-content/uploads/2025/07/OOI-Biogeochemical-Sensor-Data-Best-Practices-and-User-Guide-Version-1.1.1-with-July-dated-GOOS-Endorsement-Certificate-on-p2-Updated-DOI.pdf)
- Community example of QC'd carbonate data: Zenodo [nsf-ooi community](https://zenodo.org/communities/nsf-ooi)
  — "10 Years of Quality Controlled Carbonate Measurements … Coastal Endurance Array".
- [Shallow profiler operations](shallow-profiler.md) · [CTD + oxygen](ctd.md) · [pCO₂](pco2.md)
