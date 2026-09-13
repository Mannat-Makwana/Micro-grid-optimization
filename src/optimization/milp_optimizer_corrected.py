"""Backward-compatible name for the canonical microgrid MILP solver.

The project previously contained two copied optimizer implementations. They
could produce different dispatches and only one had the rolling-MPC fixes.
Keep this import path working while ensuring every caller uses the same model.
"""

from src.optimization import milp_optimizer as _optimizer


def __getattr__(name):
    """Expose legacy constants without maintaining a second copy."""

    return getattr(_optimizer, name)


INPUT_FILE = _optimizer.INPUT_FILE
OUTPUT_FILE = _optimizer.OUTPUT_FILE


def load_input():
    return _optimizer.load_input()


def build_model(df, **kwargs):
    return _optimizer.build_model(df, **kwargs)


def solve_model(model, verbose=True):
    return _optimizer.solve_model(model, verbose=verbose)


def extract_results(df, variables):
    return _optimizer.extract_results(df, variables)


def validate_solution(result, expected_flexible_energy=None):
    return _optimizer.validate_solution(
        result,
        expected_flexible_energy=expected_flexible_energy,
    )


def print_summary(result):
    return _optimizer.print_summary(result)


def solve_microgrid(*args, **kwargs):
    return _optimizer.solve_microgrid(*args, **kwargs)


def main():
    return _optimizer.main()


if __name__ == "__main__":
    main()
