
import json
import os
import shutil
import time
from pathlib import Path

import mysql.connector
from dotenv import load_dotenv

from gemini_agent import generate_sql
from sql_validator import validate_sql


# --------------------------------------------------
# Configuration
# --------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATASET_PATH = PROJECT_ROOT / "data" / "questions.json"
RESULTS_DIR = PROJECT_ROOT / "results"
RESULTS_PATH = RESULTS_DIR / "evaluation_results.json"
BACKUP_PATH = RESULTS_DIR / "evaluation_results_previous.json"

BATCH_SIZE = 3

load_dotenv(PROJECT_ROOT / ".env", override=True)


# --------------------------------------------------
# Load questions and previous results
# --------------------------------------------------

def load_questions():
    with open(DATASET_PATH, "r", encoding="utf-8") as file:
        questions = json.load(file)

    if not isinstance(questions, list):
        raise ValueError("Dataset must be a JSON list.")

    return questions


def load_existing_records():
    if not RESULTS_PATH.exists():
        return {}

    with open(RESULTS_PATH, "r", encoding="utf-8") as file:
        data = json.load(file)

    return {
        str(record["id"]): record
        for record in data.get("records", [])
    }


def backup_previous_results():
    if RESULTS_PATH.exists():
        shutil.copy2(RESULTS_PATH, BACKUP_PATH)
        print("Previous results backed up.")


# --------------------------------------------------
# Database
# --------------------------------------------------

def connect_to_database():
    required = ["DB_HOST", "DB_NAME", "DB_USER", "DB_PASSWORD"]
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


def get_query_result(connection, sql):
    cursor = connection.cursor()

    try:
        cursor.execute(sql)

        if cursor.description is None:
            return None

        columns = [column[0] for column in cursor.description]
        rows = cursor.fetchall()

        return columns, rows

    finally:
        cursor.close()


# --------------------------------------------------
# Result comparison
# --------------------------------------------------

def normalize_result(result, preserve_order=False):
    if result is None:
        return None

    columns, rows = result

    normalized_rows = [
        tuple(str(value) for value in row)
        for row in rows
    ]

    if not preserve_order:
        normalized_rows.sort(key=repr)

    return len(columns), tuple(normalized_rows)


# --------------------------------------------------
# Save merged results
# --------------------------------------------------

def save_results(records, total_dataset_questions, partial):
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    ordered_records = sorted(
        records.values(),
        key=lambda record: int(record["id"]),
    )

    passed = sum(r["status"] == "pass" for r in ordered_records)
    blocked = sum(r["status"] == "blocked" for r in ordered_records)
    mismatched = sum(r["status"] == "mismatch" for r in ordered_records)
    errors = sum(r["status"] == "error" for r in ordered_records)

    evaluated = len(ordered_records)

    summary = {
        "dataset_questions": total_dataset_questions,
        "evaluated_questions": evaluated,
        "remaining_questions": total_dataset_questions - evaluated,
        "passed": passed,
        "blocked": blocked,
        "mismatched": mismatched,
        "errors": errors,
        "partial": partial,
        "result_match_rate": round(passed / evaluated, 4) if evaluated else 0,
    }

    with open(RESULTS_PATH, "w", encoding="utf-8") as file:
        json.dump(
            {"summary": summary, "records": ordered_records},
            file,
            indent=4,
            ensure_ascii=False,
        )


# --------------------------------------------------
# Evaluation
# --------------------------------------------------

def main():
    questions = load_questions()
    existing = load_existing_records()

    # Only select questions that do not already have a result.
    pending = [
        item for item in questions
        if str(item["id"]) not in existing
    ][:BATCH_SIZE]

    if not pending:
        print("All dataset questions already have evaluation records.")
        print("No new Gemini requests were made.")
        return

    print(f"Dataset contains {len(questions)} questions.")
    print(f"Previously evaluated: {len(existing)}")
    print(f"New questions this batch: {len(pending)}")

    backup_previous_results()

    connection = None
    records = dict(existing)
    stopped_early = False

    try:
        connection = connect_to_database()
        print("Database connection successful.\n")

        for index, item in enumerate(pending, start=1):
            question_id = item["id"]
            question = item["question"]
            reference_sql = item["ground_truth_sql"]

            record = {
                "id": question_id,
                "difficulty": item["difficulty"],
                "question": question,
                "generated_sql": None,
                "status": "error",
                "result_match": False,
                "error": None,
            }

            print(
                f"[{index}/{len(pending)}] "
                f"Q{question_id}: {question}"
            )

            try:
                generated_sql = generate_sql(question)
                record["generated_sql"] = generated_sql

                is_valid, message = validate_sql(generated_sql)

                if not is_valid:
                    record["status"] = "blocked"
                    record["error"] = message
                    print(f"  BLOCKED: {message}")

                else:
                    preserve_order = (
                        "ORDER BY" in reference_sql.upper()
                    )

                    generated_result = get_query_result(
                        connection, generated_sql
                    )
                    reference_result = get_query_result(
                        connection, reference_sql
                    )

                    matches = (
                        normalize_result(
                            generated_result, preserve_order
                        )
                        == normalize_result(
                            reference_result, preserve_order
                        )
                    )

                    record["result_match"] = matches
                    record["status"] = (
                        "pass" if matches else "mismatch"
                    )

                    print(
                        "  PASS: Results match."
                        if matches
                        else "  MISMATCH: Results differ."
                    )

            except Exception as error:
                message = str(error)
                lower_message = message.lower()

                record["status"] = "error"
                record["error"] = (
                    f"{type(error).__name__}: {message}"
                )

                if (
                    "resource_exhausted" in lower_message
                    or "quota" in lower_message
                    or "429" in lower_message
                ):
                    record["error_category"] = "api_quota"
                    records[str(question_id)] = record
                    stopped_early = True

                    print("  API quota error. Stopping this batch.")
                elif (
                    "503" in message
                    or "service_unavailable" in lower_message
                ):
                    record["error_category"] = "api_unavailable"
                    print(f"  API unavailable: {message}")
                else:
                    record["error_category"] = "other"
                    print(f"  ERROR: {message}")

            records[str(question_id)] = record

            # Save accumulated progress after every question.
            save_results(
                records, len(questions), partial=True
            )

            if stopped_early:
                break

            if index < len(pending):
                time.sleep(1)

    except Exception as error:
        print(
            f"Evaluation stopped: {type(error).__name__}: {error}"
        )
        save_results(records, len(questions), partial=True)
        return

    finally:
        if connection is not None and connection.is_connected():
            connection.close()

    save_results(
        records,
        len(questions),
        partial=(stopped_early or len(records) < len(questions)),
    )

    with open(RESULTS_PATH, "r", encoding="utf-8") as file:
        summary = json.load(file)["summary"]

    print("\n" + "=" * 45)
    print("SQLPROOF EVALUATION SUMMARY")
    print("=" * 45)
    print(f"Dataset questions : {summary['dataset_questions']}")
    print(f"Evaluated         : {summary['evaluated_questions']}")
    print(f"Remaining         : {summary['remaining_questions']}")
    print(f"Passed            : {summary['passed']}")
    print(f"Blocked           : {summary['blocked']}")
    print(f"Mismatched        : {summary['mismatched']}")
    print(f"Errors             : {summary['errors']}")
    print(f"Match rate         : {summary['result_match_rate']:.2%}")
    print(f"Results saved to   : {RESULTS_PATH}")


if __name__ == "__main__":
    main()
