# Grading buckets for metrics

Sales are stored with `grade_company` (PSA, BGS, CGC, SGC, TAG, ACE) and `grade_value` (10, 9.5, 9, …). Raw cards have `grade_company = NULL` and `grade_value = NULL`.

## Bucketing

- **By grade (all companies)**  
  All 10s: `WHERE grade_value >= 9.99`  
  All 9s: `WHERE grade_value >= 8.99 AND grade_value < 9.99`  
  Or exact: `WHERE grade_value = 10`, `WHERE grade_value = 9.5`, etc.

- **By company (all grades)**  
  All PSA: `WHERE grade_company = 'PSA'`  
  All BGS: `WHERE grade_company = 'BGS'`

- **By company + grade**  
  PSA 10: `WHERE grade_company = 'PSA' AND grade_value >= 9.99`  
  BGS 9.5: `WHERE grade_company = 'BGS' AND grade_value >= 9.49 AND grade_value < 9.99`

## Example metrics

- **Overall 10 rate**: count(sales where grade_value >= 9.99) / count(sales where grade_company IS NOT NULL)
- **10 rate per company**: same numerator, denominator filtered by `grade_company = 'PSA'` (then BGS, etc.)
- **Prices by company–grade**: `AVG(total_price_usd)` grouped by `(grade_company, grade_value)`

## Language

Filter by `language`: `en`, `jp`, or `other`. Only en/jp are explicitly detected from titles; others are `other`.
