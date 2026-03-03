# PriceCharting-style features: plan

Goal: compile data similar to [PriceCharting](https://www.pricecharting.com/game/pokemon-ascended-heroes/mega-gengar-ex-284): search by card and by set, prices aggregated by grade (all companies), population/grading rates, and grading upside.

## 1. Card and set identity (like PriceCharting URLs)

- **Sets**: e.g. "Pokemon Ascended Heroes" with slug `pokemon-ascended-heroes`. Search/browse by set.
- **Cards**: canonical identity per set + card number + name, e.g. `mega-gengar-ex-284`. URL pattern: `/game/{set_slug}/{card_slug}`.
- **Data model**: `sets` table (set_slug, set_name, game); `card_identities` extended with set_id, card_slug. Sales linked via `card_id` to a canonical card.

## 2. Prices by grade (all companies)

- For each card: show **median price + sale count** for:
  - **Ungraded** (raw)
  - **PSA 10**, **PSA 9**, **PSA 9.5**, …
  - **BGS 10**, **BGS 9.5**, …
  - **CGC**, **TAG**, **SGC**, **ACE** by grade
- Same structure as PriceCharting’s table (e.g. Ungraded | Grade 9 | Grade 9.5 | PSA 10 | …).

## 3. Population / grading rates

- **Population**: from our data we only have *sales*, not total slabs. We show **sale count per (company, grade)** as a proxy for volume.
- **Grading rates**: for this card (or set), what % of graded sales are 10, 9.5, 9, etc., **per company**. So you can see “PSA gives 10 this often for this card” vs “BGS gives 9.5 this often”.

## 4. Grading upside / “worth grading?”

- **Inputs**: raw price (or user’s cost), grading cost (e.g. $25), and our data:
  - Median price per (company, grade) for this card
  - Observed grade distribution (from sales) per company
- **EV(grading)**: e.g. for PSA, EV = Σ P(grade g) × Price(PSA, g) − grading_cost. Use our observed P(g) from this card’s sales (or fallback to a global prior).
- **Upside**: EV − raw_price. “Worth grading?” = upside > threshold (e.g. > 0).
- **Targetable cards**: cards where upside is positive and/or above a chosen minimum; can rank by upside for a “grading targets” list.

## Implementation phases

- **Phase 1 (done in code)**: Card detail API returns `prices_by_grade`, `grade_distribution`, `grading_upside`. Frontend shows PriceCharting-style table and grading upside section. Card identity remains title-based.
- **Phase 2**: Add `sets` table, `card_identities` with set_id and card_slug, backfill from titles. Endpoints: search sets, list cards in set. Frontend: set browser, URLs by set/card slug.
- **Phase 3**: Refine grading upside (better P(g) estimates, multiple companies, cost options) and “targetable for grading” list/API.
