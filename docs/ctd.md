# Profiling CTD with dissolved oxygen (CTDPF): a practical user guide

*Unofficial. Part of [prototype-userguide](llms.txt). Every claim cites a source; official sources
take precedence. Worked examples come from one real delivered file (below) — check your own file.
"Project experience" items come from the [argosy](https://github.com/robfatland/argosy) project's
multi-year work with these data; they are field observations, not official findings.*

**Impact ratings:** **[HIGH]** will mislead your analysis if ignored · **[MEDIUM]** matters for
some analyses · **[LOW — report to data team]** a defect worth reporting, but the delivered
product is usable.


## What the instrument is

- **CTDPF** = OOI's profiler CTD: conductivity, temperature, pressure, plus a **fast-response
  dissolved-oxygen sensor** on the same pump/stream. On the Regional Cabled Array shallow
  profilers the stream is named `ctdpf_sbe43_sample` (a Sea-Bird SBE 43-class oxygen sensor).
- **It is the foundation for every other sensor:** depth, temperature, salinity, and density from
  this CTD feed the corrections in the FLORT, nitrate, pH, and pCO₂ products. If the CTD is wrong,
  everything downstream inherits it.
- **One stream gives T, S, density, and DO.** You don't need a separate oxygen download for the
  shallow profiler: project experience found the separately delivered DO product identical to the
  DO in the CTD stream. *(argosy, `SensorTable.md`)*


## The science products (which variable to use)

| You want | Use this variable | Product code / level | Units |
|---|---|---|---|
| Temperature | `sea_water_temperature` | TEMPWAT_L1 | °C (ITS-90 in-situ) |
| Practical salinity | `sea_water_practical_salinity` | PRACSAL_L2 | PSS-78 (unitless) |
| Pressure | `sea_water_pressure` | PRESWAT_L1 | dbar (sea pressure) |
| Depth | `depth` | — (from pressure + latitude) | m, positive down |
| Conductivity | `sea_water_electrical_conductivity` | CONDWAT_L1 | S m⁻¹ |
| Density | `sea_water_density` | DENSITY_L2 | kg m⁻³ — **in-situ**, see below |
| Dissolved oxygen | `corrected_dissolved_oxygen` | DOCONCF_L2 | µmol kg⁻¹ (P/T/S corrected) |

- **[HIGH for stratification / mixed-layer work] `sea_water_density` is in-situ density, not
  potential density.** In the example file it matches TEOS-10 `rho(SA, CT, p)` to 0.0003 kg m⁻³
  and differs from potential density (σ₀ + 1000) by up to **0.9 kg m⁻³** over 0–200 m — 30× a
  typical mixed-layer threshold (0.03 kg m⁻³). For mixed-layer depth, stability, or water-mass
  work, compute potential density yourself:
  ```python
  import gsw
  SA = gsw.SA_from_SP(S, p, lon, lat)
  CT = gsw.CT_from_t(SA, T, p)
  sigma0 = gsw.sigma0(SA, CT)      # potential density anomaly, kg m-3 (ref 0 dbar)
  ```
  [DPS 1341-00050 Density](https://oceanobservatories.org/wp-content/uploads/2023/09/1341-00050_Data_Product_SPEC_DENSITY_OOI.pdf);
  [TEOS-10 / GSW](https://www.teos-10.org/)
- **[MEDIUM] Oxygen appears twice.** `corrected_dissolved_oxygen` and
  `do_fast_sample-corrected_dissolved_oxygen` (the one carrying the DOCONCF_L2 product code) hold
  identical values in the example file. Use either; `corrected_dissolved_oxygen` carries the QC
  flags.
- **[MEDIUM] Oxygen units are µmol kg⁻¹** (per mass of seawater), not µmol L⁻¹ or mL L⁻¹.
  Convert with density if comparing with volume-based data.
- Salinity is **practical salinity** (PSS-78). TEOS-10 work needs Absolute Salinity (`SA` above).
  [DPS 1341-00040 Practical Salinity](https://oceanobservatories.org/wp-content/uploads/2023/09/1341-00040_Data_Product_SPEC_PRACSAL_OOI.pdf)


## What's in a delivered file (46 variables, sorted)

From a real file: Slope Base shallow profiler, `RS01SBPS-SF01A-2A-CTDPFA102`, stream
`ctdpf_sbe43_sample`, 2018-01-01 → 2018-01-19 (1,563,115 samples, **1 sample per second**).

- **Science (use these):** the seven variables in the table above.
- **Duplicate:** `do_fast_sample-corrected_dissolved_oxygen` (same values as
  `corrected_dissolved_oxygen`).
- **Raw counts (L0):** `temperature`, `conductivity`, `pressure`, `pressure_temp`, `ext_volt0`
  (oxygen sensor voltage).
- **Quality control:** `*_qartod_results` / `*_qartod_executed` (temperature, salinity,
  conductivity, pressure, oxygen) and `*_qc_executed` / `*_qc_results` (those plus density).
  **Density has no QARTOD flag.**
- **Position, time, bookkeeping:** `lat`, `lon`, `deployment`, `id`, `provenance`; time variables
  `time`, `internal_timestamp`, `driver_timestamp`, `port_timestamp`, `ingestion_timestamp`,
  `preferred_timestamp`. **Use `time`.**
- **[LOW — report to data team] `internal_timestamp` is all zeros** in the example file. Harmless
  if you use `time`.
- **The only dimension is `obs`.** In xarray: `ds = ds.swap_dims({"obs": "time"})`.


## Reading the quality-control flags

Same two systems as every OOI file — see the [FLORT guide](flort.md#reading-the-quality-control-flags)
for how to decode them. What they say in the example CTD file:

**QARTOD** (1 pass, 2 not evaluated, 3 suspect, 4 fail):

| Variable | Tests run | Suspect (3) | Fail (4) |
|---|---|---|---|
| Temperature | gross range, climatology | 2,479 (0.16%) | 0 |
| Salinity | gross range, climatology | 0 | 0 |
| Conductivity | gross range | **64,419 (4.1%)** | 0 |
| Oxygen | gross range, climatology | 11,369 (0.7%) | 0 |
| Pressure | gross range | 0 | 0 |

- **[MEDIUM] Conductivity flagged, salinity not.** Salinity (derived from conductivity) passes
  its own range test even when conductivity is flagged suspect. A conductivity flag is the earlier
  warning — check salinity around flagged conductivity rather than trusting salinity's pass.
  Project experience: the same pattern appeared in a separate 2018 study (9.4% of conductivity
  suspect, salinity passing). *(argosy, `PostProcessing.md` → QC filter study)*

**OOI automated QC bit masks** (`qc_executed = 29` → global range, spike, trend, stuck value ran):

- **[HIGH] The stuck-value test is misleading here too.** `qc_results = 13` (stuck value failed)
  on **99.8% of conductivity** and **88% of density** samples, and 2–3% of temperature, salinity,
  and pressure. A 1 Hz, high-resolution CTD does not "stick" this often; the test threshold is the
  likely problem (OOI notes stuck-value thresholds "need to be reviewed").
  **Don't discard CTD data on stuck-value alone.**
  [OOI: Interpreting QC variables](https://oceanobservatories.org/knowledgebase/interpreting-qc-variables-and-results/)
- Other tests (global range, spike, trend) passed on essentially every sample in the example file.


## What to distrust (and why)

**[HIGH] Conductivity-cell events → bad salinity and density.** The conductivity cell can foul or
clog, producing salinity drops of ~1–3 PSU (occasionally to physically impossible values) lasting
days to weeks; density inherits the error. Project experience at Slope Base logged events in
Dec 2015, Jul 2016, Dec 2017, Dec 2018, Sep 2019, Nov 2021, and Oct–Nov 2025.
*(argosy, [`sensor_exclusions.csv`](https://github.com/robfatland/argosy/blob/master/sensor_exclusions.csv))*
Check: does salinity drop while temperature doesn't move? Is conductivity QARTOD-suspect? Treat
those windows as bad, not as freshwater events.

**[MEDIUM] Isolated salinity spikes ("erratics").** Single-sample conductivity glitches show up as
spikes in salinity and density. Project experience: a multi-scale detector removes them well
before analysis. *(argosy, `PP06_Filters.md` → Filter 1)*

**[MEDIUM] Oxygen sensor response time.** Membrane oxygen sensors of this class respond in
seconds, not instantly (slower in cold water). At the profiler's ~5 cm s⁻¹ ascent this smears and
shifts sharp oxyclines by roughly tens of centimeters; ascent and descent profiles disagree slightly
in strong gradients. Matters for fine-scale oxycline work; negligible for most uses.

**[MEDIUM] Use the ascent.** The shallow profiler measures on the way up at ~5 cm s⁻¹ (1 Hz ≈
5 cm vertical spacing); descent is faster and treated as second-class.
*(argosy, `SensorTable.md`, `DescentData.md`)*

**[MEDIUM] Expect low oxygen at depth.** Values well below 100 µmol kg⁻¹ in the lower part of the
profile (example file: min 67, median 94 µmol kg⁻¹) are real — the region has an oxygen-minimum
zone below — not a sensor fault.


## Mixed layer depth (MLD) from these data

- **Threshold method (standard):** MLD = the depth where potential density first exceeds its
  value at a ~10 m reference depth by **0.03 kg m⁻³** (or temperature drops by 0.2 °C).
  de Boyer Montégut et al. 2004, JGR, doi:10.1029/2004JC002378.
- **Hybrid algorithm:** combines threshold, gradient, and curve-shape criteria; more robust on
  messy profiles. Holte & Talley 2009, J. Atmos. Oceanic Technol., doi:10.1175/2009JTECHO543.1.
- **[MEDIUM] Shallow-profiler caveat:** the profiler's shallowest point is often 5–20 m, sometimes
  deeper — check that each profile actually reaches your reference depth before applying a
  threshold; otherwise the "MLD" is undefined, not shallow.
- **Hand-labeled MLDs for validation:** a single-annotator set of human-picked MLDs on Slope Base,
  Oregon Offshore, and Axial Base shallow-profiler profiles (temperature, salinity, density, DO),
  intended as training/validation data. Zenodo, concept DOI 10.5281/zenodo.23650418
  *(argosy project)*.


## Shallow profiler specifics

- **[HIGH]** The delivered stream is **continuous**: it includes time parked at the ~200 m
  platform between profiles (48% of samples are below 150 m in the example file). Split it into
  up-casts with the RCA **profile index** (start / peak / end of every profile):
  [OOI-CabledArray/profileIndices](https://github.com/OOI-CabledArray/profileIndices).
- The profiler makes **9 profiles a day**; all of them carry CTD and oxygen data.
  *(argosy, `SensorTable.md`)*


## Further reading

- Processing specifications: [Density](https://oceanobservatories.org/wp-content/uploads/2023/09/1341-00050_Data_Product_SPEC_DENSITY_OOI.pdf),
  [Practical Salinity](https://oceanobservatories.org/wp-content/uploads/2023/09/1341-00040_Data_Product_SPEC_PRACSAL_OOI.pdf)
- [OOI: Interpreting QC variables and results](https://oceanobservatories.org/knowledgebase/interpreting-qc-variables-and-results/)
- OOI Biogeochemical Sensor Data **Best Practices & User Guide** (oxygen chapter): [PDF](https://oceanobservatories.org/wp-content/uploads/2025/07/OOI-Biogeochemical-Sensor-Data-Best-Practices-and-User-Guide-Version-1.1.1-with-July-dated-GOOS-Endorsement-Certificate-on-p2-Updated-DOI.pdf)
- TEOS-10 and the Gibbs SeaWater (GSW) toolbox: [teos-10.org](https://www.teos-10.org/)
- Community-published gridded CTD + DO products: Zenodo [nsf-ooi community](https://zenodo.org/communities/nsf-ooi)
  (e.g. "Gridded OOI Washington Offshore Profiler Mooring (CE09OSPM) CTD + DO").
