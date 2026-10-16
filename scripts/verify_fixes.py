
import json
import os
from pathlib import Path

import mysql.connector
from dotenv import load_dotenv
from sql_validator import validate_sql

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env", override=True)

FIXES = {
    10: """
        SELECT payment_id, amount
        FROM payment
        WHERE amount > 10
        ORDER BY amount DESC, payment_id
        LIMIT 10;
    """,
    12: """
        SELECT title, length
        FROM film
        WHERE length > 120
        ORDER BY title
        LIMIT 10;
    """,
}

with open(ROOT / "data" / "questions.json", encoding="utf-8") as f:
    questions = {int(q["id"]): q for q in json.load(f)}

db = mysql.connector.connect(
    host=os.getenv("DB_HOST"),
    port=int(os.getenv("DB_PORT", "3306")),
    database=os.getenv("DB_NAME"),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
    connection_timeout=10,
)

def fetch(sql):
    cursor = db.cursor()
    try:
        cursor.execute(sql)
        return len(cursor.description or []), [
            tuple(str(value) for value in row)
            for row in cursor.fetchall()
        ]
    finally:
        cursor.close()

try:
    for question_id, generated_sql in FIXES.items():
        question = questions[question_id]
        valid, message = validate_sql(generated_sql)

        print(f"\nQ{question_id}: {question['question']}")

        if not valid:
            print(f"BLOCKED: {message}")
            continue

        generated = fetch(generated_sql)
        reference = fetch(question["ground_truth_sql"])

        print("PASS: Results match." if generated == reference
              else "MISMATCH: Results differ.")
finally:
    db.close()
