
import pytest

from scripts.sql_validator import validate_sql


@pytest.mark.parametrize(
    "sql",
    [
        "SELECT COUNT(*) FROM film;",
        "SELECT title FROM film WHERE film_id = 1;",
        """
        WITH film_counts AS (
            SELECT COUNT(*) AS total FROM film
        )
        SELECT total FROM film_counts;
        """,
        "SELECT film_id FROM film UNION SELECT film_id FROM film;",
    ],
)
def test_safe_select_queries_are_allowed(sql):
    is_safe, _ = validate_sql(sql)
    assert is_safe is True


@pytest.mark.parametrize(
    "sql",
    [
        "",
        "   ",
        "DELETE FROM customer;",
        "UPDATE customer SET active = 0;",
        "INSERT INTO customer (store_id) VALUES (1);",
        "DROP TABLE film;",
        "ALTER TABLE film ADD COLUMN test_column INT;",
        "SELECT * FROM film; DROP TABLE film;",
        "SELECT * FROM customer FOR UPDATE;",
    ],
)
def test_unsafe_queries_are_blocked(sql):
    is_safe, _ = validate_sql(sql)
    assert is_safe is False
