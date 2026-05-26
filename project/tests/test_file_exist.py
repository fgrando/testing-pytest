import pytest
import paths

REQUIRED = [
    paths.FOO_HEADER,
    paths.BAR_XML,
    paths.SHARED_PROTO,
    paths.SHARED_PROTO_DUP,
    paths.LICENSE_A,
    paths.LICENSE_B,
]


@pytest.mark.parametrize("path", REQUIRED, ids=str)
def test_file_exists(path):
    """Required input file is present in the workspace."""
    assert path.is_file(), f"missing: {path}"
