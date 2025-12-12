# MatchEng

A small Flask web app to de-duplicate B2B retail records.

## What it does

- Upload a CSV containing:
  - `Source Type`
  - `Source ID`
  - `Company Name`
  - `Address`
  - `Phone Number`
- For each row, it searches a persistent SQLite dataset (`data/matches.db`) for a match.
- If a match is found, it reuses the existing `DeDup ID`; otherwise it generates a new one.
- It returns an annotated CSV with `DeDup ID`, match status, score, and matched-to record.

## Run locally

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
python3 app.py
```

Then open `http://localhost:5000`.

## Notes

- Persistence is via SQLite at `data/matches.db`.
- Matching uses fuzzy similarity on normalized company name + address, with phone (when present) acting as a strong boost.
