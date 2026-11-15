# RollCrop

<img src="frontend/public/img/brand/rollcrop-logo.png" alt="RollCrop" width="260" />

RollCrop is our project for the 2026 NASA Space Apps Challenge, theme **Field Shift: Adapting Farms with NASA Data** (repository: `nasa-field-shift`).

RollCrop is a free decision-support tool for farmers in São Paulo state. For each field it compares the current crop rotation with 2 alternatives using NASA Earth observations, local soil, crop traits and the farmer's priorities, and warns before planting when a crop is likely to fail. **It supports the farmer and the agronomist; it does not replace them.**

> **Prototype:** every value in the app is sample data. Dotted (yellow) values will be replaced by real data.

## Repository layout

```
frontend/   Vue 3 + Vite app (this README covers it)
backend/    FastAPI app with the NASA POWER client (PR #10)
docs/       spec, data requirements, reference screens, API contract example
```

## Run

From the repository root:

```bash
npm run setup      # installs the front-end dependencies (once)
npm run dev        # front end + your local backend (http://localhost:8000) → http://localhost:5173
npm run dev:mock   # front end with sample data only, no backend needed
npm run build      # production build in frontend/dist/, calls https://rollcrop-backend.vercel.app
```

## Running the backend

**Locally:**

1. Run `cd ./backend`
2. Run `pip install "fastapi[standard]" requests` or `pip install fastapi requests`
3. Run `fastapi dev main.py` or `uv fastapi run dev` (serves on http://localhost:8000, docs at `/docs`)

Every endpoint lives under `/api/`. The full list is in [`backend/README.md`](backend/README.md#endpoints); `GET /api/recommendation`, `GET /api/weather`, `GET /api/soil` and `POST /api/field/profile` are detailed in "Recommendation API" below.

**Front end + back end together:**

1. Start the backend as above (port 8000).
2. In another terminal, run `npm run dev`.

In dev, Vite proxies every `/api/*` call to the backend, so the browser never sees a CORS error.

**Which backend each build calls.** The settings live in committed files (no secrets) in `frontend/`:

| Where | File | Backend |
|---|---|---|
| `npm run dev` (local development) | `.env.development` | your machine, `http://localhost:8000` (through the Vite proxy) |
| `npm run dev:mock` | `.env.mock` | none: sample data |
| `npm run build` / Vercel **production** (the `main` branch) | `.env.production` | `https://rollcrop-backend.vercel.app` |
| Vercel **preview** (the `dev` branch and pull requests) | `vite.config.js` | `http://localhost:8000`: the backend on the machine of whoever opens the preview |

Published front end: https://rollcropfrontend.vercel.app · back end: https://rollcrop-backend.vercel.app

To override on your machine, copy `frontend/.env.example` to `frontend/.env.local` (never committed). A `VITE_API_BASE` set in the Vercel project settings wins over these files.

| Setting | Values |
|---|---|
| `VITE_API_MODE` | `api` · `mock` (missing = `mock`) |
| `VITE_BACKEND_URL` | backend used by the dev proxy |
| `VITE_API_BASE` | backend URL called directly by a build (no proxy outside dev); the backend allows CORS |

If the backend is not running in `api` mode, the screen shows an error with **Try again** and **Use sample data**.

Desktop only (reference width 1280 px). On Vercel, set the project's **Root Directory** to `frontend` (`frontend/vercel.json` handles SPA routes).

## API contract: `GET /api/recommendation`

Draft contract between back end and front end for the **When to plant** screen (`/planting`, issue #7). The example response is [`docs/contract-example.json`](docs/contract-example.json); the front-end mocks are `frontend/src/api/mock/corn.json` and `soybean.json`.

Query: `lat`, `lon` (decimal degrees) and `crop` (`corn` | `soybean`).

| Field | Meaning |
|---|---|
| `location` | `{ name, lat, lon }` |
| `crop`, `crop_label` | crop id and display name |
| `season` | `{ start, end }`, the date range drawn on the timeline (ISO dates) |
| `recommendation` | `{ summary, explanation }`: one sentence plus why, in plain language |
| `windows[]` | `{ start, end, level, explanation }` with `level` = `recommended` · `risky` · `avoid` |
| `events[]` | `{ type, label, start, end, years_hit, years_total, threshold, explanation }`; `type` = `frost` · `white_mold` |
| `source` | `{ dataset, url, parameters[], period, mode, generated_at, note }`; `mode` = `live` · `cache` · `mock` (shown as a badge) |

Events are **past frequency** ("3 of the last 10 years"), never a forecast.

## Screens and routes

| # | Screen | Route |
|---|---|---|
| 1 | Mark field (map) | `/farm` |
| 2 | Crops | `/field/1/crops` |
| 3 | Soil | `/field/1/soil` |
| 4 | Priorities | `/field/1/priorities` |
| 5 | Results | `/field/1/results` |
| 6 | Strategy detail (drawer) | `/field/1/results/:option` (`current`, `a`, `b`) |
| 7 | Pre-planting alert | `/farm/alert` |
| 8 | How we calculated | `/how` |
| 9 | Costs: your money | `/field/1/costs` |
| 10 | Costs: big picture | `/field/1/costs/big-picture` |
| 11 | When to plant (planting window + critical events) | `/planting?loc=…&crop=corn\|soybean` |

Reference screens and the original spec are in [`docs/`](docs/) (`PROMPT.md`, `DATA_REQUIREMENTS.md`, `CHANGELOG.md`, `placeholders.csv`, `reference/*.png`).

## Front-end layout (`frontend/`)

```
public/data/field-1.sample.json   sample data for Field 1 (screens 1–10)
public/img/                       illustrative images (crops)
src/api/index.js                  /api access with the mock/api flag, demo locations
src/api/mock/                     sample /api/recommendation responses (corn, soybean)
src/data/store.js                 loads the field JSON, keeps the farmer's answers,
                                  computes "Best for you" and "How sure are we?"
src/data/fields.js                the farmer's fields (polygons), area, GeoJSON export
src/components/                   AppShell, TopNav, Welcome, Onboarding, Chip, SampleValue, StrategyCard, TimelineChart, …
src/views/                        one file per screen
src/i18n/en.json                  UI strings (add pt.json later)
src/styles/prototype.css          visual rules ported 1:1 from the v3.3 prototype
src/styles/app.css                app-specific overrides
```

## Map and fields

Screen 1 uses a real satellite map (Leaflet):

- **Satellite photo:** Esri World Imagery. **Plant cover:** NASA MODIS NDVI 8-day (250 m). **Soil moisture:** NASA SMAP L4 (9 km, regional). The NASA layers come from NASA GIBS, with no login.
- Drag and zoom the map, search a town (OpenStreetMap Nominatim) or jump to your location.
- **Draw a new field:** click each corner, then *Finish field*. The area in hectares is computed from the polygon (geodesic).
- **Fix the border:** drag the corners, drag a small dot to add a corner, right-click a corner to remove it. Rename a field by editing its name.
- **Area (issue #39):** by default the map is limited to the MVP area, **Itaberá and Itapeva (SP)** (yellow outline), and a field must be fully inside it. *Explore another place in Brazil* switches to exploratory mode: any field in Brazil, live data only, with a permanent badge. Each field remembers its mode and sends it to the backend as `scope`. Outlines: `public/data/areas/` (`src/data/areas.js`).
- The app starts with **no field and no answers** (issue #38): the farmer draws a field, then chooses the crops, the soil answers and the order of priorities; results wait for those answers.
- Fields are saved in the browser under the local profile and can be downloaded as **GeoJSON** (`fields.geojson`), which is the input for the Python pipeline.

## Local profile and first visit (issue #38)

- **Local profile:** a nickname only, no password and no personal data. Everything stays in this browser (`localStorage`, keys `fieldshift.*`); several profiles can share a browser. If storage is blocked (private window), the app keeps working in memory for the visit. Code: `src/data/account.js`, `src/data/storage.js`.
- The profile menu (top right) can switch or create profiles, export or import a profile (JSON), reopen the welcome tour, delete the profile, or sign out and clear all RollCrop data.
- **Welcome tour:** 4 short steps on the first visit of a profile (what RollCrop does, draw your area, how to read results, where the data comes from). It can be skipped and reopened from *Help*.
- **Layout:** a top menu replaces the side bar. There is no global "sample data" banner any more: every value that is still an example keeps its own dotted mark and source label.

## Data format

The front end reads **one pre-computed JSON per field**. It never processes satellite data in the browser or on Vercel.

1. The app first tries `/data/field-1.json` (real data from the Python pipeline).
2. If that file is missing, it falls back to `/data/field-1.sample.json`.

To switch to real data, put `field-1.json` with the same shape in `public/data/`.

### Leaf values

Every value shown on screen is an object:

```json
{ "value": "7 of 10", "sample": true, "source": "GPM", "scale": "area" }
```

| Key | Meaning |
|---|---|
| `value` | What is displayed. `"[X]"` means no value yet. |
| `sample` | `true` renders with the dotted yellow style (`SampleValue`). Set to `false` for real data. |
| `source` | Short source name shown in the chip (`GPM`, `HLS`, `POWER`, `NASADEM`, `CEPEA`, …). |
| `scale` | `field` (measured on your field, 30 m) · `area` (data for your area, 9–50 km) · `est` (estimate) · `book` (crop knowledge) · `null` (user input / label). |

### Where each real value comes from

| JSON path | Shown as | Data / recipe |
|---|---|---|
| `field.area_ha` | Field size | Polygon area from the map |
| `field.slope`, `soil.slope_sat`, `soil.slope_pct` | Slope | NASADEM 30 m, mean slope inside the polygon |
| `field.harvest`, `field.planting`, `alert.planting`, `alert.weeks` | Dates | ZARC planting windows for the municipality |
| `soil.texture_est`, `soil.drainage_est` | "I don't know" estimate | SoilGrids 250 m / Embrapa |
| `strategies[].rows[0]` (Rain in April–May), `alert.rain_years` | Dry autumn | Years (of 10) where Apr–May GPM IMERG rain < ET₀ (POWER) × Kc (FAO-56) |
| `strategies[].rows[1]` (Frost), `alert.frost_years` | Frost | Years (of 10) with POWER `T2M_MIN` ≤ threshold in the crop's sensitive months |
| `strategies[].rows[2]` (Rain washing soil away) | Erosion | **Relative** RUSLE-like index: GPM erosivity × soil K × NASADEM LS × monthly cover. Low/some/high, never tons |
| `strategies[].rows[3]` (Soil left bare) | Bare months | Strategy calendar; for the current plan, days/year with HLS NDVI < threshold (cloud-free, 5-year mean) |
| `strategies[].rows[4]` (Feeds the soil) | Nitrogen | Yes if the plan includes a legume (crop table) |
| `strategies[].evidence.n` | "Corn seen on this field…" | HLS NDVI time series: two peaks per year = second crop |
| `strategies[].nodata` | "No field data for this crop" | `true` when the crop was never seen/declared on the field |
| `strategies[].fit` | Priority fit ✓ ~ ✗ | Good / OK / Poor per priority (agronomist table) |
| `confidence.rules` | How sure are we? | ≥10 years · main indicators field-level · GPM and POWER agree within X% · local soil info |
| `alert.smap_context` | Regional soil moisture | SMAP L4 9 km anomaly. **Always regional, never the field** |
| `strategies[].money.*`, `money.at_risk_*` | R$ results | **Live from public APIs**, see [Costs from public data](#costs-from-public-data) |
| `money.inputs[]` | Numbers we used | **Live:** IBGE PAM (yield, price), IBGE PAM + NASA POWER (loss), CONAB (cost to grow) |
| `regional.*` | State regional scenario | **Live:** IBGE PAM (area, production, price), IBGE IPCA (food prices) |

### Costs from public data

The Costs screens (`/field/1/costs`, `/field/1/costs/big-picture`) and the money bar on Results no longer use sample numbers. The browser calls free APIs directly (all allow CORS, no key) and caches the answers for 24 h in `localStorage`. The code is in `src/api/publicData.js` (fetchers) and `src/data/costs.js` (recipe).

| Step | Source | Recipe |
|---|---|---|
| Where is Field 1? | OpenStreetMap Nominatim + IBGE localidades | Field centroid → municipality → IBGE code |
| Dry autumns | NASA POWER, from the backend field profile when loaded (api mode), else monthly `PRECTOTCORR` fetched by the browser | Last 10 years; April + May rain below `DRY_AUTUMN_MM` (150 mm, `src/data/rules.js`), the same rule as the pre-planting alert |
| Yield | IBGE PAM table 839 (2nd-crop corn) and 1612 (wheat), last 10 harvests | Normal = mean of the other years; dry = mean of dry years; the state when the town has < 5 harvests |
| Price | IBGE PAM table 1612 | Value of production ÷ quantity, latest year, R$ per 60 kg bag (price received by farmers) |
| R$ per plan | — | Field area (map) × yield × price; second crop only, before costs; cover crop = R$ 0 |
| Loss if nothing changes | — | Area × (normal − dry yield) × price; worst = the worst dry year |
| Cost to grow | CONAB cost-of-production series (`public/data/conab-costs.json`) | Cash (variable) cost per ha in the nearest reference town with a season from the last 2 years; shown per plan as "after the cost to grow" |
| Big picture | IBGE PAM 839 (state and Brazil), 1612 (state price), IPCA table 7060 | Year with the biggest state 2nd-crop corn drop, price change that year, food/chicken/eggs 12-month IPCA in December |

**Cost to grow:** CONAB has no API, only one .xls per crop (one sheet per town and season). `frontend/scripts/build-conab-costs.cjs` downloads the 2nd-crop corn and wheat series, reads every sheet and writes `public/data/conab-costs.json` (run `npm i --no-save xlsx@0.18.5` then `node scripts/build-conab-costs.cjs` from `frontend/`). If any API fails, the screens show an error with *Try again* and keep the sample values.

### Rules computed in the front end

- **The 3 plans follow the farmer's crops** (`src/data/strategies.js`): the current plan is the summer and second crop the farmer chose. Options A and B are the crops our São Paulo catalog lists after that summer crop (`public/data/crop-catalog.json`, built from `backend/data/crops/` by `node scripts/build-crop-catalog-json.cjs`), documented pairs first. Each one shows its evidence status ("Documented" or "Hypothesis to validate") and the reference link. A cover crop fills the list when the catalog has fewer than 2 options. Only corn, wheat and the cover crop have RollCrop rules (rain/frost rows, Good/OK/Poor fit); any other crop is **Not rated**, with no invented scores, and is left out of "Best for you". The ranking needs at least 2 rated plans. The nitrogen row follows the plan's legumes (crop knowledge).
- **Best for you:** Σ (Good=2, OK=1, Poor=0) × weight of the farmer's priority order (4-3-2-1). Re-ranked live on the Priorities screen.
- **How sure are we?:** count of passed checks in `confidence.rules`: 4 = High, 2–3 = Medium, 0–1 = Low.

All thresholds and the Good/OK/Poor ratings are sample values and must be validated by an agronomist.

## What the app never claims

- GPM and POWER are **past records**, never a forecast.
- SMAP is **regional context**, never a measurement of the field.
- Erosion is **relative** (low/some/high), never tons.
- Food prices: history and mechanism only. **No price prediction.**

---

Prototype made with AI assistance. Images are illustrative, not AI-generated.

---

# Recommendation API

Endpoints used by the front end:

- `GET /api/recommendation?lat=&lon=&crop=corn|soybean` - best planting windows plus critical events.
- `GET /api/weather?lat=&lon=&start=YYYY-MM-DD&end=YYYY-MM-DD` - daily NASA POWER series (`null` = no data).

**Run / test** (from `backend/`):

1. `pip install -r requirements-dev.txt`
2. `pytest` (no network needed)
3. `python -m scripts.build_demo_slice [--point slug] [--force]` - downloads the offline slices into `backend/data/demo/`
4. `python -m scripts.build_soil_slice [--point slug] [--force]` - downloads the SoilGrids soil slices into `backend/data/demo/soil/` (pauses 15 s between points to respect the ISRIC rate limit)

**`GET /api/soil?lat=&lon=`** - soil profile (clay, sand, silt, organic carbon, pH in water) for 0-5, 5-15 and 15-30 cm, plus a 0-30 cm summary and the textural group. **SoilGrids 2.0 by ISRIC - complementary source, not NASA data (CC-BY 4.0, 250 m, modelled estimate).** Same `mode` logic as above (cache `backend/data/cache/soilgrids_v1_*`, then live, then the slice in `backend/data/demo/soil/`). `SOILGRIDS_TIMEOUT` (seconds, default 20) controls the request timeout; `SOILGRIDS_NEIGHBOR_PAUSE` (seconds, default 2) is the pause between calls of the neighbor-pixel search (up to 8 extra calls within ~1.6 km, only when the requested pixel is masked and the point has no demo slice). `source.sampling` is `requested`, `nearest_neighbor` or `curated_rural_pixel`. Returns 404 when SoilGrids has no data for the point (water, urban, outside coverage) and 503 when it is unavailable and there is no slice.

**`POST /api/field/profile`** - data package for one field (talhao). Body: `{ "field": <GeoJSON Polygon or Feature<Polygon>, [lon, lat] order, closed ring>, "name"?: string, "scope"?: "mvp" | "explore" }` (`name` is accepted but ignored for now). Always 200 for a valid polygon inside the scope; each block degrades on its own.

**Area scope (issue #39).** The MVP covers **Itaberá and Itapeva (SP)**, where the team loaded the satellite data:
- `scope: "mvp"` (default): the whole field (vertices, centroid and points along every edge) must be inside the union of the two municipalities, so a field can cross the border between them. Otherwise the answer is **422** with a readable message. Data can come from cache, live or the offline demo slices (`mode: "mock"`).
- `scope: "explore"`: any field inside Brazil (otherwise 422). **Live data only**: cache of live calls or the live APIs. No offline slice, no nearest demo point, and `FIELD_SHIFT_OFFLINE` is ignored. Without network a block is `unavailable` with the reason; it is never `mock`.
- The outlines are static files: `backend/data/areas/` and `frontend/public/data/areas/` (`mvp.geojson`: Itaberá 3521705 + Itapeva 3522406; `brazil.geojson`). They come from the IBGE "malhas" API and were downloaded once; nothing calls IBGE at run time.
- Of the offline demo slices, only Itapeva is inside the MVP area. Itaberá has no slice yet (`backend/scripts/build_demo_slice.py`). Business rules (alerts, scores, strategies) live in the front end: the back end only returns data with provenance. Example response: [`docs/contract-field-profile.json`](docs/contract-field-profile.json) (generated with `FIELD_SHIFT_OFFLINE=1` for the sample Field 1).

| Block | Content | Source |
|---|---|---|
| `field` | centroid, `area_ha`, bbox, `vertex_count`, `location_name` | computed from the polygon |
| `weather_summary` | monthly totals (`by_year_month`) and `climatology` for 2015-2024 | NASA POWER |
| `events` | calendar windows with frost / white-mold frequency (`years_hit` of `years_total`) | NASA POWER |
| `planting` | `corn` and `soybean`, identical to `GET /api/recommendation` | NASA POWER |
| `soil` | same body as `GET /api/soil` (without `source`, which moves to the block) | SoilGrids 2.0 (ISRIC) |
| `terrain` | `pending`: elevation and slope are being integrated in issues #11/#12 (`terrain_block()` in `backend/field_profile.py` is the single place to fill) | NASA SRTM / NASADEM (planned) |

Every block is `{ status, reason, source, data }`. `status` = `ok` · `unavailable` (source down, no slice, timeout or unexpected error) · `no_data` (soil only) · `pending` (terrain only); when not `ok`, `data` is `null` and `reason` explains why. Weather is read once and feeds `weather_summary`, `events` and `planting` (if it fails, all three are `unavailable`). If NASA POWER has nothing for the centroid, the nearest demo point within 50 km is used and `source` says so (`sampling: "nearest_demo_point"`, `sampled_point`, `distance_km`, `location_name`). Data read from an offline demo slice (`mode: "mock"`) is always reported this way, even when the field is next to the demo point; `sampling: "requested"` only means live/cache data for the field's own centroid, and `location_name` (also in `field`) is only set when the data comes from a demo point; soil has no such fallback. Weather and soil run in parallel with a budget of `FIELD_PROFILE_TIMEOUT_S` seconds (default 25); on timeout the block is `unavailable`; the slow query keeps running in the background and finishes by writing the cache, so a retry is fast. Invalid shapes return 422 with a readable `detail`: wrong type, holes, open ring, fewer than 4 positions, more than 1000 vertices, zero area, coordinates out of range, or an extent above 0.5 degrees. Limitation: self-intersecting polygons are not detected.

**`mode`** tells where the data came from: `live` (NASA POWER just fetched), `cache` (a previous live response saved in `backend/data/cache/`) or `mock` (static offline slice of a demo point). Lookup order is cache, live, mock. Set `FIELD_SHIFT_OFFLINE=1` to skip the live call. Before a demo, make one warm-up call per point so the cache is filled. `NASA_POWER_TIMEOUT` (seconds, default 30) controls the request timeout.

**"Forecast" = climatological risk.** The recommendation is the frequency of past events (2015-2024) for each planting date during the crop's critical stage. It is not a weather forecast.

## Thresholds and sources

- Frost / cold: daily minimum temperature at 2 m <= 3 C (Embrapa: damage begins with shelter air < 3 C because the surface is 3-6 C colder). Indirect reference, not specific to corn.
  - https://www.alice.cnptia.embrapa.br/alice/bitstream/doc/909515/1/95103GEADA.pdf
  - https://www.infoteca.cnptia.embrapa.br/infoteca/bitstream/doc/927281/1/Climaepoca.pdf
- White mold: 3+ consecutive days with mean temperature 15-22 C and relative humidity >= 85 %.
  - https://www.infoteca.cnptia.embrapa.br/infoteca/bitstream/doc/1094445/1/CT140mofobrancoOL.pdf
  - https://www.infoteca.cnptia.embrapa.br/infoteca/bitstream/doc/1147086/1/Circ-Tec-189.pdf

- Soil (SoilGrids): physical value = `mean / d_factor`, with the factor read from each API layer (clay/sand/silt g/kg to %, soc dg/kg to g/kg, pH*10 to pH). Summary = thickness-weighted mean of 0-30 cm.
  - Textural group: Embrapa SiBCS (2018) groups; sand/loamy sand via the USDA rule (silt + 2 x clay < 30).
  - Organic matter = organic carbon x 1.724 (van Bemmelen, Embrapa soil analysis manual); shown as derived.
  - SoilGrids: Poggio et al. (2021), SOIL 7, 217-240. https://soilgrids.org/

## Mocked / hardcoded

- Crop cycles (days after planting): corn flowering/grain filling 60-110, soybean R1-R3 45-75.
- Risk cut-offs: <= 10 % recommended, <= 30 % risky, above that avoid.
- White mold rule (3 days / 85 % / 15-22 C) is a project heuristic.
- Sowing windows: corn Jan 1 - Apr 30 (second crop), soybean Sep 1 - Dec 31.
- Demo points: Taquarituba, Itapeva and Capao Bonito (SP).
- `mock` mode serves a static slice of real NASA POWER data fetched once with `build_demo_slice`.
- Fixed analysis period 2015-2024.
- Soil `mock` mode serves a static SoilGrids slice of each demo point (`build_soil_slice`).
- Soil demo slices: SoilGrids masks the urban-center pixel of the Itapeva and Capao Bonito demo points, so `build_soil_slice` uses curated rural pixels (`SAMPLE_OVERRIDES`: Itapeva -24.00,-48.92; Capao Bonito -24.02,-48.36), checked manually on 2026-11-15; the API reports `source.sampled_point` and `distance_km`.
- Soil is simplified to a 0-30 cm weighted mean and a textural group; there is no drainage indicator (no sourced rule yet).
