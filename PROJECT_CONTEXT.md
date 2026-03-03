## TCG Market Predictor – Working Context

This file is a lightweight snapshot of what we’ve built so far and where we’re going next. You can extend or edit it anytime; I’ll read it on future sessions to quickly re-sync.

---

## 1. High-level goal

Build a **Pokémon TCG “PriceCharting++”** style tool that:
- Normalizes raw and graded eBay sales into clean canonical cards/sets.
- Provides **per-card**: fair value now (+ CI), 30/90-day trend & simple forecast, liquidity score, risk score, grading EV.
- Provides **set-level**: set index, top movers, liquidity, and grading targets.

MVP focus: Pokémon singles, raw + graded, sourced from eBay sold data (CSV/API), with simple but robust analytics and a clean UI.

---

## 2. Backend overview (FastAPI, Postgres)

Key modules:
- `app/core/config.py`: central config (DB URL, eBay, currency, etc.).
- `app/db/models.py`:
  - `Sale`: eBay sale rows with `total_price_usd`, `sold_at`, `grade_company`, `grade_value`, `language`, `card_id`, etc.
  - `Set`: `set_slug`, `set_name`, `game`.
  - `CardIdentity`: canonical cards (`card_id = set_slug/card_slug`, `set_id`, `name`, `number`, `image_url`, etc.).
- `app/services/title_parser.py`: parsing titles into name / set / number / language.
- `app/services/currency.py`: convert to USD.
- `app/services/card_image.py`: resolves Pokémon TCG images, optionally cached on `CardIdentity.image_url`.
- `scripts/backfill_sets_and_cards.py`: backfills `sets` + `card_identities` from titles and sets canonical `sales.card_id`.

### 2.1 Card detail API (`/api/v1/cards`)

`GET /api/v1/cards/search`
- PriceCharting-style search:
  - Prefer `CardIdentity` + `Set` for canonical results (`name`, `set_name`, `number`, canonical `card_id = set_slug/card_slug`).
  - Fallback groups raw `Sale.title` parses when no identities found.

`GET /api/v1/cards/{card_id}`
- `card_id` is usually `set_slug/card_slug` (canonical), but legacy title is supported.
- Resolves all relevant sales and returns `CardDetail`:
  - Identity: `card_id`, `set_slug`, `card_slug`, `name`, `set_name`, `number`, `image_url`.
  - **Fair value now**:
    - `fair_value_now`: median of last 14 days of **daily median price**.
    - `fair_value_ci_low`, `fair_value_ci_high`: ±15% band around `fair_value_now`.
  - **Trend & forecast (Option A)**:
    - `history`: daily series of `{date, median_price, sales_count}` from all sales (USD).
    - `change_30d_pct`: median in last 30 days vs previous 30 days.
    - `change_90d_pct`: median in last 90 days vs previous 90 days.
    - `forecast`: simple 30-day horizon of `{date, p10, p50, p90}` with:
      - `p50 = fair_value_now`; `p10/p90 = ±15%` band.
      - `forecast_horizon_days = 30`.
  - **Liquidity & risk**:
    - `liquidity_score`: derived from sales/week (5+ per week ~ 100).
    - `risk_score`: scaled std-dev of price returns (higher = more volatile).
  - **Raw pricing**:
    - `raw_low_usd`, `raw_median_usd`, `raw_high_usd`, `raw_sales_count` from ungraded sales.
    - `raw_by_condition`: buckets (NM/LP/MP/HP/Damaged/Unknown) with median and count.
  - **Graded & grading EV**:
    - `graded_price_bands`: value bands by company (low/median/high + count).
    - `prices_by_grade`: per-grade median/count across companies.
    - `grade_distribution`: grade histograms per company.
    - `grading_upside`: EV uplift vs raw, given a grading cost.
  - **Recent sales**: small list of recent contributing comps.

`GET /api/v1/cards/series`
- Returns multi-line daily series by company/grade (and optional raw-by-condition) for the “Market movement” chart.

### 2.2 Metrics & movers (`/api/v1/metrics`)

