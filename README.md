# testing-pytest
example

    pip install pytest pytest-html
    python -m pytest project                    # full run: writes report.html
    python -m pytest -k licenses .              # any test whose name matches
    python -m pytest --collect-only -q project  # list every check (catalogue view)