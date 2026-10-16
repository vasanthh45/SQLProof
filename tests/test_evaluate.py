
import ast
from pathlib import Path


def load_normalize_result():
    project_root = Path(__file__).resolve().parent.parent
    evaluate_path = project_root / "scripts" / "evaluate.py"

    source = evaluate_path.read_text(encoding="utf-8")
    tree = ast.parse(source)

    function_node = next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef)
        and node.name == "normalize_result"
    )

    module = ast.Module(
        body=[function_node],
        type_ignores=[],
    )

    namespace = {}
    exec(
        compile(module, str(evaluate_path), "exec"),
        namespace,
    )

    return namespace["normalize_result"]


normalize_result = load_normalize_result()


def test_different_column_aliases_match():
    first = (["film_count"], [(1000,)])
    second = (["COUNT(*)"], [(1000,)])

    assert normalize_result(first) == normalize_result(second)


def test_unordered_rows_match():
    first = (["name"], [("Alice",), ("Bob",)])
    second = (["name"], [("Bob",), ("Alice",)])

    assert normalize_result(first) == normalize_result(second)


def test_ordered_rows_do_not_match_when_order_differs():
    first = (["name"], [("Alice",), ("Bob",)])
    second = (["name"], [("Bob",), ("Alice",)])

    assert normalize_result(first, preserve_order=True) != (
        normalize_result(second, preserve_order=True)
    )


def test_different_values_do_not_match():
    first = (["film_count"], [(1000,)])
    second = (["film_count"], [(999,)])

    assert normalize_result(first) != normalize_result(second)


def test_different_column_counts_do_not_match():
    first = (["first_name"], [("Alice",)])
    second = (["first_name", "last_name"], [("Alice", "Smith")])

    assert normalize_result(first) != normalize_result(second)