- `/summary`: total sales, by-language distribution, raw vs graded counts.
- `/by-grade`: buckets by grade value (incl. “raw”).
- `/by-company`: aggregates by grading company with per-grade breakdown.
- `/ten-rate`: fraction of 10s by company and overall.
- `/movers`: global big-mover list:
  - For each `card_id`, uses a window vs previous window:
    - `value_now = median raw price (last window_days)`.
    - `value_prev = median raw price (prev window_days)`.
    - `change_pct = (now - prev) / prev`.

### 2.3 Sets & set analytics (`/api/v1/sets`)

`GET /api/v1/sets`
- Returns `SetSummary[]` with `set_slug`, `set_name`, `game`, `card_count`.

`GET /api/v1/sets/{set_slug}/cards`
- Returns canonical cards in the set (`CardInSet[]`), with `card_id`, `card_slug`, `name`, `set_name`, `number`.

`GET /api/v1/sets/{set_slug}/analytics`
- Returns `SetAnalytics` for a given set:
  - `total_sales`, `raw_sales`, `graded_sales`.
  - `language_filter`: `null` or `"en" | "jp" | "other"`.
  - `top_movers_30d` / `top_movers_90d`:
    - Each `SetTopCard` has `card_id`, `name`, `value_usd`, `change_pct`.
    - SQL uses end-of-series `sold_at` per card, then compares median in recent window vs windows ending 30/90 days back.
  - `top_liquidity`:
    - Sorted by `sales_per_week`, computed from first/last `sold_at`.
  - `index_history`: daily median price across all cards in the set (USD).
- Supports optional `?language=en|jp|other`:
  - Applied to counts, movers, liquidity, and index history.

### 2.4 Grading targets (`/api/v1/targets/grading`)

- Returns global or set-filtered grading targets with:
  - `raw_count`, `raw_median_usd`, `graded_count`.
  - `best_company`, `best_ev_usd`, `best_upside_usd`.
  - Filters: `set_slug`, `language`, `min_raw_sales`, `min_graded_sales`, `min_sales_per_week`, `max_volatility`, `min_upside_usd`.

---

## 3. Frontend overview (React, single-page)

Main file: `frontend/src/App.tsx`

Top-level views (header nav):
- **Search (default)** – card search + card detail.
- **Sets** – browse sets and open set dashboards.
- **Targets** – global grading targets.
- **Market metrics** – overall stats.
- **Big movers** – global movers table.

### 3.1 Card search & detail

Search:
- Calls `/api/v1/cards/search?q=...&language=...`.
- Displays clean results:
  - Line 1: card name.
  - Line 2: `Set · #number`.
  - Click → loads card detail via `/api/v1/cards/{card_id}`.

Card detail page:
- Header:
  - Image (from `image_url`), title, set + number.
  - Grade info for graded cards; shows “Raw / unspecified grade” otherwise.
  - **Set name is clickable when `set_slug` is present**:
    - Clicking:
      - Sets URL hash `#set={set_slug}`.
      - Switches to **Sets** view and loads that set dashboard.
- Key metrics grid:
  - **Fair Value Now** with 95% CI.
  - **Liquidity score**.
  - **Risk score**.
  - **Trend**:
    - Shows 30d and 90d % change.
    - Green for positive (`.up`), red for negative (`.down`).
  - **Raw value band**:
    - Median, low (10th percentile), high (90th percentile), and raw sales count.
- **Raw by condition** table:
  - Conditions (NM, LP, MP, HP, Damaged, Unknown).
  - Sales count + median USD, sortable by condition / median / count.
- **Market movement chart**:
  - If filtered series loaded (`/api/v1/cards/series`): multi-line chart by company/grade (and optional raw-by-condition).
  - Else: simple `LineChart` from `history`.
  - **Forecast band**:
    - `LineChart` accepts optional `forecast` from `CardDetail`.
    - Draws a shaded band for p10–p90 over the forecast period, with the p50 line extended.
- **Grade grid & prices by grade**:
  - Grid of grades by company (PriceCharting-style).
  - Table of prices by grade across companies.
- **Grading upside**:
  - Shows raw vs best graded EV, highlighting “worth grading?” decision.
- **Recent sales**:
  - Last few comps (date, price, grade, condition, title).

