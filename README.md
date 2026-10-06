# Costas

**What will it cost to live in Ireland?** A small, sourced estimator for people moving to Ireland.
Pick a county, a room or your own place, and see a monthly estimate with the source and date behind every number.

Built solo for Hacktoberfest 2026.

## Run it

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows (use: source .venv/bin/activate on Mac/Linux)
pip install -r requirements.txt
streamlit run app.py
```

The app only needs the files in `reference/`, which are committed. No database or download required.

## Refresh the data (optional)

```bash
python explore.py            # downloads the RTB/CSO rent table to data/raw/ (about 94 MB)
python export_reference.py   # writes reference/rent_area.csv
pytest -q                    # checks the calculations against hand-verified values
```

## How the estimate works

`monthly total = housing + everyday essentials`

| Part | Source |
|---|---|
| Housing, whole home | RTB Rent Index via CSO table RIH02 (latest 2025H2), by county and four cities |
| Housing, room | Daft.ie Rental Report 2026Q1, average listed room rents (pages 15 and 32) |
| Everyday essentials | Vincentian MESL 2025: single working-age adult, urban, excluding housing |

## Limits

- Everyday essentials are national, not by county, and describe a settled resident.
- Rents are averages; rents for new tenancies are usually higher than the average of existing ones.
- Not included yet: deposit and setup costs, registration fees, health insurance, childcare, couples and families.
- Items marked *estimate* in `reference/catalogue.csv` have no source yet.

## Files

| File | Purpose |
|---|---|
| `app.py` | Streamlit interface |
| `costs.py` | All calculations (no UI), covered by `test_costs.py` |
| `reference/*.csv` | Sourced data: rents, room rents, county-to-market map, cost catalogue |
| `export_reference.py` | Builds the small rent file from the large CSO download |
| `DECISIONS.md` | Why it is built this way |

Data: CSO and RTB (open data), Daft.ie, Vincentian MESL Research Centre, GoMo, Selectra.

## Optional AI features

Costas works without AI. If you add a Google AI Studio key, two extras appear:
1. **Describe your situation** on the first page fills the form from plain English.
2. **Explain this in plain words** rewrites the result in a language you choose.

The model never produces a number. Costs come from `costs.py`. Answers are checked against the allowed options and
an explanation is thrown away if it contains any euro figure that was not in the estimate (see `ai.py`).
To enable: create `.streamlit/secrets.toml` containing `GOOGLE_API_KEY = "your-key"` (this file is gitignored), then run the app.
