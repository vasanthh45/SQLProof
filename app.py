
import os
import sys
import time
from pathlib import Path

import mysql.connector
import pandas as pd
import streamlit as st
from dotenv import load_dotenv

# --------------------------------------------------
# Configuration
# --------------------------------------------------

ROOT = Path(__file__).resolve().parent
SCRIPTS_DIR = ROOT / "scripts"

if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from gemini_agent import generate_sql
from sql_validator import validate_sql

load_dotenv(ROOT / ".env", override=True)

st.set_page_config(
    page_title="SQLProof | AI SQL Workspace",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --------------------------------------------------
# Professional UI styling
# --------------------------------------------------

st.markdown(
    """
    <style>
    .stApp {
        background: #0b1020;
        color: #e8edf8;
    }

    [data-testid="stSidebar"] {
        background: #11182a;
        border-right: 1px solid #263149;
    }

    .block-container {
        max-width: 1450px;
        padding-top: 1.7rem;
        padding-bottom: 2rem;
    }

    .hero {
        padding: 1.5rem 1.7rem;
        border: 1px solid #293650;
        border-radius: 18px;
        background: linear-gradient(120deg, #182541, #111827);
        margin-bottom: 1.2rem;
    }

    .eyebrow {
        color: #93aaff;
        font-size: .75rem;
        font-weight: 700;
        letter-spacing: .15em;
        text-transform: uppercase;
    }

    .hero h1 {
        color: #f4f7ff;
        font-size: 2.35rem;
        margin: .4rem 0;
        letter-spacing: -.035em;
    }

    .hero p {
        color: #b8c4da;
        margin: 0;
    }

    .section-title {
        font-size: 1.15rem;
        font-weight: 650;
        margin: .8rem 0 .4rem 0;
    }

    div[data-testid="stMetric"] {
        background: #121b2e;
        border: 1px solid #28354c;
        padding: .8rem 1rem;
        border-radius: 12px;
    }

    div[data-testid="stMetricLabel"] {
        color: #aab8d0;
    }

    div[data-testid="stTextArea"] textarea {
        background: #111a2c;
        color: #f2f5ff;
        border: 1px solid #34425d;
        border-radius: 12px;
    }

    div.stButton > button[kind="primary"] {
        background: #536dfe;
        color: white;
        border: 1px solid #6c83ff;
        border-radius: 10px;
        min-height: 2.9rem;
        font-weight: 650;
    }

    div.stButton > button[kind="primary"]:hover {
        background: #4058e8;
        border-color: #91a2ff;
    }

    div[data-testid="stCode"] {
        border: 1px solid #293750;
        border-radius: 12px;
    }

    .footer {
        color: #8290a8;
        text-align: center;
        font-size: .82rem;
        padding-top: 1rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# --------------------------------------------------
# Helpers
# --------------------------------------------------

SAMPLE_QUESTIONS = [
    "How many films are in the database?",
    "List the 10 longest films.",
    "Which customers have made the most rentals?",
]


def select_sample(question):
    st.session_state["question"] = question


def get_database_connection():
    required = [
        "DB_HOST",
        "DB_NAME",
        "DB_USER",
        "DB_PASSWORD",
    ]

    missing = [key for key in required if not os.getenv(key)]

    if missing:
        raise ValueError(
            "Missing database settings: " + ", ".join(missing)
        )

    return mysql.connector.connect(
        host=os.getenv("DB_HOST"),
        port=int(os.getenv("DB_PORT", "3306")),
        database=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        connection_timeout=10,
    )


def show_stage(number, title, status):
    st.markdown(
        f"**{number}. {title}** · {status}"
    )


# --------------------------------------------------
# Sidebar
# --------------------------------------------------

with st.sidebar:
    st.markdown("## 🛡️ SQLProof")
    st.caption("AI-powered database workspace")
    st.divider()

    st.markdown("### Query pipeline")
    st.markdown(
        """
        **01 · Ask**

        Describe what you need in plain English.

        **02 · Generate**

        Gemini translates your question into SQL.

        **03 · Validate**

        SQLGlot checks the generated query.

        **04 · Execute**

        MySQL runs the approved query.

        **05 · Explore**

        Inspect and export the results.
        """
    )

    st.divider()
    st.markdown("### Technology")
    st.caption("Python · Gemini API")
    st.caption("SQLGlot · MySQL · Streamlit")

    st.divider()
    st.markdown("### Database")
    st.code(os.getenv("DB_NAME", "Sakila"), language=None)
    st.caption("Results are limited to 100 displayed rows.")
    st.caption("Use a dedicated read-only MySQL account.")

# --------------------------------------------------
# Header
# --------------------------------------------------

st.markdown(
    """
    <div class="hero">
        <div class="eyebrow">Natural language · SQL · Insights</div>
        <h1>Ask your database.</h1>
        <p>
            Turn everyday questions into validated SQL and explore
            your MySQL data in one workspace.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

# --------------------------------------------------
# Input area
# --------------------------------------------------

st.markdown(
    '<div class="section-title">What would you like to know?</div>',
    unsafe_allow_html=True,
)

st.session_state.setdefault("question", "")

sample_cols = st.columns(3)

for index, sample in enumerate(SAMPLE_QUESTIONS):
    with sample_cols[index]:
        st.button(
            sample,
            key=f"sample_{index}",
            use_container_width=True,
            on_click=select_sample,
            args=(sample,),
        )

question = st.text_area(
    "Your question",
    key="question",
    placeholder="Example: Show the 10 customers who rented the most films.",
    height=105,
    label_visibility="collapsed",
)

generate_clicked = st.button(
    "✦  Generate SQL and run query",
    type="primary",
    use_container_width=True,
)

# --------------------------------------------------
# Query execution pipeline
# --------------------------------------------------

if generate_clicked:
    if not question.strip():
        st.warning("Enter a question or select a sample question.")

    else:
        connection = None
        cursor = None
        started = time.perf_counter()

        st.divider()
        st.markdown("## Query workspace")

        try:
            # Stage 1: Generate SQL
            show_stage("1", "SQL generation", "In progress")

            with st.spinner("Generating SQL with Gemini..."):
                sql = generate_sql(question.strip())

            st.success("SQL generation completed.")

            with st.expander("View generated SQL", expanded=True):
                st.code(sql, language="sql")

                st.download_button(
                    "Download SQL",
                    data=sql,
                    file_name="sqlproof_query.sql",
                    mime="text/sql",
                    key="download_sql",
                )

            # Stage 2: Validate SQL
            show_stage("2", "Safety validation", "Checking")

            is_safe, validation_message = validate_sql(sql)

            if not is_safe:
                st.error(f"Query blocked: {validation_message}")
                st.stop()

            st.success(f"Validation passed: {validation_message}")

            # Stage 3: Execute SQL
            show_stage("3", "Database execution", "Connecting")

            with st.spinner("Executing query on MySQL..."):
                connection = get_database_connection()
                cursor = connection.cursor()
                cursor.execute(sql)

                # Measure elapsed time through query execution.
                execution_seconds = time.perf_counter() - started

                if cursor.description is None:
                    st.info("The query returned no result set.")

                else:
                    columns = [
                        description[0]
                        for description in cursor.description
                    ]

                    # Fetch one extra row to detect truncation.
                    fetched_rows = cursor.fetchmany(101)
                    truncated = len(fetched_rows) > 100
                    rows = fetched_rows[:100]

            st.success("Query execution completed.")

            if cursor.description is not None:
                dataframe = pd.DataFrame(rows, columns=columns)

                st.markdown("### Query results")

                metric_cols = st.columns(3)

                metric_cols[0].metric("Rows displayed", len(dataframe))
                metric_cols[1].metric("Columns", len(columns))
                metric_cols[2].metric(
                    "Elapsed time",
                    f"{execution_seconds:.2f} s",
                )

                if dataframe.empty:
                    st.info("The query ran successfully but returned no rows.")

                else:
                    # Avoid a large empty table for small result sets.
                    table_height = min(
                        500,
                        max(100, 38 + len(dataframe) * 35),
                    )

                    st.dataframe(
                        dataframe,
                        use_container_width=True,
                        hide_index=True,
                        height=table_height,
                    )

                    st.download_button(
                        "Download results as CSV",
                        data=dataframe.to_csv(index=False).encode("utf-8"),
                        file_name="sqlproof_results.csv",
                        mime="text/csv",
                        key="download_csv",
                    )

                if truncated:
                    st.caption(
                        "Showing the first 100 rows. "
                        "Additional rows were not displayed."
                    )
                else:
                    st.caption(
                        f"All {len(dataframe)} returned row(s) are displayed."
                    )

        except Exception as error:
            st.error(
                f"Unable to complete the query: "
                f"{type(error).__name__}: {error}"
            )

        finally:
            if cursor is not None:
                cursor.close()

            if connection is not None:
                if connection.is_connected():
                    connection.close()

# --------------------------------------------------
# Footer
# --------------------------------------------------

st.divider()

st.markdown(
    """
    <div class="footer">
        SQLProof · Gemini + SQLGlot + MySQL + Streamlit
        <br/>
        Generated queries are validated before execution.
    </div>
    """,
    unsafe_allow_html=True,
)
