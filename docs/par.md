# PAR — photosynthetically active radiation (PARAD): a practical user guide

*Unofficial. Part of [prototype-userguide](llms.txt). Every claim cites a source; official sources
take precedence. Worked examples come from one real delivered file (below) — check your own file.
"Project experience" items come from the [argosy](https://github.com/robfatland/argosy) project.
Read [Shallow profiler operations](shallow-profiler.md) first (profiles, daily index, GPI).*

**Impact ratings:** **[HIGH]** will mislead your analysis if ignored · **[MEDIUM]** matters for
some analyses · **[LOW — report to data team]** a defect worth reporting, but usable as is.


## What the instrument is

- **PARAD** = OOI's PAR sensor class: an upward-looking radiometer measuring the photon flux of
  visible light (400–700 nm) that phytoplankton can use for photosynthesis. On the shallow
  profiler its stream is `parad_sa_sample`.
  [OOI data product: PAR (OPTPARW)](https://oceanobservatories.org/data-products/)
- It rides the profiler up through the water column, so each daylight profile gives a light
  profile — how fast light fades with depth.


## The science product (which variable to use)

| You want | Use this variable | Product code / level | Units |
|---|---|---|---|
| PAR | `par_counts_output` | OPTPARW_L1 | µmol photons m⁻² s⁻¹ |

- **[MEDIUM] Name trap: `par_counts_output` is the *calibrated* value**, despite "counts" in its
  name. The raw counts are `par` (OPTPARW_L0). *(Consistent with argosy, `SensorTable.md`.)*
- **[MEDIUM] `par_measured` looks like the obvious choice but is empty** — every value is a fill
  value in the example file. Use `par_counts_output`.


## What's in a delivered file (32 variables)

From a real file: Slope Base shallow profiler, `RS01SBPS-SF01A-3C-PARADA101`, stream
`parad_sa_sample`, deployment 4, 2018-01-01 → 2018-01-18 (4,639,484 samples, **~3.6 samples per
second** — the fastest sensor on the profiler).

- **Science:** `par_counts_output` (L1).
- **Raw:** `par` (L0 counts, ~2.16 × 10⁹).
- **Position:** `depth`, `int_ctd_pressure`, `lat`, `lon`.
- **Quality control:** `par_qartod_results` / `par_qartod_executed` (on the **raw** `par`, see
  below) and `par_counts_output_qc_executed` / `_qc_results`.
- **Engineering — all empty in the example file:** `par_measured`, `pitch`, `roll`,
  `temp_interior`, `input_voltage`, `voltage_out`, `temperature_volts`, `raw_internal_temp`,
  `x/y/z_accel_counts` (every value is fill). Also `elapsed_time`, `checksum`, `serial_number`,
  `deployment`, `id`.
- **Time:** `time`, `port_timestamp`, `driver_timestamp`, `ingestion_timestamp`,
  `internal_timestamp` (all zeros), `preferred_timestamp`. **Use `time`.**
- **[LOW — report to data team]** Nine engineering variables plus `par_measured` are entirely
  fill values; `internal_timestamp` is all zeros. Harmless for science use, but it means no tilt
  (pitch/roll) or instrument temperature is available.


## Reading the quality-control flags

**[HIGH] Ignore the PAR QARTOD flag — it fails every sample.** In the example file,
`par_qartod_results` is **4 (fail) on all 4,639,484 samples** (`par_qartod_executed = "34"`:
climatology suspect, gross range fail). The tests are run on the **raw** variable `par` (counts
around 2.16 × 10⁹) — apparently against ranges meant for calibrated PAR — and the calibrated
`par_counts_output` has **no QARTOD flag at all**. Filtering on this flag would discard all your
data. This is also worth reporting to the data team.

**OOI QC bit masks on `par_counts_output`** (`qc_executed = 29`):

- **[MEDIUM] Global-range "failures" = negative values = darkness.** Global range failed on
  1,496,468 samples (32%) — matching the **32% of values below zero**. These are dark readings
  (night, or deep water), not bad data (next section).

Decoding details: [FLORT guide](flort.md#reading-the-quality-control-flags).


## What to distrust (and why)

**[HIGH] Darkness reads as small numbers around zero, including negatives.** The sensor's dark
offset and noise make true darkness read as roughly **0 ± 0.3 µmol m⁻² s⁻¹** (example file:
night median 0.056, 1st–99th percentile −0.26 to 0.20; noon below 150 m median 0.051 — the same
as night). So:

- Treat values below ~0.3 µmol m⁻² s⁻¹ as **"dark / below detection"**, not as light.
- Don't take logs of raw values (negatives and near-zeros blow up), and don't simply drop
  negatives (that biases the low end). Clip or mask at a dark threshold first.
- Example noon medians by depth (January): 10–20 m **70**, 20–40 m **25**, 40–60 m **7.6**,
  60–100 m **1.6**, 100–150 m **0.2**, 150–210 m **0.05** (= dark).

**[HIGH] Only daylight profiles carry a light profile.** At night every profile is dark.
Which of the 9 daily profiles fall in daylight changes with season (and the daily index is
counted in the **UTC** day). Select profiles by **local solar time or sun elevation**, not by
daily index. Profile #4 (≈ local midnight) is always dark; #9 (≈ 13:50 local) is always in
daylight.

**[MEDIUM] The profiler may not reach the surface.** In the example (January) file the
shallowest point is **14.8 m** — surface PAR is not measured directly. To estimate it, fit the
light profile and extrapolate, or use an independent surface light source.

**[MEDIUM] Light changes during a profile.** An ascent takes ~67 minutes; sun angle and clouds
change in that time, especially near sunrise and sunset. A single "profile" mixes depth and
time. For attenuation work, prefer profiles near local noon under steady conditions.

**[MEDIUM] Attenuation (Kd) is the robust quantity.** Because absolute light depends on clouds
and sun angle, fit **ln(PAR) vs depth** over the lit part of each profile (above the dark
threshold): the slope is the diffuse attenuation coefficient Kd(PAR). Example file, noon, 15–60 m:
**Kd ≈ 0.064 m⁻¹** (clear offshore winter water). Kd tracks particles and phytoplankton —
compare with [FLORT](flort.md) chlorophyll and backscatter.

**[MEDIUM] No tilt correction possible.** The pitch/roll fields are empty, so tilt of the
sensor (pod motion) can't be checked or corrected. Small effect under diffuse light; larger in
bright direct sun near the surface.

**[MEDIUM] Fouling of the sensor window reduces readings.** Growth on the upward-facing window
over a deployment lowers PAR (and biases Kd). Compare early- vs late-deployment profiles under
similar conditions; check the `deployment` number when stitching files.


## Using PAR with other sensors

- **Chlorophyll quenching:** PAR tells you when and where daytime fluorescence quenching in the
  [FLORT](flort.md) chlorophyll is likely (bright, near-surface).
- **Euphotic depth:** the depth where PAR falls to 1% of its surface value ≈ 4.6 / Kd below the
  surface (with Kd from the lit part of the profile). Useful context for nitrate drawdown
  ([nitrate](nitrate.md)) and oxygen production ([CTD + oxygen](ctd.md)).


## Further reading

- [Shallow profiler operations](shallow-profiler.md) · [FLORT](flort.md) · [nitrate](nitrate.md) · [CTD + oxygen](ctd.md)
- OOI data products list (PAR = OPTPARW): [oceanobservatories.org/data-products](https://oceanobservatories.org/data-products/)
