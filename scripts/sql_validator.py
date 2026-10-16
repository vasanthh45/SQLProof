
import sqlglot
from sqlglot import exp


FORBIDDEN_EXPRESSIONS = (
    exp.Insert,
    exp.Update,
    exp.Delete,
    exp.Drop,
    exp.Alter,
    exp.Create,
    exp.Command,
)


def validate_sql(sql: str) -> tuple[bool, str]:
    """Validate a single read-only SELECT query using SQLGlot."""

    if not sql or not sql.strip():
        return False, "SQL query is empty."

    query = sql.strip()

    # Remove one optional trailing semicolon.
    query = query.rstrip(";").strip()

    if not query:
        return False, "SQL query is empty."

    try:
        statements = sqlglot.parse(query, read="mysql")
    except sqlglot.errors.ParseError:
        return False, "SQL syntax could not be parsed."

    # Reject empty or multiple statements.
    if len(statements) != 1 or statements[0] is None:
        return False, "Exactly one SQL statement is allowed."

    statement = statements[0]

    # Only SELECT queries and SELECT-based CTEs are allowed.
    if not isinstance(statement, (exp.Select, exp.Union, exp.Intersect, exp.Except)):
        return False, "Only SELECT queries are allowed."

    # Reject prohibited operations anywhere in the parsed query.
    for node in statement.walk():
        if isinstance(node, FORBIDDEN_EXPRESSIONS):
            return False, "Query contains a forbidden SQL operation."

    # Reject file-writing and file-reading functions.
    dangerous_functions = {
        "LOAD_FILE",
        "INTO_OUTFILE",
        "INTO_DUMPFILE",
    }

    for node in statement.walk():
        if isinstance(node, exp.Func):
            function_name = node.sql_name().upper()
            if function_name in dangerous_functions:
                return False, "Query contains a forbidden function."

    # Reject locking clauses.
    if statement.args.get("locks"):
        return False, "Locking queries are not allowed."

    return True, "SQL passed parser-based safety checks."


if __name__ == "__main__":
    test_queries = [
        "SELECT COUNT(*) FROM film;",
        "WITH film_counts AS (SELECT COUNT(*) AS total FROM film) "
        "SELECT total FROM film_counts;",
        "DELETE FROM customer;",
        "SELECT * FROM film; DROP TABLE film;",
        "UPDATE customer SET active = 0;",
        "SELECT * FROM customer FOR UPDATE;",
        "",
    ]

    for query in test_queries:
        is_safe, message = validate_sql(query)
        print(f"Query: {query!r}")
        print(f"Result: {'ALLOW' if is_safe else 'BLOCK'} — {message}\n")
