# testing-pytest
example

    pip install pytest pytest-html
    pytest                           # full run: writes report.html
    pytest tests/test_file_exist.py  # just one check file
    pytest -k licenses               # any test whose name matches
    pytest --collect-only -q         # list every check (catalogue view)