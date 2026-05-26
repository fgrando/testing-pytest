import pytest
import paths
from catalog import parse_c_defines


def _define_pairs():
    # Built at collection time so each define becomes its own visible test.
    return [
        pytest.param(n, v, id=n)
        for n, v in sorted(parse_c_defines(paths.FOO_HEADER, prefix="FOO_").items())
    ]


@pytest.mark.parametrize("name,value", _define_pairs())
def test_define_matches_xml(name, value, xml_entries):
    """Each FOO_* define appears as <entry> in bar.xml with the same value."""
    assert name in xml_entries, f"{name} not declared in bar.xml"
    assert (
        xml_entries[name] == value
    ), f"{name}: header={value!r} vs xml={xml_entries[name]!r}"
