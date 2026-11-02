# Nitrate (NUTNR, SUNA): a practical user guide

*Unofficial. Part of [prototype-userguide](llms.txt). Every claim cites a source; official sources
take precedence. Worked examples come from one real delivered file (below) — check your own file.
"Project experience" items come from the [argosy](https://github.com/robfatland/argosy) project.
Read [Shallow profiler operations](shallow-profiler.md) first (profiles, daily index, GPI).*

**Impact ratings:** **[HIGH]** will mislead your analysis if ignored · **[MEDIUM]** matters for
some analyses · **[LOW — report to data team]** a defect worth reporting, but usable as is.


## What the instrument is

- **NUTNR** = OOI's nitrate sensor class; on the shallow profiler it is a Sea-Bird **SUNA**
  (Submersible Ultraviolet Nitrate Analyzer). It shines UV light through a small sample path,
  records a **256-wavelength absorption spectrum**, and fits nitrate from the shape of that
  spectrum. [OOI nitrate instrument class](https://oceanobservatories.org/instrument-class/nutnr/)
- Seawater salinity (bromide) and temperature also absorb UV, so the nitrate estimate depends on
  co-located CTD temperature and salinity — the CTD values are carried in the nitrate file.
- **It is optical and reagent-free, but it is not calibrated against bottle samples in the
  delivered product.** For best accuracy, compare against discrete samples (see "What to distrust").


## The science product (which variable to use)

| You want | Use this variable | Product code / level | Units |
|---|---|---|---|
| Nitrate | `salinity_corrected_nitrate` | NITRTSC_L2 | µmol L⁻¹ |

- **[HIGH] Use the corrected variable.** `nitrate_concentration` (NITRDIS_L1) is the same
  measurement **without** the temperature/salinity correction. The two differ by several µmol L⁻¹
  (example file medians: 28.2 vs 24.2). For analysis use `salinity_corrected_nitrate`.
- **[MEDIUM] Units are per liter (µmol L⁻¹), not per kilogram.** The CTD's oxygen is in
  µmol kg⁻¹. Before combining (e.g. N:O ratios, apparent oxygen utilization comparisons), convert
  one using density: µmol kg⁻¹ = µmol L⁻¹ × 1000 / ρ (ρ in kg m⁻³).
- `nutnr_nitrogen_in_nitrate` (mg L⁻¹) is the uncorrected value in mass units — ignore it.


## What's in a delivered file (53 variables, sorted)

From a real file: Slope Base shallow profiler, `RS01SBPS-SF01A-4A-NUTNRA101`, stream
`nutnr_a_sample`, deployment 6, 2018-07-10 → 2019-06-13 (95,143 samples; a whole deployment in
~50 MB because the sensor runs only twice a day).

- **Science:** `salinity_corrected_nitrate` (L2); `nitrate_concentration` (L1, uncorrected).
- **Raw spectrum:** `spectral_channels` (256 wavelengths × each sample; NITROPT_L0) — the only
  2-D variable; dimension `wavelength`.
- **Fit diagnostics:** `nutnr_fit_rmse`, `nutnr_fit_base_1/2`, `aux_fitting_1/2`,
  `nutnr_dark_value_used_for_fit`, `nutnr_spectrum_average`, `nutnr_absorbance_at_254_nm` /
  `_350_nm`, `nutnr_bromide_trace` (all zero here).
- **Co-located CTD (used for the correction):** `sea_water_temperature`,
  `sea_water_practical_salinity`, `int_ctd_pressure`, `depth`.
- **Instrument health:** `lamp_time` (cumulative lamp seconds), `temp_lamp`, `temp_spectrometer`,
  `temp_interior`, `humidity`, `voltage_lamp`, `voltage_main`, `nutnr_current_main`,
  `nutnr_voltage_int`.
- **Quality control:** `*_qartod_*` and `*_qc_*` for both nitrate variables.
- **Frame type:** `frame_type` — every sample in the example file is a light frame (`SLF`); no
  dark frames are delivered. The dark correction is already applied (value in
  `nutnr_dark_value_used_for_fit`).
- **Time and bookkeeping:** `time`, `internal_timestamp`, `driver_timestamp`, `port_timestamp`,
  `ingestion_timestamp`, `preferred_timestamp`, `date_of_sample`, `time_of_sample`, `checksum`,
  `serial_number`, `deployment`, `lat`, `lon`, `id`. **Use `time`** (see below).
- Only dimension for most variables is `obs`: `ds = ds.swap_dims({"obs": "time"})`.


## When nitrate is measured (sampling)

- **[HIGH] Only two profiles a day — #4 (~local midnight) and #9 (~13:50 local) — and only on
  the ascent** (from 2017 on). Verified in the example file: **563 of 570** nitrate profiles fall
  on the long-descent #4/#9 profiles (the 7 exceptions are worth checking individually). See
  [Shallow profiler operations](shallow-profiler.md) for how to identify #4/#9 safely.
- **~170 samples per ascent**, mostly ~40 s apart — roughly **one sample per 1–2 m** of depth.
  Coarser than the CTD (1 Hz); fine for nutriclines, too coarse for thin layers.
- Median coverage per profile: **~8 m to ~189 m**.
- To cut profiles: slice `start → peak` from the profile index, exactly as in the operations
  guide. 96% of samples in the example file fall inside an indexed ascent.


## Reading the quality-control flags

Decode as in the [FLORT guide](flort.md#reading-the-quality-control-flags). In the example file:

- **QARTOD** (climatology + gross range): corrected nitrate — 92,526 pass, 2,468 suspect (2.6%),
  **27 fail**; uncorrected — 833 suspect, 0 fail.
- **OOI QC bit masks** (`qc_executed = 29`: global range, spike, trend, stuck value):
  - **[MEDIUM] Global-range failures = negative values.** 1,088 samples fail global range on
    the corrected nitrate — matching the 1.1% of values below zero (next section).
  - Stuck value fails on ~22% of corrected-nitrate samples; trend fails on a few hundred.
    As with other instruments, **don't discard on stuck-value alone.**


## What to distrust (and why)

**[MEDIUM] Small negative values near the surface.** The temperature/salinity correction pushes
1.1% of corrected values below zero (minimum −3.9 µmol L⁻¹ in the example file), typically where
nitrate is truly near zero (sunlit surface water in summer). Treat values within a couple of
µmol L⁻¹ of zero as "≈ 0, below reliable detection", not as negative concentrations; don't simply
drop them (that biases the low end upward).

**[HIGH for absolute concentrations] Accuracy and drift need bottle checks.** Optical nitrate
sensors drift (lamp aging, window fouling) and carry offsets of a few µmol L⁻¹. For trends or
absolute budgets, adjust against discrete bottle samples from the annual cruises or a
deep-water reference. Community example of exactly this: the validated OOI nitrate datasets on
Zenodo (Irminger Sea 7-year; Pioneer 5-year), which document the adjustment.
[Zenodo nsf-ooi community](https://zenodo.org/communities/nsf-ooi);
[BGC Best Practices guide](https://oceanobservatories.org/wp-content/uploads/2025/07/OOI-Biogeochemical-Sensor-Data-Best-Practices-and-User-Guide-Version-1.1.1-with-July-dated-GOOS-Endorsement-Certificate-on-p2-Updated-DOI.pdf)
(nitrate chapter). Lamp health is in the file: watch `lamp_time` and `nutnr_spectrum_average`
(signal level) across a deployment.

**[MEDIUM] The correction inherits CTD problems.** The temperature/salinity correction uses the
co-located CTD. During conductivity-cell fouling events (bad salinity — see
[CTD guide](ctd.md)), corrected nitrate is wrong too. Check salinity before trusting nitrate in
those windows.

**[LOW — report to data team] The instrument's own clock fields run months behind.** In the
example file, from ~October 2018 on, `internal_timestamp` and `date_of_sample` lag `time` by
weeks to months (samples that `time` places in Nov 2018–Jun 2019 carry internal dates of
Oct–Nov 2018). `time` (= `port_timestamp`) is right: its profiles line up with the #4/#9
long-descent profiles for 563 of 570 profiles, which a months-off clock could not do.
**Use `time`; ignore the instrument clock fields.**


## Further reading

- [OOI nitrate instrument class](https://oceanobservatories.org/instrument-class/nutnr/)
- OOI Biogeochemical Sensor Data **Best Practices & User Guide** (nitrate chapter): [PDF](https://oceanobservatories.org/wp-content/uploads/2025/07/OOI-Biogeochemical-Sensor-Data-Best-Practices-and-User-Guide-Version-1.1.1-with-July-dated-GOOS-Endorsement-Certificate-on-p2-Updated-DOI.pdf)
- Validated nitrate datasets (worked examples of bottle-based adjustment): Zenodo
  [nsf-ooi community](https://zenodo.org/communities/nsf-ooi) — "A 7-year Validated Nitrate
  Dataset … Irminger Sea", "A 5-year Validated Nitrate Dataset … Pioneer New England Shelf".
- [Shallow profiler operations](shallow-profiler.md) · [CTD + oxygen](ctd.md)
