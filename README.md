# SQLProof — Safety-Aware Natural Language-to-SQL System

SQLProof is an AI-powered application that converts natural-language questions into SQL queries, validates the generated SQL, executes approved queries against a MySQL database, and presents the results through a Streamlit interface.

The project explores how generative AI can make databases easier to query while adding safeguards around AI-generated SQL.

## Features

- **Natural-language-to-SQL:** Generate SQL queries from questions using the Google Gemini API.
- **SQL validation:** Use SQLGlot to parse and validate generated SQL before execution.
- **Read-only database access:** Use a dedicated MySQL account with SELECT-only permissions as an additional safety layer.
- **Query execution:** Execute approved queries against the Sakila sample database.
- **Interactive interface:** Explore generated SQL, validation status, and query results in Streamlit.
- **Data export:** Download generated SQL and query results as CSV.
- **Benchmark evaluation:** Compare generated query results against reference SQL using a 40-question dataset.
- **Automated tests:** Test SQL validation and result-comparison behavior using pytest.

## Architecture

1. The user submits a question in natural language.
2. Gemini generates a SQL query.
3. SQLGlot-based validation checks the query.
4. Invalid queries are rejected before database execution.
5. Approved queries are executed against MySQL using the configured database account.
6. The application displays the results and allows supported downloads.

## Technology Stack

- Python
- Google Gemini API
- SQLGlot
- MySQL
- MySQL Connector/Python
- Streamlit
- Pandas
- python-dotenv
- pytest

## Project Structure

```text
SQLProof/
├── app.py
├── scripts/
│   ├── gemini_agent.py
│   ├── sql_validator.py
│   ├── run_query.py
│   ├── evaluate.py
│   ├── check_dataset.py
│   └── test_connection.py
├── tests/
│   ├── test_sql_validator.py
│   └── test_evaluate.py
├── data/
│   └── questions.json
├── results/
├── .env.example
├── .gitignore
└── README.md
```

This structure describes the main project files; optional helper scripts and generated evaluation files may also exist.

## Requirements

- Python 3.14.3 was used during development.
- MySQL Server with the Sakila sample database.
- A Google Gemini API key.
- A Python virtual environment.

## Installation

Clone the repository:

```bash
git clone YOUR_GITHUB_REPOSITORY_URL
cd SQLProof
```

Create and activate a virtual environment on Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install the dependencies used by the project:

```powershell
python -m pip install streamlit pandas mysql-connector-python python-dotenv google-genai sqlglot pytest
```

Configure the environment variables described in `.env.example` by creating a local `.env` file.

Do not commit `.env` or share real API keys or database passwords.

## Configuration

Configure the following variables in your local `.env` file:

```dotenv
GEMINI_API_KEY=your_gemini_api_key
DB_HOST=localhost
DB_PORT=3306
DB_NAME=sakila
DB_USER=your_read_only_mysql_user
DB_PASSWORD=your_local_database_password
```

Use a dedicated MySQL account with only the permissions required by the application.

## Run the Application

Start Streamlit from the project root:

```powershell
streamlit run app.py
```

Enter a natural-language question, generate SQL, review the validation status, and inspect the query results.

## Testing

Run the automated test suite:

```powershell
python -m pytest -v
```

During development, the existing test suite completed successfully with **18 passing tests**.

The tests cover SQL validation and result-comparison behavior. Rerun the suite against the final repository before publishing.

## Evaluation

SQLProof includes a benchmark dataset of 40 natural-language questions with reference SQL queries.

The evaluation framework executes generated and reference SQL and compares their results.

At the latest recorded checkpoint:

- Dataset size: 40 questions.
- Evaluation records: 13.
- Passing records: 12.
- API quota errors: 1.
- Questions without evaluation records: 27.

Two previously mismatched queries (Q10 and Q12) were corrected and independently verified against their reference SQL results.

**The 40-question evaluation is incomplete.** The Gemini free-tier API quota was exhausted during a subsequent evaluation run. The figures above describe the saved evaluation checkpoint, not a completed benchmark or a 100% success rate across all 40 questions.

## Safety Considerations

SQLProof validates generated SQL before execution and uses a read-only database account as an additional protection.

These measures reduce risk but do not make the application a complete production security solution. Generated SQL can still be incorrect, and validation alone is not a substitute for database permissions, resource limits, careful error handling, and security testing.

Use a non-production database for experiments.

## Current Limitations

- Generated SQL may be incorrect or fail to answer a question as intended.
- The full 40-question evaluation has not been completed.
- Gemini API availability and quota limits can interrupt query generation.
- The current interface displays at most 100 result rows.
- The application has not been established as a production-ready enterprise system.

## Future Improvements

- Complete and expand the benchmark evaluation.
- Improve error categorization and query-generation reliability.
- Add broader integration and security tests.
- Explore deployment with appropriate authentication and operational controls.

## License

Choose and add an appropriate open-source license before distributing the project if you intend to permit reuse.
