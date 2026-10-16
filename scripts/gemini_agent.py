
import os
import time

from dotenv import load_dotenv
from google import genai
from google.genai import errors

load_dotenv(override=True)

api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    raise ValueError(
        "GEMINI_API_KEY is missing. Check your local .env file."
    )

client = genai.Client(api_key=api_key)

MODEL_NAME = "gemini-3.5-flash"
MAX_ATTEMPTS = 3

RETRYABLE_ERRORS = {429, 500, 502, 503, 504}


def generate_sql(question: str) -> str:
    """Generate a MySQL SELECT query for the Sakila database."""

    prompt = f"""
You are an expert MySQL assistant working with the Sakila sample database.

Convert the user's natural-language question into one correct MySQL SELECT query.

RULES:
1. Return only the SQL query, without Markdown fences or explanations.
2. Use only tables and columns that exist in the Sakila database.
3. Generate read-only SELECT queries only.
4. Never generate INSERT, UPDATE, DELETE, DROP, ALTER, CREATE,
   TRUNCATE, or other data-modification statements.
5. Select only the columns requested or necessary to answer the question.
6. Never use SELECT * when specific output columns are requested.
7. For customers listed by name, select first_name and last_name
   unless additional columns are requested.
8. Include every explicitly requested output column.
9. Apply all requested filters, sorting, grouping, and row limits.
10. For "first N" or "top N" requests, use LIMIT N.
11. For "largest" or "highest" records, sort the relevant measure
    in descending order.
12. For "first N" records, use a meaningful ORDER BY when the
    question or context specifies the ordering.
13. When sort values can tie, use an appropriate stable tie-breaker
    if specified by the question or database task.
14. Do not invent columns or silently change the requested output.
15. Use valid MySQL syntax.
16. Do not execute the query; only generate it.

EXAMPLES:

Question: List the first 10 customers ordered by last name and first name.
SQL: SELECT first_name, last_name
     FROM customer
     ORDER BY last_name, first_name
     LIMIT 10;

Question: List the first 10 inactive customers ordered by last name and first name.
SQL: SELECT first_name, last_name
     FROM customer
     WHERE active = 0
     ORDER BY last_name, first_name
     LIMIT 10;

Question: How many films are in the database?
SQL: SELECT COUNT(*) FROM film;

Question: List the 10 largest payments greater than 10 dollars.
SQL: SELECT payment_id, amount
     FROM payment
     WHERE amount > 10
     ORDER BY amount DESC, payment_id
     LIMIT 10;

Question: List the first 10 films longer than 120 minutes.
SQL: SELECT title, length
     FROM film
     WHERE length > 120
     ORDER BY title
     LIMIT 10;

User question:
{question}
"""

    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            print(
                f"Gemini request attempt "
                f"{attempt}/{MAX_ATTEMPTS}..."
            )

            response = client.models.generate_content(
                model=MODEL_NAME,
                contents=prompt,
            )

            if not response.text:
                raise ValueError(
                    "Gemini returned an empty response."
                )

            return response.text.strip()

        except errors.APIError as error:
            if error.code not in RETRYABLE_ERRORS:
                print(
                    f"Gemini API error (HTTP {error.code}): "
                    f"{error.message}"
                )
                raise

            if attempt == MAX_ATTEMPTS:
                print(
                    f"Gemini is still unavailable after "
                    f"{MAX_ATTEMPTS} attempts."
                )
                raise

            delay = 2 ** attempt

            print(
                f"Temporary API error (HTTP {error.code}). "
                f"Retrying in {delay} seconds..."
            )

            time.sleep(delay)

    raise RuntimeError("SQL generation failed unexpectedly.")


if __name__ == "__main__":
    test_questions = [
        "List the 10 largest payments greater than 10 dollars.",
        "List the first 10 films longer than 120 minutes.",
    ]

    for question in test_questions:
        print(f"\nQuestion: {question}")

        try:
            sql = generate_sql(question)
            print("\nGenerated SQL:")
            print(sql)

        except errors.APIError:
            print("SQL generation failed. Please try again later.")
            break
