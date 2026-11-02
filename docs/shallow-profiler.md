# Shallow profiler operations: profiles, daily index, the profile index, and redux

*Unofficial. Part of [prototype-userguide](llms.txt). Read this before any shallow-profiler
instrument guide — they all assume it. "Project experience" items come from the
[argosy](https://github.com/robfatland/argosy) project; checked facts are marked "verified".*

**Impact ratings:** **[HIGH]** will mislead your analysis if ignored · **[MEDIUM]** matters for
some analyses · **[LOW — report to data team]** a defect worth reporting, but usable as is.


## The platform

- The Regional Cabled Array (RCA) shallow profiler is a **science pod on a winch**, parked on a
  platform moored at **~200 m**. Several times a day it is winched up to near the surface and
  back down, carrying its sensors through the upper water column.
  [Interactive Oceans: Shallow Profiler Moorings](https://interactiveoceans.washington.edu/technology/shallow-profiler-moorings/)
- **Three sites** (two-letter codes used in this guide; OOI designators in the file names):

  | Code | Site | Designator | Node | Nominal lat, lon |
  |---|---|---|---|---|
  | `sb` | Oregon Slope Base | `RS01SBPS` | `SF01A` | 44.53 N, 125.39 W |
  | `oo` | Oregon Offshore | `CE04OSPS` | `SF01B` | 44.37 N, 124.96 W |
  | `ab` | Axial Base | `RS03AXPS` | `SF03A` | 45.83 N, 129.75 W |

  *(argosy, `ooipaths.py`)*
- **Delivered files are continuous streams**, not profiles: they include ascent, descent, and the
  time parked at the platform. **[HIGH]** You must cut the stream into profiles yourself (below).
- **Deployments:** the profiler is recovered and redeployed periodically; each delivered file has
  a `deployment` number. Expect gaps around turnovers and calibration changes across them.


## One profile, three phases

Every profile is **ascent → descent → rest**. Typical durations (verified from the 2024 Slope
Base profile index, medians):

| Phase | Duration | Speed / notes |
|---|---|---|
| Ascent (`start` → `peak`) | **67 min** | ~5 cm s⁻¹; the **science** phase for most sensors |
| Descent (`peak` → `end`) | **34 min** — or **95 min** on profiles #4 and #9 | ~10 cm s⁻¹; #4 and #9 stop at set depths |
| Rest (until next `start`) | ~30–70 min | parked at the ~200 m platform |

- **[MEDIUM] Use the ascent for science.** The sensors sit at the top of the pod, so on the way
  up they meet undisturbed water; on the way down the pod falls through water it has just
  stirred. Descent data are noisier and treated as second-class (still useful for checking
  stability between the two passes). *(argosy, `DescentData.md`)*
- **Exception:** pH and pCO₂ measure **on descent** by design (see daily index).


## The daily index (1–9) and which sensors run when

- The profiler normally makes **9 profiles per day**. The **daily index** is a profile's position
  (1–9) within the **UTC day**.
- **Profiles #4 and #9 are special:** they have the long (~95 min), stop-and-go descents
  (verified). #4 peaks around **08:30 UTC ≈ local midnight**; #9 around **21:50 UTC ≈ 13:50 local**
  (Pacific standard time; an hour later in local daylight time).
- **Sensor duty cycles** (from 2017 on; in 2015–2016 the sparse sensors ran on more profiles):

  | Sensors | Profiles | Phase | Points per profile |
  |---|---|---|---|
  | CTD (T, S, density, DO), FLORT (chl, CDOM, backscatter), PAR | all 9 | ascent | hundreds–thousands (~1 Hz) |
  | Nitrate (SUNA) | #4 and #9 | ascent | ~150 |
  | pH (SAMI-pH), pCO₂ | #4 and #9 | descent, at the stops | ~10 |

  *(argosy, `SensorTable.md`)* pH files also appear for the other 7 profiles, but those hold a
  single reading at the platform (~190 m), not a profile.
- **[HIGH] Don't find #4 and #9 by counting.** Only 247 of 2024's days at Slope Base had all 9
  profiles (verified). On a day with a missing profile, "the 4th profile of the day" is the wrong
  profile. Identify them by their **long descent** (`end − peak` well above ~60 min) or by start
  time window.


## The profile index (and "GPI")

- **What it is:** a public table, maintained by the RCA data team, of **every profile** each
  profiler has made: a running **profile number** plus three UTC times — `start` (ascent begins),
  `peak` (shallowest point: ascent ends, descent begins), `end` (descent ends).
  [OOI-CabledArray/profileIndices](https://github.com/OOI-CabledArray/profileIndices)
- **GPI = global profile index** = that running profile number. It starts at **1** when a
  profiler begins operating and counts up forever (Slope Base passed 20,000 in early 2026). For a
  given profiler, **a GPI names exactly one profile** — it's the cleanest key for linking data,
  labels, and products across instruments. *(argosy, `Sharding.md`)*
- **Files:** one CSV per profiler per year, `<DESIGNATOR>_profiles_<YYYY>.csv` (e.g.
  `RS01SBPS_profiles_2018.csv`), columns `profile,start,peak,end`. Shallow profilers end in `PS`;
  deep profilers (`PD`) have their own files. Direct download:
  `https://raw.githubusercontent.com/OOI-CabledArray/profileIndices/main/RS01SBPS_profiles_2018.csv`
- **Times are UTC** and match the `time` variable in delivered files (verified).

**Cutting a delivered stream into ascents (the core procedure):**

```python
import pandas as pd
import xarray as xr

idx = pd.read_csv("https://raw.githubusercontent.com/OOI-CabledArray/profileIndices/main/"
                  "RS01SBPS_profiles_2018.csv", parse_dates=["start", "peak", "end"])
ds = xr.open_dataset("deployment0004_RS01SBPS-...-ctdpf_sbe43_sample_....nc")
ds = ds.swap_dims({"obs": "time"}).sortby("time")

t0, t1 = ds.time.values[[0, -1]]
for p in idx[(idx.start >= t0) & (idx.peak <= t1)].itertuples():
    ascent = ds.sel(time=slice(p.start, p.peak))     # descent: slice(p.peak, p.end)
    if ascent.sizes["time"] == 0:
        continue                                      # profile listed but no data in file
    gpi = p.profile
    # ... analyze or save one profile, keyed by gpi ...
```

- **[MEDIUM]** Some indexed profiles have no data in a given instrument's file (sensor off,
  gaps); always check for an empty slice.


## Redux: one file per profile per sensor (a project convention)

Working with month-long, multi-million-sample streams is slow and error-prone. The argosy project
cuts every stream once, up front, into small **"redux" (shard) files**: one NetCDF per profile per
sensor, holding just that sensor's variable plus `depth`, on a `time` dimension. Everything
downstream (QC, filtering, plots, labeling) then works profile by profile.
*(argosy, `Sharding.md`)* This is a project convention, not an OOI product.

- **Procedure:** for each instrument file → for each profile in the index that falls inside the
  file → slice `start→peak` (ascent sensors) or `peak→end` (descent sensors) → keep the one science
  variable + `depth` → write one file.
- **Filename (all fields positional):**
  `RCA_<site>_sp_<sensor>_<yyyy>_<ddd>_<gpi>_<daily>_<version>.nc`
  e.g. `RCA_sb_sp_temperature_2018_003_3752_4_V1.nc` = Slope Base shallow profiler, temperature,
  2018 day-of-year 003, GPI 3752, daily index 4, version 1 (ascent). Descent copies use version
  `V1D`.
- **Why it helps:** the GPI in the name joins sensors (same GPI = same profile = same time); the
  daily index finds the #4/#9 profiles for sparse sensors; and a quality decision ("drop this
  profile") becomes deleting or flagging one small file.
- **Results:** a year at one site is up to 365 × 9 files per sensor. Project experience:
  2,400–2,500 midnight and noon profile-days were recovered at Slope Base over 2015–2025.
  *(argosy, `Sharding.md`)*


## Time

- **[HIGH] Everything is UTC** — file `time`, the profile index, and the daily index. Convert to
  local time (`America/Los_Angeles`) only for interpretation (day vs night, quenching, diel
  migration).
- Delivered files carry several other time variables (`internal_timestamp`, `driver_timestamp`,
  `port_timestamp`, …). **Use `time`.**


## See also

- Instrument guides: [CTD + oxygen](ctd.md), [FLORT](flort.md).
- [Interactive Oceans: Shallow Profiler Moorings](https://interactiveoceans.washington.edu/technology/shallow-profiler-moorings/)
- argosy project docs: [`Sharding.md`](https://github.com/robfatland/argosy/blob/master/Sharding.md),
  [`SensorTable.md`](https://github.com/robfatland/argosy/blob/master/SensorTable.md),
  [`DescentData.md`](https://github.com/robfatland/argosy/blob/master/DescentData.md)
