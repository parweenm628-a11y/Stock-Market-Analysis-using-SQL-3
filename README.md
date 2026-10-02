# SQL Stock Market Analysis — Streamlit Playground

A single-file Streamlit SQL playground for the stock-market analysis assignment.

## Files

Keep these files in the same folder:

```text
app.py
requirements.txt
README.md
Bajaj Auto.csv
Eicher Motors.csv
Hero Motocorp.csv
Infosys.csv
TCS.csv
TVS Motors.csv
```

The app does **not** merge the CSV files into one CSV. Each CSV remains a separate table:

| CSV | SQLite table |
|---|---|
| Bajaj Auto.csv | `bajaj_auto` |
| Eicher Motors.csv | `eicher_motors` |
| Hero Motocorp.csv | `hero_motocorp` |
| Infosys.csv | `infosys` |
| TCS.csv | `tcs` |
| TVS Motors.csv | `tvs_motors` |

## Run

```bash
pip install -r requirements.txt
streamlit run app.py
```

Then open the Streamlit URL shown in the terminal.

## CSV encoding protection

The app intentionally does **not** assume every CSV is UTF-8.

It tries:

1. UTF-8 with BOM
2. UTF-8
3. Windows-1252 (`cp1252`)
4. Latin-1
5. A final UTF-8 replacement-character fallback

So the common error:

```text
'utf-8' codec can't decode byte 0x93 ...
```

will not normally stop the application.

The reader also normalizes the dates to `YYYY-MM-DD`, matching the SQL playground design, and converts numeric columns safely.

## What is included

- SQL editor
- Run SQL button
- SQLite in-memory database
- Separate stock tables
- CSV upload support
- Automatic local CSV loading
- Query result table
- Download query result as CSV
- Data explorer
- Schema viewer
- Assignment task checklist
- Starter SQL examples
- Window functions for moving averages and golden-cross practice

## Important

The assignment guide uses SQLite for the playground and MySQL for final submission. This app is a **practice playground**, not a replacement for the final MySQL `.sql` submission.

For example:

```sql
-- SQLite playground
SELECT strftime('%Y', date) AS year
FROM tcs;
```

The guide notes that the corresponding MySQL expression is:

```sql
YEAR(date)
```

## Recommended folder

Do not put the CSVs inside the Python file. Keep them as separate files beside `app.py`. You can also upload them from the Streamlit sidebar if you run the app somewhere that does not have the CSVs locally.