### 3.2 Sets view (browse by set)

Access via **“Sets”** nav tab.

Controls:
- Search box: filter by set name.
- **Language dropdown**: `All`, `English (en)`, `Japanese (jp)`, `Other`.
  - When a set is selected, changing this:
    - Reloads `/api/v1/sets/{set_slug}/analytics?language=...`.
    - Reloads set-level grading targets with matching `language`.

Behavior:
- Left panel:
  - List of sets from `/api/v1/sets` (shows `Set Name — N cards`).
  - Clicking a set:
    - Sets hash to `#set={set_slug}`.
    - Calls `loadCardsInSet(set_slug)`, which:
      - Fetches `/sets/{set_slug}/cards`.
      - Fetches `/sets/{set_slug}/analytics` (with `language` if selected).
      - Fetches `/targets/grading?set_slug=...` (with same `language`).
- Right panel (when a set is selected):
  - **Set index chart**:
    - `LineChart` of `index_history` (daily median).
  - **Summary cards**:
    - Total sales, Raw, Graded (respecting `language_filter` when set).
  - **Top movers (30d)** table:
    - Card, median price, % change; clicking a row loads that card detail.
  - **Top liquidity** table:
    - Card, median price, sales/week; rows clickable to card detail.
  - **Top grading targets (in set)**:
    - Small subset (limit ~10) of grading targets for that set.
  - **Cards in set list**:
    - Each row is clickable → loads card detail.
  - Button: **“Show targets for this set”**:
    - Pre-fills `set_slug` in the **Targets** view.

Deep linking:
- On initial load, app checks `window.location.hash`:
  - If it starts with `#set=...`, it:
    - Switches to **Sets** view.
    - Calls `loadCardsInSet(set_slug)` to populate the dashboard.
- When you click a set in the list, it updates the hash so the URL is bookmarkable.

### 3.3 Targets view

- Shows global grading targets from `/api/v1/targets/grading`.
- Filters:
  - Language (en/jp/other).
  - `set_slug` (text input, prefilled when coming from Sets view).
  - Min raw/graded sales, grading cost, min sales/week, max volatility, min upside USD.
- Table includes:
  - Card name, set info, best company, EV and upside, liquidity, volatility.
- Export:
  - CSV export of current targets table for offline analysis.

### 3.4 Market metrics & Big movers

**Market metrics**:
- Uses `/api/v1/metrics/summary`, `/by-grade`, `/by-company`, `/ten-rate`.
- Cards show total sales, raw vs graded, by-language counts, grade/ company breakdowns.

**Big movers**:
- Uses `/api/v1/metrics/movers`.
- Filters:
  - Language, window days, min sales now/prev.
- Table:
  - Card, `value_now_usd`, `value_prev_usd`, % change, sales now/prev.
- Rows clickable → go to card detail.

---

## 4. How to run everything locally

Backend:
```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Make sure DB is running & migrated, then:
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Optional backfill after loading some `sales` data:
```bash
cd backend
source venv/bin/activate
python -m scripts.backfill_sets_and_cards
```

Frontend:
```bash
cd frontend
npm install   # first time only
npm run dev   # then open the printed URL in a browser
```

---

## 5. Roadmap / next ideas

You can edit this section as we go. Current ideas:

- **Per-card analytics**
  - Replace heuristic trend/forecast with a more robust time-series model (e.g. simple ARIMA/ETS or Bayesian).
  - Add scenario bands (bear/base/bull) derived from model uncertainty instead of ±15%.

- **Set-level & cross-market views**
  - Add more filters to set analytics (e.g. min sales, only raw/only graded).
  - Set-level comparisons (e.g. index chart across multiple sets).

- **Grading EV**
  - Multiple grading cost presets per company.
  - Richer grade distribution modeling (Bayesian, Monte Carlo).

- **Data pipeline**
  - Swap manual CSV ingest for scheduled eBay API ingest in production.
  - Monitoring for volume, failure, and data drift.

- **UI/UX**
  - Dark mode toggle.
  - Saved filters / presets for power users (e.g. “JP only, high-liquidity cards”).

Add anything you care about here; I’ll treat this file as the source of truth for context when you come back.

