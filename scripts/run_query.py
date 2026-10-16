
import os

import mysql.connector
from dotenv import load_dotenv

from gemini_agent import generate_sql
from sql_validator import validate_sql


load_dotenv(override=True)


def run_query(question: str) -> None:
    """Generate, validate, and execute a read-only SQL query."""

    connection = None
    cursor = None

    try:
        # 1. Generate SQL using Gemini
        print("\n[1/3] Generating SQL with Gemini...")
        sql = generate_sql(question)

        print("\nGenerated SQL:")
        print(sql)

        # 2. Validate SQL before execution
        print("\n[2/3] Validating SQL...")
        is_safe, message = validate_sql(sql)

        print(message)

        if not is_safe:
            print("Query blocked. Nothing was executed.")
            return

        # 3. Connect using the read-only database account
        print("\n[3/3] Connecting to MySQL...")

        required_vars = [
            "DB_HOST",
            "DB_PORT",
            "DB_NAME",
            "DB_USER",
            "DB_PASSWORD",
        ]

        missing_vars = [
            name for name in required_vars
            if not os.getenv(name)
        ]

        if missing_vars:
            print("Missing database configuration:", ", ".join(missing_vars))
            return

        connection = mysql.connector.connect(
            host=os.getenv("DB_HOST"),
            port=int(os.getenv("DB_PORT")),
            database=os.getenv("DB_NAME"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            connection_timeout=10,
        )

        cursor = connection.cursor()
        cursor.execute(sql)

        # Display at most 100 rows in this initial version
        rows = cursor.fetchmany(100)

        if cursor.description:
            columns = [column[0] for column in cursor.description]
            print("\nColumns:", columns)

            if not rows:
                print("No results found.")
            else:
                for row in rows:
                    print(row)

            print(f"\nDisplayed {len(rows)} row(s), maximum 100.")

        else:
            print("The query did not return a result set.")

    except Exception as error:
        print(f"\nSQLProof error: {error}")

    finally:
        if cursor is not None:
            cursor.close()

        if connection is not None and connection.is_connected():
            connection.close()
            print("\nDatabase connection closed.")


if __name__ == "__main__":
    user_question = input("Ask a question about the Sakila database: ").strip()

    if not user_question:
        print("Please enter a question.")
    else:
        run_query(user_question)
