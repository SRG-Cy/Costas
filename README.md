# Costas

**What will it cost to live in Ireland?** A small, sourced cost-of-living estimator for people moving to Ireland.
Answer a few questions, one per page, and get a monthly estimate plus the one-off cash you need on arrival.
Every number links to its source.

**Live app: https://costas.streamlit.app/**

Built solo for Hacktoberfest 2026.

## What it does

1. **Where:** pick a county (and the city, where the county has one).
2. **What kind of home:** a room in a shared house, or your own place.
3. **About you:** coming to study or to work, plus optional gym and IRP registration (non-EU).
4. **Result:** housing, everyday essentials, total per month, and one-off arrival cash (deposit, first month, IRP fee).

Extras on the result page: a breakdown of everyday costs, rent over time, a county comparison, and a Sources section.

An optional AI helper can fill the form from a plain-English description (you confirm everything before the estimate)
and explain the result in another language. See below.

## Run it

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows (use: source .venv/bin/activate on Mac/Linux)
pip install -r requirements.txt
streamlit run app.py
```

The app only needs the files in `reference/`, which are committed. No database or large download is required.

## How the estimate works

```
monthly total = housing + everyday essentials (+ gym, if chosen)
one-off cash  = deposit (one month's rent) + first month's rent (+ IRP fee, if chosen)
```

| Part | Source |
|---|---|
| Housing, whole home | RTB Rent Index via CSO table RIH02 (latest 2025H2), by county and four cities |
| Housing, room | Daft.ie Rental Report 2026Q1, average advertised room rents |
| Everyday essentials | Estimated typical monthly costs for a student or a working professional (not official statistics) |
| Whole-home electricity | Selectra average bill for a small home |
| Deposit and first month | RTB rules: at most one month's rent each |
| IRP registration fee | 300 euro per adult (DkIT international office page; check the official fee) |
| Comparison figure | Vincentian MESL 2025: minimum budget for a settled single adult, excluding housing |

The everyday-essentials basket is deliberately labelled low confidence. The official MESL budget is shown beside it for
comparison, because it describes a settled household and runs higher than a typical student budget.

## Limits

- Everyday costs are national estimates, not by county. Only rent changes by county.
- Rents are averages; rents for new tenancies are usually higher than the average of existing ones.
- Gas and heating for a whole home are not included yet.
- Not included: visa and permit fees, setup items (SIM, bedding), childcare, couples and families.
- Student accommodation can have different deposit rules.

## Optional AI features

Costas works without AI. If you add a Google AI Studio key, two extras appear:

1. **Describe your situation** on the first page fills the form from plain English, then shows a confirmation page
   listing every choice (marking anything it had to assume) before you see an estimate.
2. **Explain this in plain words** rewrites the result in a language you choose.

The model never produces a number. Costs come from `costs.py`. Answers are checked against the allowed options, and
an explanation is thrown away if it contains any euro figure that was not in the estimate (see `ai.py`).

To enable: create `.streamlit/secrets.toml` containing `GOOGLE_API_KEY = "your-key"` (this file is gitignored),
then run the app.

## Tests

```bash
pytest -q
```

The tests check the calculations against hand-verified values and the AI helpers with a mocked model.

## Refresh the data (optional)

```bash
python explore.py            # downloads the RTB/CSO rent table to data/raw/ (about 94 MB)
python export_reference.py   # writes reference/rent_area.csv
```

## Files

| File | Purpose |
|---|---|
| `app.py` | Streamlit interface (step-by-step flow) |
| `costs.py` | All calculations, no UI, covered by `test_costs.py` |
| `ai.py` | Optional AI helpers with validation of everything the model returns |
| `reference/*.csv` | Sourced data: rents, room rents, county-to-market map, cost catalogue, everyday-costs basket |
| `export_reference.py` | Builds the small rent file from the large CSO download |
| `DECISIONS.md` | Why it is built this way |

Data: CSO and RTB (open data), Daft.ie, Vincentian MESL Research Centre, Selectra, DkIT.
