
import json
import os
from collections import Counter
from pathlib import Path

import mysql.connector
from dotenv import load_dotenv

load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATASET_PATH = PROJECT_ROOT / "data" / "questions.json"


def main():
    # 1. Load and validate the JSON dataset
    with open(DATASET_PATH, "r", encoding="utf-8") as file:
        questions = json.load(file)

    print(f"Loaded {len(questions)} questions.")

    expected_ids = list(range(1, 41))
    actual_ids = [q.get("id") for q in questions]

    if len(questions) != 40:
        raise ValueError(f"Expected 40 questions, found {len(questions)}.")

    if sorted(actual_ids) != expected_ids:
        raise ValueError("Question IDs must be unique and range from 1 to 40.")

    counts = Counter(q.get("difficulty") for q in questions)
    expected_counts = {"easy": 15, "medium": 15, "tricky": 10}

    if dict(counts) != expected_counts:
        raise ValueError(f"Unexpected difficulty counts: {dict(counts)}")

    for question in questions:
        if not question.get("question") or not question.get("ground_truth_sql"):
            raise ValueError(f"Question {question.get('id')} is missing required fields.")

    print("Dataset structure: PASS")
    print(f"Difficulty counts: {dict(counts)}")

    # 2. Connect using the read-only account and test every reference query
    connection = None
    passed = []
    failed = []

    try:
        connection = mysql.connector.connect(
            host=os.getenv("DB_HOST"),
            port=int(os.getenv("DB_PORT", "3306")),
            database=os.getenv("DB_NAME"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            connection_timeout=10,
        )

        for question in questions:
            cursor = connection.cursor()
            try:
                cursor.execute(question["ground_truth_sql"])
                cursor.fetchall()
                passed.append(question["id"])
                print(f"Q{question['id']:02d}: PASS")
            except mysql.connector.Error as error:
                failed.append((question["id"], str(error)))
                print(f"Q{question['id']:02d}: FAIL — {error}")
            finally:
                cursor.close()

    finally:
        if connection is not None and connection.is_connected():
            connection.close()

    print("\n--- Summary ---")
    print(f"Total: {len(questions)}")
    print(f"Passed: {len(passed)}")
    print(f"Failed: {len(failed)}")

    if failed:
        print("\nQueries to fix:")
        for question_id, error in failed:
            print(f"Q{question_id}: {error}")
        raise SystemExit(1)

    print("All dataset queries executed successfully.")


if __name__ == "__main__":
    main()
