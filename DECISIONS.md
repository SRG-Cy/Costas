# Decisions log

Short notes on why the project is built the way it is. Each one is a talking point.

## Audience and scope
- **Newcomers to Ireland** who do not know local prices, so the app supplies realistic numbers and never asks the user to type in their own rent.
- First persona: **a single adult** (student or early-career worker). Couples, families and childcare are out of scope for now.

## Data
- **A 403 from the CSO API meant "no such table", not "forbidden".** RIQ02 returned 403; RIH02 and RIA02 returned 200. Tested all codes with the same URL pattern to isolate the cause.
- **Raw data stays untouched.** The 94 MB download goes to `data/raw/` (gitignored). `export_reference.py` creates a 255 KB slice in `reference/` that is committed, so the app deploys without the big file.
- **Unpublished rents are NULL, never 0.** The RTB and Daft leave out cells with too few listings. Zero would drag every average down.
- **Filter before aggregating.** An early query averaged 18 years and every bedroom type and put Dublin at ~EUR 1,519 instead of EUR 2,162.
- **Whole homes and rooms come from different sources.** The RTB index covers whole dwellings. Room rents come from the Daft.ie Q1 2026 rental report (page 15 by region, page 32 by city). Every value was checked against the PDF text.
- **Rooms are by market, not county.** Daft publishes Dublin, four cities, and regions. `county_market.csv` maps each county to its market. Galway rest-of-county is mapped to Connacht-Ulster as an assumption (the report label says "ex-Galway").
- **MESL is the baseline for everyday costs.** It already includes food, energy, transport and phone, so the itemised catalogue rows (TV licence, electricity, GoMo...) are shown for reference and NOT added on top (double counting). It is a national, urban, single-adult figure.
- **Every catalogue row has a source, a date and a confidence.** Unsourced numbers are `estimate` with low confidence and are labelled in the app. Missing ones stay `todo`.
- **Listed (asking) rents vs registered rents.** Daft = what a newcomer sees when searching. RTB = registered tenancies. The app labels which is which.

## Product
- **Deterministic numbers, no LLM for prices.** The model never writes a price. (An LLM could later parse free-text answers or explain the result.)
- **Honest about gaps:** deposits, registration fees, health insurance and families are shown as not included, not guessed.

## Open items
- Deposit and arrival costs, public transport fares, health insurance: need sourced figures.
- Roll rents forward with CPI (RTB data ends 2025H2); use the newer Daft Q2 2026 report.
- Urban vs rural MESL split.


## Everyday costs: student vs working professional (2026-10-06)

**Decision:** the essentials figure is now a basket built from the author's three years of living in Galway,
split by student or working professional. The official MESL budget (about 1,244 a month, a settled adult) is kept
only for comparison.

**Why:** MESL describes a permanent household. A newcomer student spends far less (about 476 a month against 1,244).
Showing 1,244 to every newcomer would overstate the cost for the main audience.

**Gaps:** a professional's health insurance uses the MESL insurance share (no figure was given). A whole home uses
Selectra's small-home electricity average and adds broadband at 40 (author: 30 to 45). Gas and heating are
excluded for now (no figure yet).

**Known weaknesses:** the basket is one person's experience in one city (confidence: low), not an official statistic.
Professional transport of 100 assumes a car. Broadband is assumed to be part of shared bills in a shared house.
Gas and heating are not in the basket.
