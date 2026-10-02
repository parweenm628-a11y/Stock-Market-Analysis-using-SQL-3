import io
import sqlite3
from pathlib import Path

import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="SQL Stock Market Playground",
    page_icon="📈",
    layout="wide",
)

# -------------------------------------------------------------------
# Configuration
# -------------------------------------------------------------------
EXPECTED_FILES = [
    "Bajaj Auto.csv",
    "Eicher Motors.csv",
    "Hero Motocorp.csv",
    "Infosys.csv",
    "TCS.csv",
    "TVS Motors.csv",
]

TABLE_NAMES = {
    "Bajaj Auto.csv": "bajaj_auto",
    "Eicher Motors.csv": "eicher_motors",
    "Hero Motocorp.csv": "hero_motocorp",
    "Infosys.csv": "infosys",
    "TCS.csv": "tcs",
    "TVS Motors.csv": "tvs_motors",
}

# The original project uses these logical SQL column names.
COLUMN_MAP = {
    "Date": "date",
    "Open Price": "open_price",
    "High Price": "high_price",
    "Low Price": "low_price",
    "Close Price": "close_price",
    "WAP": "wap",
    "No.of Shares": "no_of_shares",
    "No. of Trades": "no_of_trades",
    "Total Turnover (Rs.)": "total_turnover",
    "Deliverable Quantity": "deliverable_qty",
    "% Deli. Qty to Traded Qty": "pct_deli_qty",
    "Spread High-Low": "spread_high_low",
    "Spread Close-Open": "spread_close_open",
}

# -------------------------------------------------------------------
# Robust CSV reader
# This deliberately avoids assuming UTF-8. It fixes the common:
# "'utf-8' codec can't decode byte 0x93..." problem.
# -------------------------------------------------------------------
def read_csv_robust(source):
    if isinstance(source, (str, Path)):
        raw = Path(source).read_bytes()
    else:
        raw = source.getvalue()

    # BOM-aware UTF-8 first, then common Windows encodings.
    encodings = ["utf-8-sig", "utf-8", "cp1252", "latin1"]
    last_error = None

    for encoding in encodings:
        try:
            text = raw.decode(encoding)
            df = pd.read_csv(io.StringIO(text))
            return normalize_dataframe(df)
        except (UnicodeDecodeError, pd.errors.ParserError) as exc:
            last_error = exc

    # Final safety net: never let a bad byte kill the Streamlit app.
    text = raw.decode("utf-8", errors="replace")
    df = pd.read_csv(io.StringIO(text))
    return normalize_dataframe(df)


