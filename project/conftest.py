import pytest
import inspect


import paths
from catalog import parse_c_defines, parse_xml_entries

@pytest.fixture(scope="session")
def c_defines():
    return parse_c_defines(paths.FOO_HEADER, prefix="FOO_")

@pytest.fixture(scope="session")
def xml_entries():
    return parse_xml_entries(paths.BAR_XML)

@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()
    if report.when != "call":
        return
    doc = inspect.getdoc(item.function) if item.function else None
    print(f"\n[DEBUG] {item.name}: {doc!r}")
    if doc:
        from pytest_html import extras
        report.extras = getattr(report, "extras", []) + [
            #extras.text(doc, name="Description"),
            extras.text(doc, name=doc) # bug, so we have to put like this...
        ]