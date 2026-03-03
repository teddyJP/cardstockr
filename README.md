## TCG Predictor – MVP Skeleton

This repo contains an MVP skeleton for an AI-powered **TCG / sports card market predictor**, starting with **Pokémon PSA-graded singles** and eBay sold data.

### Structure

- **backend/** – FastAPI app, database models, and data/ML scripts.
- **frontend/** – React-based UI skeleton (search + card detail placeholder).
- **data/** – Sample CSVs and raw/processed data.
- **notebooks/** – Exploration, prototyping, and modeling notebooks.

### Backend (FastAPI)

- Entrypoint: `backend/app/main.py`
- Config: `backend/app/core/config.py`
- Database:
  - SQLAlchemy models in `backend/app/db/models.py`
  - Session/engine in `backend/app/db/database.py`
- Scripts:
  - `backend/scripts/ingest_sales.py` – ingest eBay Order earnings CSV into `sales`
  - `backend/scripts/ingest_ebay_api.py` – ingest completed listings from eBay Finding API
  - `backend/scripts/backfill_sets_and_cards.py` – build `sets` and `card_identities` from sales titles; set `sales.card_id` to `set_slug/card_slug` for browse-by-set and stable URLs
  - `backend/scripts/backfill_card_images.py` – fill `card_identities.image_url` from Pokémon TCG API (run after backfill_sets_and_cards to speed up card detail and avoid per-request API calls)
  - `backend/scripts/train_models.py` – (stub) nightly model training
  - `backend/scripts/backfill_identity_map.py` – (stub) identity mapping

#### Running the backend locally

Using Docker (recommended):

```bash
docker compose up --build
```

Then open `http://localhost:8000/docs` for the FastAPI docs.

Without Docker (Python 3.10+):

```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Frontend (React)

The frontend includes:

- **Cards**: Search by name/set (canonical card list like PriceCharting). Card detail shows image (from Pokémon TCG API when available), set + number, prices by grade, raw-by-condition table (with sort), grading upside (condition + per-company cost), market movement chart (toggle raw condition + companies/grades), grade grid, recent sales.
- **Sets**: Browse sets, view cards in set, set analytics (top movers, liquidity, grading targets), set index chart.
- **Targets**: Ranked grading targets with filters (language, set, min sales/week, volatility, upside, grading cost). **Export CSV** to download the table.
- **Market metrics**: Summary, by-grade / by-company, 10 rate.

To run it (after `npm install` in `frontend/`):

```bash
cd frontend
npm install
npm run dev
```

Then open the printed `http://localhost:xxxx` URL in your browser.

### Services & Docker

- `docker-compose.yml` defines:
  - `db`: Postgres database.
  - `backend`: FastAPI app.
  - (Frontend can be run separately for now.)

### Browse by set (PriceCharting-style)

After ingesting sales, run the backfill to enable **Sets** in the UI and stable card URLs:

```bash
cd backend
source venv/bin/activate
python -m scripts.backfill_sets_and_cards
```

Then open the **Sets** tab: search set names, click a set to see its cards, and click a card to open detail (same as Cards search). Card URLs use canonical ids like `set_slug/card_slug`.

Optional: to cache card images and avoid calling the Pokémon TCG API on every card view, run:

```bash
python -m scripts.backfill_card_images
```

This fills `card_identities.image_url` for cards that have `set_name` and `number`. Card detail will use the cached URL when present.

### Next steps

- Add more set name patterns in `app/services/title_parser.py` (KNOWN_SET_SUBSTRINGS) if your titles use different set names.
- **Image cache**: Run `python -m scripts.backfill_card_images` after backfill_sets_and_cards so card detail uses cached `card_identities.image_url` instead of calling the API every time.
- **PSA population data** (later): Ingest population by grade when you have a source (CSV or API) for grading rates.
- Implement time-series cleaning + forecasting in `backend/app/services`.
- Export targets or card detail to CSV.