def normalize_dataframe(df):
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]

    rename = {k: v for k, v in COLUMN_MAP.items() if k in df.columns}
    df.rename(columns=rename, inplace=True)

    if "date" in df.columns:
        # Keep ISO YYYY-MM-DD text so SQLite sorting and strftime work
        # exactly like the student guide.
        parsed = pd.to_datetime(df["date"], dayfirst=True, errors="coerce")
        df["date"] = parsed.dt.strftime("%Y-%m-%d")

    numeric_cols = [
        "open_price", "high_price", "low_price", "close_price", "wap",
        "no_of_shares", "no_of_trades", "total_turnover",
        "deliverable_qty", "pct_deli_qty", "spread_high_low",
        "spread_close_open",
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(
                df[col].astype(str).str.replace(",", "", regex=False).str.strip(),
                errors="coerce",
            )

    return df


def load_uploaded_files(uploaded_files):
    loaded = {}
    for file in uploaded_files or []:
        try:
            df = read_csv_robust(file)
            table = TABLE_NAMES.get(file.name)
            if not table:
                table = (
                    Path(file.name).stem.lower()
                    .replace(" ", "_")
                    .replace("-", "_")
                )
            loaded[table] = df
        except Exception as exc:
            st.error(f"Could not read **{file.name}**: {exc}")
    return loaded


def load_local_files():
    loaded = {}
    for name in EXPECTED_FILES:
        path = Path(name)
        if path.exists():
            try:
                loaded[TABLE_NAMES[name]] = read_csv_robust(path)
            except Exception as exc:
                st.warning(f"Could not load {name}: {exc}")
    return loaded


def build_database(tables):
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    for table, df in tables.items():
        df.to_sql(table, conn, if_exists="replace", index=False)
    return conn


def schema_text(tables):
    blocks = []
    for table, df in tables.items():
        cols = ", ".join(f"{c} {str(df[c].dtype)}" for c in df.columns)
        blocks.append(f"{table} ({cols})")
    return "\n".join(blocks)


def example_queries():
    return {
        "1. History of Bajaj": """SELECT COUNT(*) AS trading_days,
       MIN(date) AS first_day,
       MAX(date) AS last_day
FROM bajaj_auto;""",
        "2. Eicher top 5 closes": """SELECT date, close_price
FROM eicher_motors
ORDER BY close_price DESC
LIMIT 5;""",
        "3. TCS average by year": """SELECT strftime('%Y', date) AS year,
       ROUND(AVG(close_price), 2) AS avg_close
FROM tcs
GROUP BY year
ORDER BY year;""",
        "4. Find NULL deliverables": """SELECT 'bajaj_auto' AS stock, date
FROM bajaj_auto
WHERE deliverable_qty IS NULL
UNION ALL
SELECT 'eicher_motors', date
FROM eicher_motors
WHERE deliverable_qty IS NULL
UNION ALL
SELECT 'hero_motocorp', date
FROM hero_motocorp
WHERE deliverable_qty IS NULL
UNION ALL
SELECT 'infosys', date
FROM infosys
WHERE deliverable_qty IS NULL
UNION ALL
SELECT 'tcs', date
FROM tcs
WHERE deliverable_qty IS NULL
UNION ALL
SELECT 'tvs_motors', date
FROM tvs_motors
WHERE deliverable_qty IS NULL;""",
        "5. 20-day moving average": """WITH x AS (
    SELECT date, close_price,
           ROW_NUMBER() OVER (ORDER BY date) AS rn,
           AVG(close_price) OVER (
               ORDER BY date
               ROWS BETWEEN 19 PRECEDING AND CURRENT ROW
           ) AS raw_ma20
    FROM bajaj_auto
)
SELECT date, close_price,
       CASE WHEN rn >= 20 THEN ROUND(raw_ma20, 2) END AS ma20
FROM x
ORDER BY date;""",
        "6. Master table preview": """SELECT b.date,
       b.close_price AS bajaj,
       t.close_price AS tcs,
       tv.close_price AS tvs,
       i.close_price AS infosys,
       e.close_price AS eicher,
       h.close_price AS hero
FROM bajaj_auto b
JOIN tcs t ON t.date = b.date
JOIN tvs_motors tv ON tv.date = b.date
JOIN infosys i ON i.date = b.date
JOIN eicher_motors e ON e.date = b.date
JOIN hero_motocorp h ON h.date = b.date
ORDER BY b.date
LIMIT 20;""",
        "7. Golden cross example": """WITH x AS (
    SELECT date, close_price,
           AVG(close_price) OVER (
               ORDER BY date
               ROWS BETWEEN 19 PRECEDING AND CURRENT ROW
           ) AS ma20,
           AVG(close_price) OVER (
               ORDER BY date
               ROWS BETWEEN 49 PRECEDING AND CURRENT ROW
           ) AS ma50
    FROM bajaj_auto
),
y AS (
    SELECT *,
           LAG(ma20) OVER (ORDER BY date) AS prev_ma20,
           LAG(ma50) OVER (ORDER BY date) AS prev_ma50
    FROM x
)
SELECT date, close_price,
       CASE
         WHEN ma20 IS NULL OR ma50 IS NULL
              OR prev_ma20 IS NULL OR prev_ma50 IS NULL THEN 'Hold'
         WHEN ma20 > ma50 AND prev_ma20 <= prev_ma50 THEN 'Buy'
         WHEN ma20 < ma50 AND prev_ma20 >= prev_ma50 THEN 'Sell'
         ELSE 'Hold'
       END AS signal
FROM y
ORDER BY date;""",
    }


# -------------------------------------------------------------------
# UI
# -------------------------------------------------------------------
st.title("📈 SQL Stock Market Analysis — Playground")
st.caption(
    "SQLite-powered Streamlit playground for the six-stock SQL assignment. "
    "Run queries, inspect tables, and practise the moving-average / golden-cross tasks."
)

with st.sidebar:
    st.header("1. Load data")
    uploaded = st.file_uploader(
        "Upload CSV files",
        type=["csv"],
        accept_multiple_files=True,
        help="You can upload the six CSVs separately. The app handles UTF-8, UTF-8 BOM, Windows-1252 and Latin-1.",
    )

    uploaded_tables = load_uploaded_files(uploaded)
    local_tables = load_local_files()

    # Uploaded files take priority over local files with the same table.
    tables = {**local_tables, **uploaded_tables}

    st.success(f"{len(tables)} table(s) loaded")

    st.header("2. Tables")
    if tables:
        for table, df in tables.items():
            st.write(f"**{table}** — {len(df):,} rows")
    else:
        st.info("Upload the CSVs to start.")

    st.header("3. SQL examples")
    examples = example_queries()
    selected_example = st.selectbox("Choose an example", list(examples.keys()))

if not tables:
    st.markdown(
        """
        ### Start here
        Upload one or more of these files:

        - `Bajaj Auto.csv`
        - `Eicher Motors.csv`
        - `Hero Motocorp.csv`
        - `Infosys.csv`
        - `TCS.csv`
        - `TVS Motors.csv`

        The data is loaded into SQLite using the table names from the assignment.
        """
    )
    st.stop()

conn = build_database(tables)

tab_sql, tab_data, tab_schema, tab_tasks = st.tabs(
    ["🧑‍💻 SQL Playground", "📊 Data Explorer", "🗂️ Schema", "🎯 Assignment Tasks"]
)

with tab_sql:
    left, right = st.columns([3, 1])

    with left:
        default_sql = examples[selected_example]
        query = st.text_area(
            "SQL query",
            value=default_sql,
            height=360,
            key="sql_editor",
            help="SQLite syntax is used in this playground. The assignment guide explains SQLite vs MySQL differences.",
        )

    with right:
        st.markdown("#### Quick tips")
        st.write("• Use `strftime('%Y', date)` for year.")
        st.write("• Use `IS NULL`, not `= NULL`.")
        st.write("• Window functions are supported.")
        st.write("• Use `ROWS BETWEEN 19 PRECEDING AND CURRENT ROW` for 20 rows.")
        st.write("• For a crossover, compare today's averages with `LAG()` values.")

        if st.button("↩️ Load selected example", use_container_width=True):
            st.session_state["sql_editor"] = default_sql
            st.rerun()

    run = st.button("▶ Run SQL", type="primary", use_container_width=True)

    if run:
        try:
            statements = [s.strip() for s in query.split(";") if s.strip()]
            if not statements:
                st.warning("Please enter a SQL query.")
            else:
                result = None
                for statement in statements:
                    cursor = conn.execute(statement)
                    if cursor.description:
                        result = cursor.fetchall()
                        columns = [d[0] for d in cursor.description]
                if result is not None:
                    result_df = pd.DataFrame(result, columns=columns)
                    st.success(f"Query executed successfully — {len(result_df):,} row(s).")
                    st.dataframe(result_df, use_container_width=True, height=430)
                    st.download_button(
                        "⬇️ Download result as CSV",
                        result_df.to_csv(index=False).encode("utf-8"),
                        file_name="sql_result.csv",
                        mime="text/csv",
                    )
                else:
                    st.success("SQL executed successfully.")
        except Exception as exc:
            st.error("SQL error")
            st.code(str(exc))

with tab_data:
    stock = st.selectbox("Select table", list(tables.keys()))
    df = tables[stock]

    c1, c2, c3 = st.columns(3)
    c1.metric("Rows", f"{len(df):,}")
    c2.metric("Columns", f"{len(df.columns):,}")
    c3.metric("Missing values", f"{int(df.isna().sum().sum()):,}")

    st.dataframe(df, use_container_width=True, height=500)

with tab_schema:
    st.subheader("SQLite schema")
    st.code(schema_text(tables), language="sql")
    st.info(
        "Logical table/column names follow the student guide: "
        "for example `bajaj_auto`, `close_price`, `deliverable_qty`."
    )

with tab_tasks:
    st.subheader("Practice path")
    tasks = [
        ("1", "Get to know the data", "COUNT, MIN, MAX"),
        ("2", "Eicher's five best closes", "ORDER BY ... DESC, LIMIT"),
        ("3", "TCS, year by year", "strftime, GROUP BY, AVG, ROUND"),
        ("4", "Find the holes", "IS NULL, UNION ALL"),
        ("5", "Moving averages", "AVG() OVER, ROWS BETWEEN, ROW_NUMBER, CASE"),
        ("6", "Master table", "JOIN ... ON"),
        ("7", "Golden cross signals", "LAG, CTE, CASE"),
        ("8", "How often did it trigger?", "GROUP BY, COUNT"),
        ("9", "Signal on a given day", "WHERE"),
        ("10", "All six stocks in one query", "PARTITION BY, CTEs, ROW_NUMBER"),
        ("11", "Who went up?", "CTEs, first/last close, arithmetic"),
        ("12", "The data trap", "LAG, PARTITION BY, ROW_NUMBER"),
        ("13", "Fix it", "CASE, conditional aggregation"),
    ]
    for number, title, skills in tasks:
        st.markdown(f"**{number}. {title}** — `{skills}`")

    st.divider()
    st.markdown(
        "The playground is intentionally SQLite-based, matching the practice "
        "environment described in the student guide. For final MySQL submission, "
        "adapt SQLite-specific functions such as `strftime()` as described in the guide."
    )
