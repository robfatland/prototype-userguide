# Getting OOI data: ordering, access routes, and a resolution trap

*Unofficial. Part of [prototype-userguide](llms.txt). Every claim cites a source; official sources
take precedence. For shallow-profiler structure (profiles, GPI, ascent/descent) read
[Shallow profiler operations](shallow-profiler.md) first.*

**Impact ratings:** **[HIGH]** will mislead your analysis if ignored · **[MEDIUM]** matters for
some analyses · **[LOW — report to data team]** a defect worth reporting, but usable as is.

There are several ways to get OOI data, and **they do not all give you the same thing** — the
biggest surprise for shallow-profiler users is that some routes deliver **downsampled** data by
default (see "The resolution trap"). Pick the route that matches what you need.


## The routes at a glance

| Route | What it is | Best for | Resolution |
|---|---|---|---|
| **OOINET** (Data Portal) | The legacy ordering interface; builds a custom NetCDF order on demand | Full-resolution raw/calibrated NetCDF for specific instruments + time ranges | **Full** (native sampling) |
| **Data Explorer** | The newer web tool to search, plot, and download | Discovery, quick plots, cross-instrument comparison | **Binned to 1-minute** for high-rate cabled data (see below) |
| **ERDDAP** | Standard data server behind Data Explorer downloads | Scripted/subset downloads (CSV, NetCDF) | 1-minute binned product (the Data Explorer product) |
| **THREDDS / OPeNDAP** | Catalog of pre-generated datasets for common instruments | Streaming subsets into Python/MATLAB without bulk download | Pre-generated datasets |
| **Gold Copy** | The full-resolution archive of delivered datasets | The complete, full-rate time series | **Full** |

Sources: [OOI Data Access](https://oceanobservatories.org/data-access/),
[ERDDAP server](https://oceanobservatories.org/erddap-server/),
[THREDDS quick start](https://oceanobservatories.org/thredds-quick-start/),
[Data Explorer docs](https://dataexplorer.oceanobservatories.org/help/).


## Ordering raw data from OOINET

OOINET (the Data Portal, `ooinet.oceanobservatories.org`) builds a NetCDF **to order**:

1. Find the instrument by site/node/instrument (e.g. Slope Base shallow profiler CTD =
   `RS01SBPS-SF01A-2A-CTDPFA102`) and pick a **time range**.
2. Submit the request. OOINET processes it **asynchronously** — it converts raw data into a
   processed dataset using the latest algorithms and calibrations at request time, so the same
   request re-run later can differ if calibrations changed.
   [OOI: on-demand processing](https://oceanobservatories.org/knowledgebase/what-should-i-do-if-i-dont-get-an-email-from-the-data-portal/)
3. You get an **email with a link** to the staged files when the order is ready; download from
   there.
4. The delivered file is a **continuous, full-resolution stream** (ascent + descent + time parked
   at the platform) — not split into profiles. Cut it into profiles yourself with the profile
   index: see [Shallow profiler operations](shallow-profiler.md).

- **[MEDIUM]** The order dialog offers options (restrict to certain parameters; include
  provenance; include annotations). Fewer parameters = smaller, faster orders. If unsure which
  you need, ordering everything is the safe (if larger) default.
- This is the route to use when you want the **native-resolution** data the instrument guides in
  this corpus describe.


## The resolution trap (read this before using Data Explorer / ERDDAP for SP data)

**[HIGH] Shallow-profiler sensors sample fast, and the convenient routes downsample them.** For
high-resolution cabled instruments, the product served through **Data Explorer and its ERDDAP
downloads is binned to 1-minute resolution** — a lighter product for visualization and quick
downloads, **not** the full time series.
([OOI ERDDAP server](https://oceanobservatories.org/erddap-server/): *"this product is binned to
1-minute resolution … for users that do not need the full-resolution, gold copy time series."*)

Why this matters for the shallow profiler: the pod ascends at ~5 cm s⁻¹ and these sensors sample
at ~1 Hz or faster (PAR ~3.6 Hz, CTD 1 Hz) — so native data is ~5 cm (or finer) in the vertical.
**1-minute binning is ~3 m vertical** bins on ascent, which will **smear thin features** (sharp
pycnoclines, thin chlorophyll layers, the near-surface structure you need for MLD). If you are
studying fine vertical structure, the 1-minute product is the wrong one.

- For **full-resolution** shallow-profiler data use **OOINET** (order) or the **Gold Copy**
  archive, not the default Data Explorer/ERDDAP download.
- The Interactive Oceans Data Portal uses **Datashader decimation** for its plots — a plotting
  optimization, not a stored product; good for exploring, but the picture is decimated too.
  [Interactive Oceans Data Portal](https://interactiveoceans.washington.edu/data-portal/)
- If you downsample yourself, there is an OOI example notebook for requesting and downsampling
  high-resolution profiler data (CTD, fluorometer):
  [Downsampling high-resolution timeseries](https://oceanobservatories.org/knowledgebase/downsampling-high-resolution-timeseries-datasets/).


## Which route should I use?

- **I need fine vertical structure / native resolution** (MLD, thin layers, internal waves) →
  **OOINET order** or **Gold Copy** (full resolution). Then split into profiles with the profile
  index.
- **I want to browse, plot, or grab a quick subset** → **Data Explorer / ERDDAP** — but remember
  it's the **1-minute** product for cabled sensors.
- **I want to stream subsets into code** → **THREDDS/OPeNDAP** (check whether the pre-generated
  dataset is full-resolution or binned for your instrument).


## Further reading

- [OOI Data Access overview](https://oceanobservatories.org/data-access/)
- [Data Explorer documentation](https://dataexplorer.oceanobservatories.org/help/)
- [OOI ERDDAP server](https://oceanobservatories.org/erddap-server/) ·
  [THREDDS quick start](https://oceanobservatories.org/thredds-quick-start/)
- [Shallow profiler operations](shallow-profiler.md) — profiles, GPI, ascent vs descent.
