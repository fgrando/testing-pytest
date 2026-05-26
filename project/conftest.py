import pytest

import paths
from catalog import parse_c_defines, parse_xml_entries

@pytest.fixture(scope="session")
def c_defines():
    return parse_c_defines(paths.FOO_HEADER, prefix="FOO_")

@pytest.fixture(scope="session")
def xml_entries():
    return parse_xml_entries(paths.BAR_XML)