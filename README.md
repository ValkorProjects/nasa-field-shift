# nasa-field-shift
A project submitted to the 2026 NASA Space Apps challenge for the theme: Field Shift: Adapting Farms with NASA Data

Field Shift is a free decision-support tool for farmers in São Paulo state. For each field it compares the current crop rotation with 2 alternatives using NASA Earth observations, local soil, crop traits and the farmer's priorities, and warns before planting when a crop is likely to fail. **It supports the farmer and the agronomist; it does not replace them.**

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
npm run dev        # front end with sample data (mock)  → http://localhost:5173
npm run dev:api    # front end calling the backend at /api
npm run build      # production build in frontend/dist/
```

## Running the backend

**Locally:**

1. Run `cd ./backend`
2. Run `pip install "fastapi[standard]" requests` or `pip install fastapi requests`
3. Run `fastapi dev main.py` or `uv fastapi run dev` (serves on http://localhost:8000, docs at `/docs`)

Current endpoints (NASA POWER, comma-separated `parameter`, e.g. `T2M,RH2M`):

| Endpoint | What it returns |
|---|---|
| `GET /nasapower/point` | values for one point and period (`parameter`, `longitude`, `latitude`, `year_start`…`day_end`) |
| `GET /nasapower/plot` | daily series for the same query, at most 5 parameters |

`GET /api/recommendation` (below) is not implemented yet (issues #4/#5); until then the front end uses its mock.

**Front end + back end together:**

1. Start the backend as above (port 8000).
2. In another terminal, run `npm run dev:api`.

In dev, Vite proxies every `/api/*` call to the backend, so the browser never sees a CORS error. To use another backend address, copy `frontend/.env.example` to `frontend/.env.local` and change `VITE_BACKEND_URL`. Never commit `.env` files.

| Setting | Values | Default |
|---|---|---|
| `VITE_API_MODE` (or `npm run dev:api`) | `mock` · `api` | `mock` |
| `VITE_BACKEND_URL` | backend used by the dev proxy | `http://localhost:8000` |

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
src/components/                   AppShell, SideNav, Chip, SampleValue, StrategyCard, TimelineChart, …
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
- Fields are saved in the browser (`localStorage`) and can be downloaded as **GeoJSON** (`fields.geojson`), which is the input for the Python pipeline.
- The 3 sample fields are traced on crop fields near Taquarituba (SP). Their colours are sample values; only Field 1 has sample results.

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
| `strategies[].money.*`, `money.at_risk_*` | R$ results | FAO-33: 1 − Ya/Ym = Ky(1 − ETa/ETm); loss = area × yield × loss × price |
| `money.inputs[]` | Numbers we used | IBGE PAM (yield), CEPEA (price), CONAB (cost), FAO + GPM (loss) |
| `regional.*` | SP regional scenario | IBGE PAM / CONAB area × share affected × yield loss; past CONAB + CEPEA |

### Rules computed in the front end

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

**`mode`** tells where the data came from: `live` (NASA POWER just fetched), `cache` (a previous live response saved in `backend/data/cache/`) or `mock` (static offline slice of a demo point). Lookup order is cache, live, mock. Set `FIELD_SHIFT_OFFLINE=1` to skip the live call. Before a demo, make one warm-up call per point so the cache is filled. `NASA_POWER_TIMEOUT` (seconds, default 30) controls the request timeout.

**"Forecast" = climatological risk.** The recommendation is the frequency of past events (2015-2024) for each planting date during the crop's critical stage. It is not a weather forecast.

## Thresholds and sources

- Frost / cold: daily minimum temperature at 2 m <= 3 C (Embrapa: damage begins with shelter air < 3 C because the surface is 3-6 C colder). Indirect reference, not specific to corn.
  - https://www.alice.cnptia.embrapa.br/alice/bitstream/doc/909515/1/95103GEADA.pdf
  - https://www.infoteca.cnptia.embrapa.br/infoteca/bitstream/doc/927281/1/Climaepoca.pdf
- White mold: 3+ consecutive days with mean temperature 15-22 C and relative humidity >= 85 %.
  - https://www.infoteca.cnptia.embrapa.br/infoteca/bitstream/doc/1094445/1/CT140mofobrancoOL.pdf
  - https://www.infoteca.cnptia.embrapa.br/infoteca/bitstream/doc/1147086/1/Circ-Tec-189.pdf

## Mocked / hardcoded

- Crop cycles (days after planting): corn flowering/grain filling 60-110, soybean R1-R3 45-75.
- Risk cut-offs: <= 10 % recommended, <= 30 % risky, above that avoid.
- White mold rule (3 days / 85 % / 15-22 C) is a project heuristic.
- Sowing windows: corn Jan 1 - Apr 30 (second crop), soybean Sep 1 - Dec 31.
- Demo points: Taquarituba, Itapeva and Capao Bonito (SP).
- `mock` mode serves a static slice of real NASA POWER data fetched once with `build_demo_slice`.
- Fixed analysis period 2015-2024.
